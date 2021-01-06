import pathlib

_basedir = pathlib.Path(__file__).parent.absolute()
_appdir = _basedir / "limud"


class Config:
    """Configuration for the flashcard app."""

    SECRET_KEY = "dev"
    FLASK_ENV = "development"
    SCHEMA_DB = _appdir / "schema.sql"
    VOCABULARY_DB = _basedir / "vocabulary.sqlite"