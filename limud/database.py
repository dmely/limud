import sqlite3
from typing import Optional

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


def dump_db(favorites: bool):
    db = get_db()
    cursor = db.cursor()
    query = f"SELECT * FROM {'favorites' if favorites else 'vocabulary'}"
    cursor.execute(query)
    cursor.fetchall()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["VOCABULARY_DB"],
            detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e: Optional[Exception] = None):
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
    click.secho("Initialized the database.", fg="blue")


@click.command("dump-db")
@click.option("--favorites", default=False, is_flag=True, help="Only show favorites.")
@with_appcontext
def dump_db_command(favorites: bool):
    """Print out the entire vocabulary dataset to standard output.
    """
    click.secho("Dumping the database to STDOUT.", fg="blue")
    click.secho("Printing favorites only." if favorites else
               "Printing entire vocabulary.", fg="white")
    dump_db(favorites)


# Configures the app; needs to be called in the factory
def initialize_database(app: Flask):
    """Configure the Flask app to use database-related commands and
    context.
    """
    # Clean-up connection to database when exiting
    app.teardown_appcontext(close_db)

    # Enable 'flask <verb>'
    app.cli.add_command(init_db_command)
    app.cli.add_command(dump_db_command)
