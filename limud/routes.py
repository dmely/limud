from flask import current_app as app
from flask import render_template
from flask import Blueprint

from limud.words import Word


welcome = Blueprint(
    "welcome", __name__,
    template_folder="templates",
    static_folder="static"
)

flashcard = Blueprint(
    "flashcard", __name__,
    template_folder="templates",
    static_folder="static"
)

@welcome.route("/")
def root():
    return render_template("welcome.html")

@flashcard.route("/render/")
@flashcard.route("/render/<word>")
def render(word=None, obverse=True):
    if word is None:
        text = b'\xd7\x90\xd6\xb8\xd7\x9e\xd6\xb7\xd7\xa8'
        word = text.decode("utf-8")

    return render_template("flashcard.html", word=word, obverse=obverse)


