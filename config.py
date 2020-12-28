import pathlib

_basedir = pathlib.Path(__file__).parent.absolute()
_appdir = _basedir / "limud"
_dbname = "vocabulary.db.sqlite3"


class Config:
    """Configuration for the flashcard app."""

    # General application settings
    SECRET_KEY = "do_not_serve_in_production_this_is_not_vetted"
    FLASK_ENV = "development"
    RANDOM_SEED = 0

    # By default, show the Hebrew side of cards and make the user
    # guess the English key. Set to false to invert this behavior.
    USER_READS_HEBREW_AND_GUESSES_ENGLISH = True

    # When practicing conjugations, include waw-consecutive forms?
    # These are very similar to their non-consecutive forms, so the
    # user may want to skip them.
    CONJUGATION_PRACTICE_EXCLUDE_WAW_CONSECUTIVES = True

    # When practicing conjugations, include jussive/cohortative forms?
    # These are very similar to the imperfect conjugation, so the user
    # may want to skip them.
    CONJUGATION_PRACTICE_EXCLUDE_JUSSIVE_AND_COHORTATIVES = True

    # Database settings
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(_basedir / _dbname)
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False