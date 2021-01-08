from flask import current_app as app
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import Blueprint

from .models import Word
from .models import create_word_from_form_dict
from .models import database


home = Blueprint(
    "home", __name__,
    template_folder="templates",
    static_folder="static")


flashcard = Blueprint(
    "flashcard", __name__,
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


@flashcard.route("/flashcard/")
@flashcard.route("/flashcard/<word_id>")
def display(word_id=None, obverse=True):
    if word_id is None:
        word_id = 1

    # Retrieve word from database
    word = Word.query.get(word_id)
    app.logger.info("Retrieved word: %s from database", word)

    return render_template(
        "flashcard.html",
        display_text=word.hebrew,
        obverse=obverse)
