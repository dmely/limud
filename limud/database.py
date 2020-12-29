import pathlib
import sqlite3

# Where all the vocabulary is stored using SQLite
DB_PATH = pathlib.Path.cwd() / "vocabulary.db"


def add():
    with sqlite3.connect(DB_PATH) as db:
