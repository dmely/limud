import os
import pathlib

from flask import Flask
from flask import render_template

from limud.words import Word

# Where all the vocabulary is stored using SQLite
DB_PATH = pathlib.Path(__file__).parent / "vocabulary.sqlite"

# Application templates
TEMPLATE_ROOT = pathlib.Path(__file__).parent / "templates"
FLASHCARD_HTML = TEMPLATE_ROOT / "flashcard.html"


def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_url_path="",
        static_folder="static",
        template_folder="templates")

    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=DB_PATH)

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # A simple page that says hello
    @app.route("/")
    def root():
        return render_template("flashcard.html")

    @app.route("/render/")
    @app.route("/render/<word>")
    def render(word=None):
        if word is None:
            text = b'\xd7\x90\xd6\xb8\xd7\x9e\xd6\xb7\xd7\xa8'
            word = text.decode("utf-8")
        return render_template("flashcard.html", word=word)
        # Word(text=text, description="word").render()

    return app
