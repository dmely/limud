from flask import Flask

from .database import initialize_database
from .routes import edit
from .routes import flashcard
from .routes import welcome


def create_app():
    app = Flask(
        __name__,
        static_url_path="",
        static_folder="static",
        template_folder="templates",
        instance_relative_config=False)

    app.config.from_object("config.Config")
    app.register_blueprint(edit)
    app.register_blueprint(flashcard)
    app.register_blueprint(welcome)
    initialize_database(app)

    return app

