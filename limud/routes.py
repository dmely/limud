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
    
    # Retrieve current list of words and then current word
    try:
        word_ids = session["word_ids"]
    except KeyError:
        app.logger.error("Invalid route: No 'words' found in flask.session!")
        raise

    # Retrieve index relative to current list of words (or 'run')
    index = request.args.get("index", None)
    index = 0 if index is None else int(index)
    app.logger.debug("Using index %i", index)
    
    # Process button clicks
    if request.method == "POST":
        if request.form["button_press"] == "flip":
            session["side"] = 1 - session["side"]
        
        if request.form["button_press"] == "previous":
            index = (index - 1) % len(word_ids)

        if request.form["button_press"] == "next":
            index = (index + 1) % len(word_ids)

    word = Word.query.get(word_ids[index])
    app.logger.info("Retrieved word: %s from database", word)

    # Show front or back of the flashcard? 0 = front, 1 = back
    if "side" not in session:
        session["side"] = 0

    if session["side"] == 0:
        content = word.hebrew
    elif session["side"] == 1:
        content = word.description
    else:
        raise ValueError("Invalid value for session variable 'side'!")

    return render_template(
        "flashcards.html",
        content=content,
        side=session["side"])


@flashcards.route("/flashcards/all")
def display_all():
    """Displays every word."""

    words = Word.query.all()
    word_ids = [word.id for word in words]
    if not word_ids:
        raise RuntimeError("Query returned no words!")
    
    if request.args.get("shuffle", False):
        random.shuffle(word_ids)

    session["word_ids"] = word_ids

    return redirect(url_for(".display_run", index=0))


@flashcards.route("/flashcards/favorites")
def display_all_favorites():
    """Displays all favorited words."""

    words = Word.query.filter_by(favorite=True).all()
    word_ids = [word.id for word in words]
    if not word_ids:
        raise RuntimeError("Query returned no words!")

    if request.args.get("shuffle", False):
        random.shuffle(word_ids)

    session["word_ids"] = word_ids

    return redirect(url_for(".display_run", index=0))


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

    session["word_ids"] = word_ids

    return redirect(url_for(".display_run", index=0))
    

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
