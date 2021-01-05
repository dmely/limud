import enum
import logging
from typing import Optional
from typing import Union

LOG = logging.getLogger(__name__)
QAMATS_HE_BYTES = b'\xd6\xb8\xd7\x94'


class WordType(enum.IntEnum):
    NOUN = 1
    VERB = 2
    ADJECTIVE = 3
    OTHER = 99


class WordGender(enum.IntEnum):
    MASCULINE = 1
    FEMININE = 2


class Word:
    def __init__(self,
                 text: str,
                 description: str,
                 kind: WordType = WordType.OTHER,
                 from_chapter: int = -1):

        self.text = text
        self.description = description
        self.kind = kind
        self.from_chapter = from_chapter

        if kind == WordType.OTHER:
            LOG.warn("Input word %s without a word type!", text)

        if from_chapter == -1:
            LOG.warn("Input word %s does not have a source chapter!", text)


class Adjective(Word):
    def __init__(self, text: str, description: str):
        super().__init__(
            text=text,
            description=description,
            kind=WordType.ADJECTIVE)


class Verb(Word):
    def __init__(self, text: str, description: str):
        super().__init__(
            text=text,
            description=description,
            kind=WordType.VERB)


class Noun(Word):
    def __init__(self,
                 text: str,
                 description: str,
                 gender: Optional[WordGender] = None,
                 plural: Optional[str] = None,
                 construct: Optional[str] = None,
                 plural_construct: Optional[str] = None):

        super().__init__(
            text=text,
            description=description,
            kind=WordType.NOUN)

        self.gender = gender or self.infer_gender(text)
        self.plural = plural
        self.construct = construct
        self.plural_construct = plural_construct

    @staticmethod
    def infer_gender(text):
        """Infers the gender of a noun based on the presence of a
        qamats-he ending (in which case the feminine is assumed).

        Obviously, this does not account for exceptions (such as the
        word for 'father').
        """
        if text.encode("utf-8").endswith(QAMATS_HE_BYTES):
            return WordGender.FEMININE
        return WordGender.MASCULINE