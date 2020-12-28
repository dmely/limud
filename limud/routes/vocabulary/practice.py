import random

from flask import current_app as app
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import Blueprint

from limud.backend.flashcards import FlashcardSide
from limud.backend.flashcards import FlashcardSorting
from limud.backend.flashcards import FlashcardRunState
from limud.backend.flashcards import make_flashcard_run
from limud.backend.flashcards import description_as_html
from limud.backend.models.vocabulary import GrammaticalCategory
from limud.backend.models.vocabulary import Word
from limud.extensions import database
from limud.routes.vocabulary._blueprint import vocabulary


@vocabulary.route("/practice/", methods=["GET", "POST"])
def practice():
    state = FlashcardRunState.from_flask_session()

    # Process button clicks
    if request.method == "POST":
        if request.form["button_press"] == "flip":
            app.logger.debug("Received request to flip")

            # Note that unlike the "review" mode (see: /flashcards/ route),
            # once a card has been flipped, we disallow "unflipping" it.
            state.side = FlashcardSide.answer_side()

        # User indicates they got the word right: Remove word from the set of 
        # words being considered. No need to update the index since the length
        # of the word list has changed. Display the prompt side again for the
        # card next in line.
        if request.form["button_press"] == "correct":
            app.logger.debug("Received request for correct")
            state.words.pop(state.index)
            state.progress[0] += 1
            state.side = FlashcardSide.prompt_side()
            
        # User indicates they got the word wrong: Move on to the next word and
        # display the prompt side again for the card next in line.
        if request.form["button_press"] == "incorrect":
            app.logger.debug("Received request for incorrect")
            state.index += 1
            state.progress[0] += 1
            state.side = FlashcardSide.prompt_side()

    if not state.words:
        app.logger.info("Finished current run. Good job!")
        return redirect(url_for("home.index"))

    # New run: Make sure index is valid wrt. new word list length
    if state.index == len(state.words):
        app.logger.info("Finished a run, shuffling remaining words.")
        random.shuffle(state.words)
        state.progress = [0, len(state.words)]
        state.index = 0

    word = Word.query.get(state.words[state.index])
    app.logger.info("Retrieved word: %s from database", word)
        
    if state.side is FlashcardSide.FRONT:
        content = word.hebrew
        app.logger.debug("Showing front of flashcard")
    elif state.side is FlashcardSide.BACK:
        content = description_as_html(word)
        app.logger.debug("Showing back of flashcard ")
    else:
        raise ValueError("Invalid value for session variable 'side'!")

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

    # Save state before leaving function
    state.to_flask_session()
    app.logger.debug(
        "Game state: button press = %s, state = %s",
        request.form.get("button_press", None), state,
    )

    # Note: Unlike "review mode" (flashcards), progress[0] is essentially
    # equal to the index (and not index + 1) to avoid ever showing a full 
    # progress bar to 100%, which would reduce the mental reward to the user
    # for completing a run.
    return render_template("practice.html",
        content=content,
        render_hebrew_large=state.side is FlashcardSide.FRONT,
        render_reveal_button=state.side is FlashcardSide.FRONT,
        render_favorite_button=True,
        favorite=word.favorite,
        progress_percent=100 * state.progress[0] / state.progress[1],
    )


@vocabulary.route("/practice/all")
def practice_all():
    """Displays every word.
    
    Randomizes word order by default.
    """
    return make_flashcard_run(
        endpoint=".practice",
        query=Word.query,
        sorting=FlashcardSorting.SHUFFLE,
    )


@vocabulary.route("/practice/favorites")
def practice_all_favorites():
    """Displays all favorited words.

    Randomizes word order by default.
    """
    return make_flashcard_run(
        endpoint=".practice",
        query=Word.query.filter_by(favorite=True),
        sorting=FlashcardSorting.SHUFFLE,
    )


@vocabulary.route("/practice/category/<category>")
def practice_by_category(category: str):
    """Displays all words belonging to some grammatical category.

    Randomizes word order by default.
    """
    return make_flashcard_run(
        endpoint=".practice",
        query=Word.query.filter_by(category=GrammaticalCategory(category)),
        sorting=FlashcardSorting.SHUFFLE,
    )


@vocabulary.route("/practice/chapter/<chapter_id>")
def practice_by_chapter(chapter_id: str):
    """Fetches all words from a chapter, shuffles them, and displays
    them.

    Randomizes word order by default.
    """
    return make_flashcard_run(
        endpoint=".practice",
        query=Word.query.filter_by(chapter=int(chapter_id)),
        sorting=FlashcardSorting.SHUFFLE,
    )
    