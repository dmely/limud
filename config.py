import pathlib

_basedir = pathlib.Path(__file__).parent.absolute()
_appdir = _basedir / "limud"


class Config:
    """Configuration for the flashcard app."""

    SECRET_KEY = "dev"
    FLASK_ENV = "development"
    VOCABULARY_DB = _appdir / "vocabulary.sqlite"