from flask import Flask

from .commands import register_commands
from .routes import edit
from .routes import flashcard
from .routes import welcome
from .models import database


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

    register_commands(app)
    database.init_app(app)

    with app.app_context():
        database.create_all()

    return app
