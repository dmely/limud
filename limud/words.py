import enum
import logging
from typing import Optional
from typing import Union

LOG = logging.getLogger(__name__)
QAMATS_HE_BYTES = b'\xd6\xb8\xd7\x94'


class GrammaticalCategory(enum.IntEnum):
    """Grammatical category, or class, of a word in Hebrew."""
    NOUN = 1
    VERB = 2
    ADJECTIVE = 3
    ADVERB = 4


class NounGender(enum.IntEnum):
    """Gender of a noun in Hebrew."""
    MASCULINE = 1
    FEMININE = 2


class Word:
    """Base class for a word in Hebrew

    Attributes
    ----------
    text : str
        Word, in Hebrew.
    description : str
        (Extended) translation in Hebrew, with any notes.
    category : Optional[GrammaticalCategory]
        Grammatical category of the word. See 'GrammaticalCategory'
        for more details.
    chapter : Optional[int]
        Chapter in which the word was introduced; None for no chapter.
    """
    def __init__(self,
                 text: str,
                 description: str,
                 category: Optional[GrammaticalCategory] = None,
                 chapter: Optional[int] = None):

        self.text = text
        self.description = description
        self.category = category
        self.chapter = chapter

        if category is None:
            LOG.warn("Input word %s without a grammatical category!", text)

        if chapter is None:
            LOG.warn("Input word %s does not have a source chapter!", text)


class Adjective(Word):
    """Represents an adjective in Hebrew

    Attributes
    ----------
    See 'Word'.
    """
    def __init__(self, text: str, description: str):
        super().__init__(
            text=text,
            description=description,
            category=GrammaticalCategory.ADJECTIVE)


class Verb(Word):
    """Represents a verb in Hebrew

    Attributes
    ----------
    See 'Word'.
    """
    def __init__(self, text: str, description: str):
        super().__init__(
            text=text,
            description=description,
            category=GrammaticalCategory.VERB)


class Adverb(Word):
    """Represents a verb in Hebrew

    Attributes
    ----------
    See 'Word'.
    """
    def __init__(self, text: str, description: str):
        super().__init__(
            text=text,
            description=description,
            category=GrammaticalCategory.ADVERB)


class Noun(Word):
    """Represents a noun in Hebrew.

    Attributes
    ----------
    gender : Optional[NounGender]
        Specified when the gender cannot be inferred from the ending.
    plabs : Optional[str]
        PLural (ABSolute form). Specified when irregular.
    sgcst : Optional[str]
        SinGular (ConSTruct form). Specified when irregular.
    plcst : Optional[str]
        PLural (ConSTruct form). Specified when irregular.

    See also 'Word' for other attributes.
    """
    def __init__(self,
                 text: str,
                 description: str,
                 gender: Optional[NounGender] = None,
                 plabs: Optional[str] = None,
                 sgcst: Optional[str] = None,
                 plcst: Optional[str] = None):

        super().__init__(
            text=text,
            description=description,
            category=GrammaticalCategory.NOUN)

        if gender is None:
            gender = self.infer_gender(text)

        self.gender = gender
        self.plabs = plabs
        self.sgcst = sgcst
        self.plcst = plcst

    @staticmethod
    def infer_gender(text):
        """Infers the gender of a noun based on the presence of a
        qamats-he ending (in which case the feminine is assumed).

        Obviously, this does not account for exceptions (such as the
        word for 'father').
        """
        if text.encode("utf-8").endswith(QAMATS_HE_BYTES):
            return NounGender.FEMININE
        return NounGender.MASCULINE