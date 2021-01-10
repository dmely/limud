import random
from flask import Flask

from .commands import register_commands
from .routes import edit
from .routes import flashcards
from .routes import home
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
    app.register_blueprint(flashcards)
    app.register_blueprint(home)

    register_commands(app)
    database.init_app(app)

    try:
        seed = app.config["RANDOM_SEED"]
    except KeyError:
        app.logger.warn("No random seed was set!")
    else:
        random.seed(seed)

    with app.app_context():
        database.create_all()

        from . import context_processors

    return app
