import random

from flask import Flask

from limud.extensions import database
from limud.extensions import migrate
from limud.routes import blueprints

def create_app():
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
        instance_relative_config=False)

    app.config.from_object("config.Config")
    for bp in blueprints:
        app.register_blueprint(bp)
    database.init_app(app)

    try:
        seed = app.config["RANDOM_SEED"]
    except KeyError:
        app.logger.warning("No random seed was set!")
    else:
        app.logger.info("Setting random seed: %i", seed)
        random.seed(seed)

    with app.app_context():
        database.create_all()
        migrate.init_app(app, database)

        from . import context_processors

    return app
