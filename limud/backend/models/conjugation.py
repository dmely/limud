"""Object-relational mapping for conjugations for each verb stem.

Note that the integer values associated with each enumeration may be
combined and encoded as a bitfield to compactly label cells in the
conjugation table, so do not change these!
"""

import enum
from typing import Optional
from typing import Tuple

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy import String

from limud.extensions import database


@enum.unique
class Binyan(enum.Enum):
    QAL = "qal"
    NIFAL = "nifal"
    PIEL = "piel"
    PUAL = "pual"
    HIFIL = "hifil"
    HOFAL = "hofal"
    HITPAEL = "hitpael"


@enum.unique
class Tense(enum.Enum):
    PERFECT = 0
    IMPERFECT = 1
    # This includes both moods since the cohortative mood applies to
    # the first person exclusively, and the jussive to the second and
    # third persons (almost?) exclusively.
    JUSSIVE_COHORTATIVE = 2
    IMPERATIVE = 3
    PARTICIPLE_ACTIVE = 4
    PARTICIPLE_PASSIVE = 5
    INFINITIVE_ABSOLUTE = 6
    INFINITIVE_CONSTRUCT = 7
    PERFECT_WAW_CONSECUTIVE = 8
    IMPERFECT_WAW_CONSECUTIVE = 9


@enum.unique
class Person(enum.Enum):
    FIRST = 0
    SECOND = 1
    THIRD = 2


@enum.unique
class Gender(enum.Enum):
    MASCULINE = 0
    FEMININE = 1
    COMMON = 2


@enum.unique
class Number(enum.Enum):
    SINGULAR = 0
    PLURAL = 1


class ConjugatedVerb(database.Model):  # type: ignore
    __tablename__ = "conjugation"
    
    id = Column(Integer, primary_key=True, autoincrement=True)

    # This has to be nullable because some combinations of column
    # values (e.g., imperative third-person) do not make sense.
    hebrew = Column(String, nullable=True)

    # The rest fully determines a verbal stem's conjugation
    binyan = Column(Enum(Binyan), nullable=False)
    tense = Column(Enum(Tense), nullable=False)

    # These are nullable in case it's an infinitive
    person = Column(Enum(Person), nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    number = Column(Enum(Number), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} {self.id}: '{self.hebrew}' ("
            f"{self.binyan}, {self.tense}, {self.person}, "
            f"{self.gender}, {self.number})>"
        )



def pack(t: Tense, p: Person, g: Gender, n: Number) -> int:
    """Store any conjugation (trivially equivalent to a tuple of
    tense, person, gender, number) as an integer representing a
    bitfield.

    The bitfield is structured as follows:
    * First four bits: tense (since Tense has log2(len(Tense)) = 3.32 bits)
    * Next two bits: person
    * Next two bits: gender
    * Last bit: number
    """
    return t.value << 0 | p.value << 4 | g.value << 6 | n.value << 8


def unpack(bits: int) -> Tuple[Tense, Person, Gender, Number]:
    """Converse of pack(): Parses a bitfield representation of a
    conjugation back into a tuple of enum instances.
    """
    return (
        Tense((bits  & 0b000001111) >> 0),
        Person((bits & 0b000110000) >> 4),
        Gender((bits & 0b011000000) >> 6),
        Number((bits & 0b100000000) >> 8),
    )


def get_conjugation(binyan: Binyan,
                    tense: Tense,
                    person: Person,
                    gender: Gender,
                    number: Number) -> Optional[ConjugatedVerb]:
    """There is a one-to-one mapping between a conjugation
    (ConjugatedVerb) and a tuple of binyan, tense, person, gender,
    number.
    
    This function retrieves that row from the database and ensures
    that there is exactly zero or one such row.
    """
    fetched = ConjugatedVerb.query.filter_by(
        binyan=binyan,
        tense=tense,
        person=person,
        gender=gender,
        number=number,
    ).all()

    if len(fetched) == 0:
        return None

    if len(fetched) == 1:
        conjugation, = fetched
        return conjugation

    raise ValueError(f"Unexpected: Query returned > 1 rows: {fetched}")


def label_tense(tense: Tense) -> str:
    if tense is Tense.PERFECT:
        return "Pf."
    if tense is Tense.IMPERFECT:
        return "Impf."
    if tense is Tense.JUSSIVE_COHORTATIVE:
        return "Juss. / Cohort."
    if tense is Tense.IMPERATIVE:
        return "Impv."
    if tense is Tense.PARTICIPLE_ACTIVE:
        return "Act. Ptc."
    if tense is Tense.PARTICIPLE_PASSIVE:
        return "Pas. Ptc."
    if tense is Tense.INFINITIVE_ABSOLUTE:
        return "Inf. Abs."
    if tense is Tense.INFINITIVE_CONSTRUCT:
        return "Inf. Cst."
    if tense is Tense.PERFECT_WAW_CONSECUTIVE:
        return "Waw C. Pf."
    if tense is Tense.IMPERFECT_WAW_CONSECUTIVE:
        return "Waw C. Impf."
    raise TypeError


def label_pronouns(p: Person, g: Gender, n: Number) -> str:
    if p is Person.FIRST and g is Gender.COMMON and n is Number.SINGULAR:
        return "I (1cs)"
    if p is Person.SECOND and g is Gender.MASCULINE and n is Number.SINGULAR:
        return "you (2ms)"
    if p is Person.SECOND and g is Gender.FEMININE and n is Number.SINGULAR:
        return "you (2fs)"
    if p is Person.THIRD and g is Gender.MASCULINE and n is Number.SINGULAR:
        return "he (3ms)"
    if p is Person.THIRD and g is Gender.FEMININE and n is Number.SINGULAR:
        return "she (3fs)"
    if p is Person.FIRST and g is Gender.COMMON and n is Number.PLURAL:
        return "we (1cp)"
    if p is Person.SECOND and g is Gender.MASCULINE and n is Number.PLURAL:
        return "you (2mp)"
    if p is Person.SECOND and g is Gender.FEMININE and n is Number.PLURAL:
        return "you (2fp)"
    if p is Person.THIRD and g is Gender.MASCULINE and n is Number.PLURAL:
        return "they (3mp)"
    if p is Person.THIRD and g is Gender.FEMININE and n is Number.PLURAL:
        return "they (3fp)"
    raise TypeError(f"{p}, {g}, {n}")


def translate_pronouns(p: Person, g: Gender, n: Number) -> str:
    if p is Person.FIRST and g is Gender.COMMON and n is Number.SINGULAR:
        return b'\xd7\x90\xd6\xb2\xd7\xa0\xd6\xb4\xd7\x99'.decode()
    if p is Person.SECOND and g is Gender.MASCULINE and n is Number.SINGULAR:
        return  b'\xd7\x90\xd6\xb7\xd7\xaa\xd6\xb8\xd6\xbc\xd7\x94'.decode()
    if p is Person.SECOND and g is Gender.FEMININE and n is Number.SINGULAR:
        return b'\xd7\x90\xd6\xb7\xd7\xaa\xd6\xb0\xd6\xbc'.decode()
    if p is Person.THIRD and g is Gender.MASCULINE and n is Number.SINGULAR:
        return b'\xd7\x94\xd7\x95\xd6\xbc\xd7\x90'.decode()
    if p is Person.THIRD and g is Gender.FEMININE and n is Number.SINGULAR:
        return b'\xd7\x94\xd6\xb4\xd7\x99\xd7\x90'.decode()
    if p is Person.FIRST and g is Gender.COMMON and n is Number.PLURAL:
        return (
            b'\xd7\x90\xd6\xb2\xd7\xa0\xd6\xb7\xd7\x97'
            b'\xd6\xb0\xd7\xa0\xd7\x95\xd6\xbc'
        ).decode()
    if p is Person.SECOND and g is Gender.MASCULINE and n is Number.PLURAL:
        return b'\xd7\x90\xd6\xb7\xd7\xaa\xd6\xb6\xd6\xbc\xd7\x9d'.decode()
    if p is Person.SECOND and g is Gender.FEMININE and n is Number.PLURAL:
        return b'\xd7\x90\xd6\xb7\xd7\xaa\xd6\xb6\xd6\xbc\xd7\x9f'.decode()
    if p is Person.THIRD and g is Gender.MASCULINE and n is Number.PLURAL:
        return b'\xd7\x94\xd6\xb5\xd7\x9d'.decode()
    if p is Person.THIRD and g is Gender.FEMININE and n is Number.PLURAL:
        return b'\xd7\x94\xd6\xb5\xd7\x9f'.decode()
    raise TypeError(f"{p}, {g}, {n}")