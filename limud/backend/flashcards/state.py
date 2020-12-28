import enum
import random
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional
from typing import Sequence
from typing import SupportsInt
from typing import Union

from flask import Blueprint
from flask import current_app as app
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from sqlalchemy.orm import Query
from werkzeug import Response

from limud.backend.flashcards.formatting import description_as_html
from limud.backend.models.vocabulary import GrammaticalCategory
from limud.backend.models.vocabulary import Word
from limud.backend.models.conjugation import ConjugatedVerb
from limud.backend.wiktionary import WiktionaryWordParse
from limud.extensions import database


class FlashcardSorting(enum.Enum):
    """Represents a desired word order when displaying flashcards.

    NONE: Do not sort, take the words in whatever order the query
      returned them (presumably ordered by database ID).
    ALPHABETICAL: Sort with respect to the Hebrew abjad.
    SHUFFLE: Randomly shuffle the cards.
    """
    NONE = 1
    ALPHABETICAL = 2
    SHUFFLE = 3


class FlashcardSide(enum.Flag):
    FRONT = True
    BACK = False

    @classmethod
    def prompt_side(cls) -> "FlashcardSide":
        """Helper method that returns the "prompt" (or query) side of
        the flashcard.

        The "prompt" side of the flashcard is Hebrew by default (and
        the user attempts to guess the English key) but that behavior
        can be reversed by the appropriate configuration flag.
        """
        if app.config["USER_READS_HEBREW_AND_GUESSES_ENGLISH"]:
            return cls.FRONT
        return cls.BACK

    @classmethod
    def answer_side(cls) -> "FlashcardSide":
        """Helper method that returns the opposide of the prompt side.

        See also FlashcardSide.prompt_side().
        """
        return ~cls.prompt_side()


@dataclass
class FlashcardRunState:
    """Represents the state of a flashcard 'run'.
    
    Attributes
    ----------
    words : Sequence[int] | Sequence[WiktionaryWordParse] | 
            Sequence[ConjugatedVerb]
        Most often, words represented as row identifiers in the
        database.
        Sometimes, we need to store words in the state as parses from
        Wiktionary, which do not always neatly conform to the ORM.
    index : int
        The index of the word ID to be presented on the flashcard.
    side : FlashcardSide (boolean enum.Flag flag)
        The side of the flashcard to be presented.
    progress : [int, int]
        Represents how many words have been reviewed so far (first
        item) and how many remain in the current run (second item).
    """
    words: Union[
        Sequence[int],
        Sequence[WiktionaryWordParse],
        Sequence[ConjugatedVerb],
    ]
    index: int
    side: FlashcardSide
    progress: [int, int]

    @classmethod
    def from_flask_session(cls) -> "FlashcardRunState":
        """Initializes an instance from the Flask session."""
        instance = cls(
            words=session["words"],
            index=session["index"],
            side=FlashcardSide(session["side"]),
            progress=session["progress"],
        )

        app.logger.debug("Retrieved %s from Flask session", instance)

        return instance

    def to_flask_session(self):
        """Serializes an instance into the Flask session"""
        session["words"] = self.words
        session["index"] = self.index
        session["side"] = bool(self.side)
        session["progress"] = self.progress
        app.logger.debug("Serialized %s to Flask session", self)


def make_flashcard_run(endpoint: str,
                       query: Query,
                       sorting: FlashcardSorting = FlashcardSorting.NONE,
                       start_at_word_id: Optional[SupportsInt] = None) \
                       -> Response:
    """Uses a query to fetch a set of words from the database, and
    redirects to the correct endpoint.

    Parameters
    ----------
    endpoint : str
        Endpoint to be redirected to after words have been fetched.
    query : sqlalchemy.orm.Query
        Query used to retrieve words from the database.
    sorting : FlashcardSorting
        In what order should the words be presented. See documentation
        for FlashcardSorting for more information.
    start_at_word_id : int | str | None
        ID of the word to display first. If not specified, start with
        the first word available. If you specify some integer, make
        sure the word with that ID is actually present among the words
        retrieved by the input query!

    Returns
    -------
    werkzeug.Response
    """
    words = [word for word in query.all()]
    if not words:
        app.logger.error("Query %s returned no words!", query)
        return redirect(url_for("home.index"))
    
    if sorting is FlashcardSorting.NONE:
        app.logger.debug("No sorting required")
    elif sorting is FlashcardSorting.ALPHABETICAL:
        app.logger.debug("Alphabetical sorting required")
        words.sort(key=lambda word: remove_niqqudot(word.hebrew))
    elif sorting is FlashcardSorting.SHUFFLE:
        app.logger.debug("Random sorting (shuffling) required")
        random.shuffle(words)
    else:
        raise ValueError

    words_ids = [word.id for word in words]

    try:
        start_index = words_ids.index(int(start_at_word_id))  # type: ignore
    except TypeError:  # start_at_word_id is None
        start_index = 0
    except ValueError:  # start_at_word_id is int-castable
        app.logger.error(
            "Could not find word with desired ID %i "
            "among words queried from the database",
            start_at_word_id
        )
        return redirect(url_for("home.index"))

    # Set word list and reset other state
    FlashcardRunState(
        words=words_ids,
        index=start_index,
        side=FlashcardSide.prompt_side(),
        progress=[0, len(words)],
    ).to_flask_session()

    return redirect(url_for(endpoint))


def remove_niqqudot(hebrew: str) -> str:
    """Helper method thast removes niqqudot, to enable sorting Hebrew
    words alphabetically.

    The data must be normalized since a consonant followed by a niqqud
    may very well be represented by a single character.

    Parameters
    ----------
    hebrew : str
        String with diacritics.

    Returns
    -------
    str
        String without diacritics.
    """
    normalized = unicodedata.normalize("NFD", hebrew)
    stripped = re.sub(r"[^\u05d0-\u05f4]", "", normalized)
    app.logger.debug("Stripped word: %s -> %s", hebrew, stripped)
    return stripped