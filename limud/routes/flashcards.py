import random

from flask import current_app as app
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import Blueprint

from ..models import Word
from ..models import database


flashcards = Blueprint(
    "flashcards", __name__,
    template_folder="templates",
    static_folder="static")


@flashcards.route("/flashcards/", methods=["GET", "POST"])
def display_run():
    """Displays all cards in a given "run".
    
    The order and contents of the run are determined by the 'word_ids'
    variable of the state stored in flask.session.

    Thus: to display any series of words, ensure that list of IDs is
    in flask.session before accessing this route.
    """

    # Retrieve current application state:
    # - the list of words being displayed
    # - the current index relative to current list of words (or 'run')
    # - the side of the flashcard being shown (0 = front, 1 = back)
    try:
        word_ids = session["word_ids"]
    except KeyError:
        error_message = (
            "Invalid route: No 'word_ids' found in flask.session! "
            "This should never happen. Crashing."
        )
        app.logger.error(error_message)
        raise RuntimeError(error_message)

    if not word_ids:
        error_message = (
            "Invalid route: 'word_ids' in flask.session is empty! "
            "This should never happen. Crashing."
        )
        app.logger.error(error_message)
        raise RuntimeError(error_message)

    app.logger.debug("Retrieved %i words from cache.", len(word_ids))

    index = session.setdefault("index", 0)
    side = session.setdefault("side", 0)

    # Now we process any button clicks (always HTTP POST requests)
    if request.method == "POST":
        if request.form["button_press"] == "flip":
            app.logger.debug("Received request to flip")
            side = 1 - side

        if request.form["button_press"] == "previous":
            app.logger.debug("Received request for previous")
            index = (index - 1) % len(word_ids)

        if request.form["button_press"] == "next":
            app.logger.debug("Received request for next")
            index = (index + 1) % len(word_ids)

    word = Word.query.get(word_ids[index])
    app.logger.info("Retrieved word: %s from database", word)
        
    if side == 0:
        content = word.hebrew
        app.logger.debug("Showing front of flashcard")
    elif side == 1:
        content = word.description
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

        if request.form["button_press"] == "edit":
            app.logger.debug("Received request to edit word %s", word)
            return redirect(url_for("edit.existing_word", word_id=word.id))

    # Update state before leaving function
    session["index"] = index
    session["side"] = side

    return render_template("flashcards.html",
        content=content, side=side, favorite=int(word.favorite))


@flashcards.route("/flashcards/all")
def display_all():
    """Displays every word.
    
    Randomize by default.
    """

    words = Word.query.all()
    word_ids = [word.id for word in words]
    if not word_ids:
        app.logger.error("Query (ALL) returned no words!")
        return redirect(url_for("home.index"))
    
    if request.args.get("shuffle", False):
        random.shuffle(word_ids)

    # Set word list and reset other state
    session["word_ids"] = word_ids
    session["index"] = 0
    session["side"] = 0

    return redirect(url_for(".display_run"))


@flashcards.route("/flashcards/favorites")
def display_all_favorites():
    """Displays all favorited words.

    Randomize by default.
    """
    words = Word.query.filter_by(favorite=True).all()
    word_ids = [word.id for word in words]

    if not word_ids:
        app.logger.warn("Query (FAVORITES = TRUE) returned no words!")
        return redirect(url_for("home.index"))

    if request.args.get("shuffle", False):
        random.shuffle(word_ids)

    # Set word list and reset other state
    session["word_ids"] = word_ids
    session["index"] = 0
    session["side"] = 0

    return redirect(url_for(".display_run"))


@flashcards.route("/flashcards/chapter/<chapter_id>")
def display_by_chapter(chapter_id: str):
    """Fetches all words from a chapter, shuffles them, and displays
    them.

    Randomize by default.
    """
    chapter_id = int(chapter_id)
    words = Word.query.filter_by(chapter=chapter_id).all()
    word_ids = [word.id for word in words]

    if not word_ids:
        app.logger.warn("Query (CHAPTER = %i) returned no words!", chapter_id)
        return redirect(url_for("home.index"))

    if request.args.get("shuffle", False):
        random.shuffle(word_ids)

    # Set word list and reset other state
    session["word_ids"] = word_ids
    session["index"] = 0
    session["side"] = 0

    return redirect(url_for(".display_run"))
    

@flashcards.route("/flashcards/word/<word_id>")
def display_by_word(word_id: str):
    """Display every word but start at the word with the requisite ID.

    Do not randomize by default.
    """
    word_id = int(word_id)
    words = Word.query.all()
    word_ids = [word.id for word in words]

    if not word_ids:
        app.logger.warn("Query (ALL) returned no words!")
        return redirect(url_for("home.index"))

    try:
        index = word_ids.index(word_id)
    except ValueError:
        app.logger.error("Could not find word with desired ID %i", word_id)
        return redirect(url_for("home.index"))

    # Set word list and other state
    session["word_ids"] = word_ids
    session["index"] = index
    session["side"] = 0

    return redirect(url_for(".display_run"))
