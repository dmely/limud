import enum
import random
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional
from typing import Sequence
from typing import SupportsInt
from typing import Union

from flask import Blueprint
from flask import current_app as app
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from sqlalchemy.orm import Query
from werkzeug import Response

from limud.backend.flashcards import description_as_html
from limud.backend.flashcards import make_flashcard_run
from limud.backend.flashcards import FlashcardRunState
from limud.backend.flashcards import FlashcardSide
from limud.backend.flashcards import FlashcardSorting
from limud.backend.models.conjugation import ConjugatedVerb
from limud.backend.models.vocabulary import GrammaticalCategory
from limud.backend.models.vocabulary import Word
from limud.backend.wiktionary import WiktionaryWordParse
from limud.extensions import database
from limud.routes.vocabulary._blueprint import vocabulary


@vocabulary.route("/review/", methods=["GET", "POST"])
def review():
    """Displays all cards in a given "run".

    Before accessing this route, proper state must be set in the Flask
    session object. See also the docs of 'FlashcardRunState'.
    """
    state = FlashcardRunState.from_flask_session()

    if not state.words:
        app.logger.error("Empty word list. Going back to home.")
        return redirect(url_for("home.index"))
    
    # Process button clicks
    if request.method == "POST":
        if request.form["button_press"] == "flip":
            app.logger.debug("Received request to flip")
            state.side = ~state.side

        # Previous: Show previous card *without* showing the side
        # the user is trying to guess (since they are practicing).
        if request.form["button_press"] == "previous":
            app.logger.debug("Received request for previous")
            state.index = (state.index - 1) % len(state.words)
            
            # Force switch back to the prompt side
            state.side = FlashcardSide.prompt_side()

        # Next: Show next card *without* showing the side
        # the user is trying to guess (since they are practicing).
        if request.form["button_press"] == "next":
            app.logger.debug("Received request for next")
            state.index = (state.index + 1) % len(state.words)

            # Force switch back to the prompt side
            state.side = FlashcardSide.prompt_side()

    word = Word.query.get(state.words[state.index])
    app.logger.info("Retrieved word: %s from database", word)

    state.progress[0] = state.index + 1
    state.progress[1] = len(state.words)
    app.logger.info("Progress: %i out of %i", *state.progress)
        
    if state.side is FlashcardSide.FRONT:
        content = word.hebrew
        app.logger.debug("Showing front of flashcard")
   
    if state.side is FlashcardSide.BACK:
        content = description_as_html(word)
        app.logger.debug("Showing back of flashcard")

    # Look at these requests at the end since we need to load the word first
    if request.method == "POST":
        if request.form["button_press"] == "favorite":
            app.logger.debug("Received request to favorite")
            word.favorite = True
            database.session.commit()

        if request.form["button_press"] == "unfavorite":
            app.logger.debug("Received request to unfavorite")
            word.favorite = False
            database.session.commit()

        if request.form["button_press"] == "edit":
            app.logger.debug("Received request to edit word %s", word)
            return redirect(url_for("vocabulary.edit_word", word_id=word.id))

    # Save state before leaving function
    state.to_flask_session()

    return render_template("review.html",
        content=content,
        render_front_of_flashcard=state.side is FlashcardSide.FRONT,
        favorite=word.favorite,
        progress_percent=100 * state.progress[0] / state.progress[1],
    )


@vocabulary.route("/review/all")
def review_all():
    """Displays every word.
    
    Do not randomize by default.
    """
    return make_flashcard_run(
        endpoint=".review",
        query=Word.query,
        sorting=FlashcardSorting.ALPHABETICAL,
    )


@vocabulary.route("/review/favorites")
def review_all_favorites():
    """Displays all favorited words.

    Do not randomize by default.
    """
    return make_flashcard_run(
        endpoint=".review",
        query=Word.query.filter_by(favorite=True),
        sorting=FlashcardSorting.ALPHABETICAL,
    )


@vocabulary.route("/review/category/<category>")
def review_by_category(category: str):
    """Displays all words belonging to some grammatical category.

    Do not randomize by default.
    """
    return make_flashcard_run(
        endpoint=".review",
        query=Word.query.filter_by(category=GrammaticalCategory(category)),
        sorting=FlashcardSorting.ALPHABETICAL,
    )


@vocabulary.route("/review/chapter/<chapter_id>")
def review_by_chapter(chapter_id: str):
    """Fetches all words from a chapter, shuffles them, and displays
    them.

    Do not randomize by default.
    """
    return make_flashcard_run(
        endpoint=".review",
        query=Word.query.filter_by(chapter=int(chapter_id)),
        sorting=FlashcardSorting.ALPHABETICAL,
    )
    

@vocabulary.route("/review/word/<word_id>")
def review_by_word(word_id: str):
    """Display every word but start at the word with the requisite ID.

    Do not randomize by default.
    """
    return make_flashcard_run(
        endpoint=".review",
        query=Word.query,
        sorting=FlashcardSorting.ALPHABETICAL,
        start_at_word_id=int(word_id),
    )
