import sqlite3

import click
from flask import Flask
from flask import current_app
from flask import g
from flask.cli import with_appcontext


def init_db():
    db = get_db()
    schema = current_app.config["SCHEMA_DB"]
    with current_app.open_resource(schema) as f:
        db.executescript(f.read().decode("utf8"))


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["VOCABULARY_DB"],
            detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Register command-line verbs to be run ('flask <verb>')
@click.command("init-db")
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables.
    """
    init_db()
    click.echo(click.style("Initialized the database.", fg="blue"))


# Configures the app; needs to be called in the factory
def initialize_database(app: Flask):
    """Configure the Flask app to use database-related commands and
    context.
    """
    # Clean-up connection to database when exiting
    app.teardown_appcontext(close_db)

    # Enable 'flask init-db'
    app.cli.add_command(init_db_command)
