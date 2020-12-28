from typing import Union

from flask import current_app as app

from limud.backend.models.conjugation import pack
from limud.backend.models.conjugation import unpack
from limud.backend.models.conjugation import Binyan
from limud.backend.models.conjugation import ConjugatedVerb
from limud.backend.models.conjugation import Gender
from limud.backend.models.conjugation import Number
from limud.backend.models.conjugation import Person
from limud.backend.models.conjugation import Tense
from limud.backend.models.conjugation import get_conjugation
from limud.backend.models.conjugation import label_pronouns
from limud.backend.models.conjugation import label_tense
from limud.backend.models.conjugation import translate_pronouns
from limud.backend.models.vocabulary import GrammaticalCategory
from limud.backend.models.vocabulary import Word
from limud.extensions import database 


@app.context_processor
def add_all_chapters():
    """Return all unique chapter IDs, in sorted order.
    
    This is necessary because the main menu of the application
    contains a drop-down menu referencing each chapter that exists in
    the database.

    The query below implements:
        SELECT DISTINCT vocabulary.chapter AS <?> FROM vocabulary
    """
    query = database.session.query(Word.chapter).distinct()
    chapter_ids = sorted(chapter_id for chapter_id, in query.all())

    return {"all_chapters_ids": chapter_ids}


@app.context_processor
def add_all_categories():
    """Return all grammatical categories, in alphabetical order.
    
    This is necessary because the main menu of the application
    contains a drop-down menu referencing each category.
    """
    return {"all_grammatical_categories": [
        gc.value for gc in GrammaticalCategory
        if gc is not GrammaticalCategory.GENERIC
    ]}


@app.context_processor
def add_conjugation_functions():
    return {
        "conjugation_pack": pack,
        "conjugation_unpack": unpack,
        "label_tense": label_tense,
        "label_pronouns": label_pronouns,
        "translate_pronouns": translate_pronouns,
        "get_conjugation_str": get_conjugation_str,
    }


@app.context_processor
def add_true_length_of_hebrew_string():
    return {
        # Mesure the "length" of a pure Hebrew string without diacritics
        # The range U+0590–U+05C7 includes all niqqudot and cantillation
        "true_length_of_hebrew_string": \
            lambda s: sum(1 for c in s if not
                (ord("\u0590") <= ord(c) <= ord("\u05c7"))
            ),
    }


def get_conjugation_str(binyan: Union[Binyan, str],
                        tense: Union[Tense, str],
                        person: Union[Person, str],
                        gender: Union[Gender, str],
                        number: Union[Number, str]) -> str:
    """Type-tolerant wrapper for get_conjugation() that returns the
    empty string if no conjugation is found (appropriate for an HTML
    form).
    """
    conjugation = get_conjugation(
        binyan=Binyan(binyan),
        tense=Tense(tense),
        person=Person(person),
        gender=Gender(gender),
        number=Number(number),
    )

    if conjugation is None:
        return ""

    return conjugation.hebrew


@app.context_processor
def add_all_pronouns():
    """Iterate over all pronouns in Hebrew, for convenience.

    Note this is done is careful order so that the table looks
    intuitive.
    """
    return {"all_pronouns": [
        (Person.FIRST, Gender.COMMON, Number.SINGULAR),
        (Person.SECOND, Gender.MASCULINE, Number.SINGULAR),
        (Person.SECOND, Gender.FEMININE, Number.SINGULAR),
        (Person.THIRD, Gender.MASCULINE, Number.SINGULAR),
        (Person.THIRD, Gender.FEMININE, Number.SINGULAR),
        (Person.FIRST, Gender.COMMON, Number.PLURAL),
        (Person.SECOND, Gender.MASCULINE, Number.PLURAL),
        (Person.SECOND, Gender.FEMININE, Number.PLURAL),
        (Person.THIRD, Gender.MASCULINE, Number.PLURAL),
        (Person.THIRD, Gender.FEMININE, Number.PLURAL),
    ]}


@app.context_processor
def add_all_tenses_except_the_infinitives():
    """Iterate over most (but not all) tenses for the conjugation
    table.

    This only makes sense considering the layout of the table in the
    conjugation.html template.
    """
    return {"all_tenses_except_the_infinitives": [
        Tense.PERFECT,
        Tense.IMPERFECT,
        Tense.JUSSIVE_COHORTATIVE,
        Tense.IMPERATIVE,
        Tense.PARTICIPLE_ACTIVE,
        Tense.PARTICIPLE_PASSIVE,
        Tense.PERFECT_WAW_CONSECUTIVE,
        Tense.IMPERFECT_WAW_CONSECUTIVE,
    ]}


@app.context_processor
def add_all_binyanim():
    return {"all_binyanim": [e.value for e in Binyan]}