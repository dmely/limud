"""Object-relational mapping for words in the vocabulary.

All words have the following attributes:

    * id: Global, unique identifier
    * hebrew: The word itself, in Hebrew
    * description: The extended translation of the word
    * category: Whether the word is a noun, verb, adjective, ...
        See also the words.GrammaticalCategory Python enum.
    * chapter: Chapter in which the word was introduced.
    * favorite: Whether this is added to the favorites list.

Nouns have the following, additional attributes:

    * gender: Whether the word is feminine or masculine.
        See also the words.NounGender Python enum.
    * plabs: PLural (ABSolute form). Specified when irregular.
    * sgcst: SinGular (ConSTruct form). Specified when irregular.
    * plcst: PLural (ConSTruct form). Specified when irregular.

Adjectives have the following, additional attributes:

    * pladj: Form of the adjective when applied to a plural noun.
        Specified when irregular.
    * femadj: Form of the adjective when applied to a feminine noun.
        Specified when irregular.

Verbs have the following, additional attributes, corresponding to
their translated meaning in each (non qal/paal) binyan:

    nifal; piel; pual; hifil; hofal; hitpael;

For verbs, the 'description' field has the meaning of the qal
(paal) form.
"""

import enum

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy import String

from limud.extensions import database

QAMATS_HE_BYTES = b'\xd6\xb8\xd7\x94'


@enum.unique
class GrammaticalCategory(enum.Enum):
    """Grammatical category, or class, of a word in Hebrew.
    
    The values of each enum key correspond to values returned by the
    HTML form (see 'templates/edit.html' relative to this file).
    """
    GENERIC = None
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PARTICLE = "particle"


@enum.unique
class NounGender(enum.Enum):
    """Gender of a noun in Hebrew.
    
    The values of each enum key correspond to values returned by the
    HTML form (see 'templates/edit.html' relative to this file).
    """
    MASCULINE = "masculine"
    FEMININE = "feminine"

    @staticmethod
    def infer_from_word(text):
        """Infers the gender of a noun based on the presence of a
        qamats-he ending (in which case the feminine is assumed).

        Obviously, this does not account for exceptions (such as the
        word for 'father').
        """
        if text.encode("utf-8").endswith(QAMATS_HE_BYTES):
            return NounGender.FEMININE
        return NounGender.MASCULINE


class Word(database.Model):  # type: ignore
    """Base class for a word.

    Never to be used directly; instead, instantiate one of its
    subclasses.
    """
    __tablename__ = "vocabulary"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hebrew = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(Enum(GrammaticalCategory), nullable=False)
    chapter = Column(Integer)
    favorite = Column(Boolean, default=False)

    __mapper_args__ = {
        "polymorphic_on": category,
        "polymorphic_identity": GrammaticalCategory.GENERIC,
    }

    def __repr__(self):
        return (
            f"<Word {self.hebrew} | "
            f"id: {self.id}, "
            f"ch: {self.chapter}, "
            f"cat: {self.category}, "
            f"fav: {'yes' if self.favorite else 'no'}>")


class Noun(Word):
    gender = Column(Enum(NounGender))
    plabs = Column(String)
    sgcst = Column(String)
    plcst = Column(String)

    __mapper_args__ = {
        "polymorphic_identity": GrammaticalCategory.NOUN,
    }

    def __repr__(self):
        return (
            f"<Word {self.hebrew} | "
            f"id: {self.id}, "
            f"ch: {self.chapter}, "
            f"cat: {self.category}, "
            f"gdr: {self.gender}, "
            f"fav: {'yes' if self.favorite else 'no'}>")


class Verb(Word):
    nifal = Column(String)
    piel = Column(String)
    pual = Column(String)
    hifil = Column(String)
    hofal = Column(String)
    hitpael = Column(String)

    __mapper_args__ = {
        "polymorphic_identity": GrammaticalCategory.VERB,
    }


class Adjective(Word):
    pladj = Column(String)
    femadj = Column(String)

    __mapper_args__ = {
        "polymorphic_identity": GrammaticalCategory.ADJECTIVE,
    }


class Adverb(Word):
    __mapper_args__ = {
        "polymorphic_identity": GrammaticalCategory.ADVERB,
    }


class Particle(Word):
    __mapper_args__ = {
        "polymorphic_identity": GrammaticalCategory.PARTICLE,
    }


def create_word_from_form_dict(*,
                               hebrew: str,
                               description: str,
                               category: str,
                               chapter: str,
                               gender: str,
                               plabs: str,
                               sgcst: str,
                               plcst: str,
                               nifal: str,
                               piel: str,
                               pual: str,
                               hifil: str,
                               hofal: str,
                               hitpael: str,
                               pladj: str,
                               femadj: str):
    """Polymorphic constructor for a Word, based on a request's form.

    Creates the appropriate subtype of Word based on the value of the
    'category' enum, and performs various checks on the input fields.

    Important: This merely creates a Python object, it does not change
    the state of the database (e.g., it does not add and commit to the
    database). The parent caller is responsible for any calls to the 
    database API. 

    Parameters
    ----------
    See the documentation for Word. Note inputs to this function are
    all strings and need to be cast to the appropriate type.

    Returns
    -------
    Noun | Verb | Adjective | Adverb | Particle
    """
    category = GrammaticalCategory(category)  # type: ignore
    description = _capitalize(description)
    
    if category is GrammaticalCategory.NOUN:
        if not gender:
            gender = NounGender.infer_from_word(hebrew)
        else:
            gender = NounGender(gender)

        return Noun(
            hebrew=hebrew,
            description=description,
            category=category,
            chapter=int(chapter),
            favorite=False,
            gender=gender,
            plabs=plabs,
            sgcst=sgcst,
            plcst=plcst,
        )
    elif category is GrammaticalCategory.VERB:
        return Verb(
            hebrew=hebrew,
            description=description,
            category=category,
            chapter=int(chapter),
            favorite=False,
            nifal=_capitalize(nifal),
            piel=_capitalize(piel),
            pual=_capitalize(pual),
            hifil=_capitalize(hifil),
            hofal=_capitalize(hofal),
            hitpael=_capitalize(hitpael),
        )
    elif category is GrammaticalCategory.ADJECTIVE:
        return Adjective(
            hebrew=hebrew,
            description=description,
            category=category,
            chapter=int(chapter),
            favorite=False,
            pladj=pladj,
            femadj=femadj,
        )
    elif category is GrammaticalCategory.ADVERB:
        return Adverb(
            hebrew=hebrew,
            description=description,
            category=category,
            chapter=int(chapter),
            favorite=False,
        )
    elif category is GrammaticalCategory.PARTICLE:
        return Particle(
            hebrew=hebrew,
            description=description,
            category=category,
            chapter=int(chapter),
            favorite=False,
        )
    else:
        raise TypeError


def update_word_from_form_dict(word: Word,
                               hebrew: str,
                               description: str,
                               category: str,
                               chapter: str,
                               gender: str,
                               plabs: str,
                               sgcst: str,
                               plcst: str,
                               nifal: str,
                               piel: str,
                               pual: str,
                               hifil: str,
                               hofal: str,
                               hitpael: str,
                               pladj: str,
                               femadj: str):
    """Updates an existing Word, based on a request's form.

    Important: this merely updates the Python object, it does not
    affect the database state (e.g., it does not call commit() or
    flush() on the database). The parent caller is responsible for
    any calls to the database API.

    Parameters
    ----------
    See the documentation for Word. Note inputs to this function are
    all strings and need to be cast to the appropriate type.
    """
    word.hebrew = hebrew
    word.description = _capitalize(description)
    word.category = GrammaticalCategory(category)
    word.chapter = int(chapter)

    if word.category is GrammaticalCategory.NOUN:
        if not gender:
            gender = NounGender.infer_from_word(hebrew)
        else:
            gender = NounGender(gender)  # type: ignore

        word.gender = gender
        word.plabs = plabs
        word.sgcst = sgcst
        word.plcst = plcst

    if word.category is GrammaticalCategory.ADJECTIVE:
        word.pladj = pladj
        word.femadj = femadj

    if word.category is GrammaticalCategory.VERB:
        word.nifal = _capitalize(nifal)
        word.piel = _capitalize(piel)
        word.pual = _capitalize(pual)
        word.hifil = _capitalize(hifil)
        word.hofal = _capitalize(hofal)
        word.hitpael = _capitalize(hitpael)


def _capitalize(string: str) -> str:
    """Capitalize first letter of string without modifying the rest.
    """
    return f"{string[:1].upper()}{string[1:]}"