import logging
import re
import requests
from dataclasses import dataclass
from dataclasses import field
from requests import Response
from typing import Optional
from typing import List

from bidi.algorithm import get_display
import click
from bs4 import BeautifulSoup

from limud.backend.models.vocabulary import Adjective
from limud.backend.models.vocabulary import Adverb
from limud.backend.models.vocabulary import GrammaticalCategory
from limud.backend.models.vocabulary import Noun
from limud.backend.models.vocabulary import NounGender
from limud.backend.models.vocabulary import Particle
from limud.backend.models.vocabulary import Verb
from limud.backend.models.vocabulary import Word

logging.basicConfig(level=logging.INFO)


# Acceptable <h3> tags based on Wiktionary's recommended style. See:
# - https://en.wiktionary.org/wiki/Wiktionary:Entry_layout#Part_of_speech
# - https://en.wiktionary.org/wiki/Wiktionary:Entry_layout#List_of_headings
# 
# Some pages do not follow the official recommendation. We ignore
# those and hope they represent a tiny minority of the pages.
RECEIVABLE_H3_TAGS = [
    # Parts of speech
    "adjective", "adverb", "ambiposition", "article", "circumposition",
    "classifier", "conjunction", "contraction", "counter", "determiner",
    "ideophone", "interjection", "noun", "numeral", "participle", "particle",
    "postposition", "preposition", "pronoun", "proper noun", "verb",
    # Morphemes
    "circumfix", "combining form", "infix", "interfix", "prefix", "root",
    "suffix",
    # Phrases
    "phrase", "proverb", "prepositional phrase"
]


class UnparsablePageError(Exception):
    """Raised when processing a completely unparsable page, from which
    recovery is impossible.
    """
    def __init__(self, original: Exception, response: Response = None):
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find("title").text
            url = response.url
        except Exception:
            title = "UNKNOWN"
            url = "UNKNOWN"

        self.message = f"'{title}' at URL {url} (original: {str(original)})"
        super().__init__(self.message)


@dataclass
class WiktionaryWordParse:
    """Represents a single word parsed from a Wiktionary page.

    There may be several of these per single page (e.g., when a word
    can be construed as an adjective or a verb).

    Methods
    -------
    prettyprint()
        Prints the result to console, with colors for clarity.
    as_word() -> limud.models.Word
        Converts this instance to a Word (from the ORM).
    """
    url: str
    word: str
    category: str
    meanings: List[str] = field(default_factory=list)
    examples: List[Optional[str]] = field(default_factory=list)
    binyan: Optional[str] = None  # Obviously only verbs set this

    def prettyprint(self):
        if self.binyan is not None:
            _safeprint(
                f"({self.category}, {self.binyan}) {self.word}:", fg="cyan"
            )
        else:
            _safeprint(f"({self.category}) {self.word}:", fg="cyan")

        for i, (m, e) in enumerate(zip(self.meanings, self.examples)):
            if len(self.meanings) > 1:
                # If there are multiple meanings, number them
                _safeprint(f"{i + 1}. {m}", fg="white", indent=2)
            else:
                _safeprint(f"{m}", fg="white", indent=2)

            if e is not None:
                _safeprint(f"{e}", fg="yellow", indent=4)

    def as_word(self) -> Word:
        try:
            description, = self.meanings
        except ValueError:
            description = "; ".join(
                f"{i + 1}. {m}" for i, m in enumerate(self.meanings)
            )
        description = description.capitalize()
            
        try:
            category = GrammaticalCategory(self.category)
        except ValueError:
            category = GrammaticalCategory.PARTICLE

        if category is GrammaticalCategory.NOUN:
            gender = NounGender.infer_from_word(self.word)
            return Noun(
                hebrew=self.word,
                description=description,
                category=category,
                chapter=-1,
                gender=gender,
            )
        elif category is GrammaticalCategory.VERB:
            kwargs = dict(
                hebrew=self.word,
                description="",
                category=category,
                chapter=-1,
            )

            # We need to carefully map the way Wiktionary spells the
            # binyanim (en.wiktionary.org/wiki/Appendix:Hebrew_verbs)
            # to how the constructor of 'Verb' does.
            if self.binyan == "pa'al":
                kwargs["description"] = description
            elif self.binyan == "nif'al":
                kwargs["nifal"] = description
            elif self.binyan == "pi'el":
                kwargs["piel"] = description
            elif self.binyan == "pu'al":
                kwargs["pual"] = description
            elif self.binyan == "hif'il":
                kwargs["hifil"] = description
            elif self.binyan == "huf'al":
                # Note the qubbuts / cholam difference
                kwargs["hofal"] = description
            elif self.binyan == "hitpa'el":
                kwargs["hitpael"] = description
            else:
                # Here we throw our hands in the air (e.g., hitpual)
                raise ValueError(f"Unsupported binyan: {self.binyan}")
            return Verb(**kwargs)

        elif category is GrammaticalCategory.ADJECTIVE:
            return Adjective(
                hebrew=self.word,
                description=description,
                category=category,
                chapter=-1,
            )
        elif category is GrammaticalCategory.ADVERB:
            return Adverb(
                hebrew=self.word,
                description=description,
                category=category,
                chapter=-1,
            )
        elif category is GrammaticalCategory.PARTICLE:
            return Particle(
                hebrew=self.word,
                description=description,
                category=category,
                chapter=-1,
            )


def scrape_page_from_wiktionary(url: Optional[str] = None,
                                retry: bool = True,
                                ) -> List[WiktionaryWordParse]:
    """Scrapes a random (Hebrew lemma) page from Wiktionary for words,
    or the page at a custom URL if specified.

    Parameters
    ----------
    url : str | None
        If None, retrieve a page at random. Otherwise, use the
        specified URL.
    retry : bool
        Whether to try a different random page if parsing the current
        page fails. Ignored if an URL argument was passed.

    Returns
    -------
    [limud.wiktionary.WiktionaryWordParse]
        Parsed words from the page.

    Raises
    ------
    limud.wiktionary.UnparsablePageError
        If the page is unparsable and retry is disabled.
    """
    while True:
        response = get_response_from_wiktionary(url)
        try:
            return parse_response_from_wiktionary(response)
        except UnparsablePageError:
            # When the page is not random, there is no point in retrying
            if url is not None:
                raise
            # Otherwise, the URL is None and a new page will get sampled
            if retry:
                logging.info("Could not parse page, trying another one")
                continue
            # If the URL is None but we do not retry, just fail
            raise


def get_response_from_wiktionary(url: Optional[str]) -> Response:
    """Retrieves a random Hebrew lemma (word) from Wiktionary. If a
    URL is specified, retrieve the contents of that page instead.

    Parameters
    ----------
    url : str | None
        If specified, do not sample a random page, but retrieve that
        page instead.

    Returns
    -------
    requests.Response
    """
    if url is not None:
        logging.debug("Retrieving word from page.")
        return requests.get(url)
    
    logging.debug("Requesting random word.")
    url = 'https://en.wiktionary.org/wiki/Special:RandomInCategory'

    headers = {
        'Referer': 'https://en.wiktionary.org/wiki/Special:RandomInCategory',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://en.wiktionary.org',
    }

    payload = {
        'wpcategory': 'Hebrew lemmas',
        'wpEditToken': '+\\',
        'title': 'Special:RandomInCategory',
        'redirectparams': '',
    }

    response = requests.post(
        url,
        headers=headers,
        data=payload,
        allow_redirects=True,
    )

    logging.info("Redirected to: %s", response.url)

    return response


def parse_response_from_wiktionary(
        response: Response) -> List[WiktionaryWordParse]:
    """Scrapes an HTTP response containing a Wiktionary page, and
    returns a list of words parsed from that page.

    Parameters
    ----------
    response: requests.Response
        HTTP response containing the page to be scraped.

    Returns
    -------
    [limud.wiktionary.WiktionaryWordParse]
        Parsed words from the page.

    Raises
    ------
    limud.wiktionary.UnparsablePageError
        When the page is completely unparsable. Partially parsable
        pages will not cause this exception to be raised.
    """
    soup = BeautifulSoup(response.text, 'html.parser')
    page_title = soup.find("h1").text
    logging.info(get_display(f"Page title: {page_title}"))

    # Get the <span> within an <h2> that specifies "Hebrew"
    # This is to avoid Aramaic, Yiddish meanings
    try:
        span_tag, = soup.find_all(
            lambda tag: tag.name == "span" and
                        tag.text == "Hebrew" and
                        tag.parent.name == "h2"
        )
    except ValueError as e:
        raise UnparsablePageError(e, response=response)

    # The parent of that <h2> is a <div> that contains
    # various meanings under <h3>s (and so on)
    h2_tag = span_tag.parent
    div_tag = h2_tag.parent

    # Each <h3> corresponds to a grammatical type, e.g., verb or noun
    h3_tags = div_tag.find_all("h3")
    parses = []

    for h3_tag in h3_tags:
        # Each <h3> contains a <span> that has the grammatical type
        category = h3_tag.find_next("span").text.lower()

        # If this is not the case, the page is likely not formatted in
        # the recommended style. If so, we give up.
        if category not in RECEIVABLE_H3_TAGS:
            logging.warn(
                "Ill-formed page %s with category %s. Skipping this tag.",
                response.url, category,
            )
            continue

        # Each <p> contains a possible spelling with niqqudot
        # The actual word is in <strong>
        p_tag = h3_tag.find_next_sibling("p")
        try:
            strong_tag, = p_tag.find_all("strong", lang="he")
        except ValueError:
            # This case also covers when a word has multiple <h2> tags,
            # as when there are multiple languages like Hebrew, Ladino...
            continue

        # If it's a verb its binyan should be annotated
        binyan = None
        if category == "verb":
            a_tag, = p_tag.find_all("a", href="/wiki/Appendix:Hebrew_verbs")
            binyan = _extract_binyan(a_tag.text)

        word = _remove_ktiv_male(strong_tag.text)
        parse = WiktionaryWordParse(
            url=response.url,
            word=word,
            category=category,
            binyan=binyan,
        )
        
        # Each <ol> contains a list of possible meanings
        ol_tag = p_tag.find_next_sibling("ol")

        # ... and each <li> is one meaning
        li_tags = ol_tag.find_all("li", recursive=False)

        for li_tag in li_tags:
            # Skip spurious <li> tags that are empty
            if not li_tag.text:
                continue

            # Remove any transliteration from the meaning,
            # because users really should know how to read
            transliteration = li_tag.find_all(lambda tag:
                tag.name == "span" and
                set(tag.get("class", [])) & {
                    "mention-gloss-paren",
                    "mention-tr",
                }
            )

            for tag in transliteration:
                tag.decompose()

            meaning, example = _split_meaning_example(li_tag)
            parse.meanings.append(meaning)        
            parse.examples.append(example)
        
        parses.append(parse)

    return parses


def _split_meaning_example(li_tag):
    """One <li> tag represents one meaning, typically."""
    example = None

    try:
        ul_tag = li_tag.ul.extract()
    except AttributeError:
        # <li> may not have a child <ul>, then ignore
        pass
    else:
        example = ul_tag.text.replace("\n", " ")

    # Less common: no quotation drop-down, just a <dl> tag
    try:
        dl_tag = li_tag.dl.extract()
    except AttributeError:
        # <li> may not have a child <dl>, then ignore
        pass
    else:
        example = dl_tag.text.replace("\n", " ")

    meaning = li_tag.text.replace("\n", " ")

    return meaning, example


# So many backslashes... To escape the pattern for '\' (single
# backslash) passed to re.compile(), that function needs to receive
# '\\' (double backslash). But then, in order to build the string '\\'
# Python needs to receive the literal '\\' for each '\', so 2x2 = 4
# backslashes total.
# 
# Thank you for coming to my TED talk.
_regex_spellings = re.compile(
    u"(?P<ktiv_male>[\u0590-\u05ff]+)\s*\\\\\s*"
    u"(?P<ktiv_menuqad>[\u0590-\u05ff\ufb1d-\ufb4f]+)"
)

def _remove_ktiv_male(text: str) -> str:
    """Sometimes Wiktionary presents both spellings of a word, with
    and without diacritics, side-by-side, separated by a backslash.

    We do not need the latter.
    """
    match = _regex_spellings.fullmatch(text)

    try:
        return match["ktiv_menuqad"]
    except TypeError:
        logging.info("No ktiv male found in the word.")
        return text


_regex_binyan = re.compile("(?P<binyan>[a-zA-Z']+) construction.*")

def _extract_binyan(text: str) -> str:
    """When the word is a verb, the binyan is specified thereafter.
    
    This extracts the binyan and matches it to the way it is spelled
    in this codebase.
    """
    return _regex_binyan.fullmatch(text)["binyan"]


def _safeprint(string, indent=0, **kwargs):
    click.secho(" " * indent + get_display(string), **kwargs)
