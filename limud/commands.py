import click
from flask import Flask
from flask import current_app as app
from flask.cli import with_appcontext

from .models import database
from .models import Word


_dump_db_help = "Only show favorites."

@click.command("dump-db")
@click.option("--favorites", default=False, is_flag=True, help=_dump_db_help)
@with_appcontext
def dump_db_command(favorites: bool):
    """Print out the entire vocabulary dataset to standard output."""
    click.secho("Dumping the database to standard output.", fg="blue")

    if favorites:
        click.secho("Printing favorites only.", fg="white")
        click.echo(Word.query.filter_by(favorite=True).all())
    else:
        click.secho("Printing entire vocabulary.", fg="white")
        click.echo(Word.query.all())


_drop_db_prompt = "Are you sure you want to clear the database?"
_drop_db_prompt = click.style(_drop_db_prompt, fg="red")

@click.command("drop-db")
@click.confirmation_option(prompt=_drop_db_prompt)
@with_appcontext
def drop_db_command():
    """Clear the contents of the database (this is irreversible!)"""
    database.drop_all()
    click.secho("Dropped all tables!", fg="red")


# Configures the app; needs to be called in the factory
def register_commands(app: Flask):
    """Configure the Flask app to admit database-related commands."""
    app.cli.add_command(dump_db_command)
    app.cli.add_command(drop_db_command)
