import pathlib

_basedir = pathlib.Path(__file__).parent.absolute()
_appdir = _basedir / "limud"
_dbname = "vocabulary.db.sqlite3"


class Config:
    """Configuration for the flashcard app."""

    # General application settings
    SECRET_KEY = "dev"
    FLASK_ENV = "development"

    # Database settings
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(_basedir / _dbname)
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False