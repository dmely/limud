import random

from flask import current_app as app
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import Blueprint

from .models import Word
from .models import create_word_from_form_dict
from .models import database


home = Blueprint(
    "home", __name__,
    template_folder="templates",
    static_folder="static")


flashcards = Blueprint(
    "flashcards", __name__,
    template_folder="templates",
    static_folder="static")


edit = Blueprint(
    "edit", __name__,
    template_folder="templates",
    static_folder="static")


@home.route("/")
def index():
    return render_template("index.html")


@edit.route("/edit/", methods=["GET", "POST"])
def form():
    if request.method == "GET":
        return render_template("edit.html")

    if request.method == "POST":
        app.logger.debug(f"Submitted fields: {request.form}")
        
        word = create_word_from_form_dict(**request.form)
        database.session.add(word)
        database.session.commit()
        
        app.logger.info("Added word: %s to database", word)

        return redirect(url_for("home.index"))


@flashcards.route("/flashcards/", methods=["GET", "POST"])
def display_run():
    """By default, displays every word in word ID order.

    If the flask.session object has a list of word IDs (possibly in
    random order), display words by ID order from that list instead.

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
        app.logger.error("Invalid route: No 'word_ids' found in flask.session!")
        raise
    else:
        if not word_ids:
            raise RuntimeError("Invalid: cached word list is empty!")
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

    # Update state before leaving function
    session["index"] = index
    session["side"] = side

    return render_template("flashcards.html", content=content, side=side)


@flashcards.route("/flashcards/all")
def display_all():
    """Displays every word."""

    words = Word.query.all()
    word_ids = [word.id for word in words]
    if not word_ids:
        raise RuntimeError("Query returned no words!")
    
    if request.args.get("shuffle", False):
        random.shuffle(word_ids)

    # Set word list and reset other state
    session["word_ids"] = word_ids
    session["index"] = 0
    session["side"] = 0

    return redirect(url_for(".display_run"))


@flashcards.route("/flashcards/favorites")
def display_all_favorites():
    """Displays all favorited words."""

    words = Word.query.filter_by(favorite=True).all()
    word_ids = [word.id for word in words]
    if not word_ids:
        raise RuntimeError("Query returned no words!")

    if request.args.get("shuffle", False):
        random.shuffle(word_ids)

    # Set word list and reset other state
    session["word_ids"] = word_ids
    session["index"] = 0
    session["side"] = 0

    return redirect(url_for(".display_run"))


@flashcards.route("/flashcards/chapter/<chapter_id>")
def display_by_chapter(chapter_id: int):
    """Fetches all words from a chapter, shuffles them, and displays
    them.
    """
    words = Word.query.filter_by(chapter=chapter_id).all()
    word_ids = [word.id for word in words]
    if not word_ids:
        raise RuntimeError("Query returned no words!")

    if request.args.get("shuffle", False):
        random.shuffle(word_ids)

    # Set word list and reset other state
    session["word_ids"] = word_ids
    session["index"] = 0
    session["side"] = 0

    return redirect(url_for(".display_run"))
    

# @flashcards.route("/flashcards/word/<word_id>")
# def display_by_word(word_id: int):
#     obverse = True

#     # Retrieve word from database
#     word = Word.query.get(word_id)
#     app.logger.info("Retrieved word: %s from database", word)

#     return render_template(
#         "flashcards.html",
#         display_text=word.hebrew,
#         obverse=obverse)
