import re
import textwrap
from typing import Optional

from flask import Markup
from flask import current_app as app

from limud.backend.models.vocabulary import GrammaticalCategory
from limud.backend.models.vocabulary import Word


def description_as_html(word: Word) -> Markup:
    """Formats a word's description as an HTML string.

    Useful to inject into a template with the correct formatting,
    given that the description may contain both Hebrew and Latin text,
    and needs to be formatted non-uniformly.

    Parameters
    ----------
    word : Word

    Returns
    -------
    flask.Markup
        Valid HTML string.
    """
    template = textwrap.dedent("""
        <div style="white-space-collapse: discard;">
        <span style="font-size: 400; color: var(--flashcard-text-minor);">
        ({category_text}{gender_text})
        </span>
        {description_html}
        {endings_html}
        </div>
    """)

    values = {
        "category_text": word.category.value,
        "description_html": make_html_for_description(word.description),
        "endings_html": "",
        "gender_text": "",
    }

    # Depending on the grammatical category of the word, there might
    # be extra information that needs to be formatted and presented.
    if word.category is GrammaticalCategory.NOUN:
        values["gender_text"] = f", {word.gender.value[0]}."
        values["endings_html"] = make_html_for_noun_endings(word)

    if word.category is GrammaticalCategory.ADJECTIVE:
        values["endings_html"] = make_html_for_adjective_endings(word)

    if word.category is GrammaticalCategory.VERB:
        values["description_html"] = make_html_for_verb_binyanim(word)

    app.logger.debug("Assembled word description. Template:\n%s", template)
    html = template.format(**values)
    app.logger.debug("Formatted word description. HTML:\n%s", html)

    return Markup(html)


def make_html_for_noun_endings(word: Word) -> Markup:
    """If a noun has irregular declension, create an HTML string
    presenting that information in the correct formatting.
    """
    assert word.category is GrammaticalCategory.NOUN
    snippets = []
    html = ""

    if word.sgcst:
        snippets.append(textwrap.dedent(f"""
            cst.&nbsp;
            <span class="flashcard-back-hebrew">
            {word.sgcst}
            </span>
        """).replace("\n", ""))

    if word.plabs:
        snippets.append(textwrap.dedent(f"""
            pl.&nbsp;
            <span class="flashcard-back-hebrew">
            {word.plabs}
            </span>
        """).replace("\n", ""))

    if word.plcst:
        snippets.append(textwrap.dedent(f"""
            pl.&nbsp;cst.&nbsp;
            <span class="flashcard-back-hebrew">
            {word.plcst}
            </span>
        """).replace("\n", ""))

    if snippets:
        html = textwrap.dedent(f"""
        <span style="font-size: 400; color: var(--flashcard-text-minor);">
        ({', '.join(snippets)})
        </span>
        """).replace("\n", "")

    return Markup(html)


def make_html_for_adjective_endings(word: Word) -> Markup:
    """If an adjective has irregular declension, create an HTML string
    presenting that information in the correct formatting.
    """
    assert word.category is GrammaticalCategory.ADJECTIVE
    snippets = []
    html = ""

    if word.pladj:
        snippets.append(textwrap.dedent(f"""
            pl.&nbsp;
            <span class="flashcard-back-hebrew">
            {word.pladj}
            </span>
        """).replace("\n", ""))

    if word.femadj:
        snippets.append(textwrap.dedent(f"""
            fem.&nbsp;
            <span class="flashcard-back-hebrew">
            {word.femadj}
            </span>
        """).replace("\n", ""))

    if snippets:
        html = textwrap.dedent(f"""
        <span style="font-size: 400; color: var(--flashcard-text-minor);">
        ({', '.join(snippets)})
        </span>
        """).replace("\n", "")

    return Markup(html)


def make_html_for_verb_binyanim(word: Word) -> Markup:
    """Create an HTML to represent the various meanings of a verbal
    stem per binyan.
    """
    assert word.category is GrammaticalCategory.VERB
    snippets = []
    html = ""

    binyanim_attributes = (
        "qal", "nifal", "piel", "pual",
        "hifil", "hofal", "hitpael",
    )

    for attribute in binyanim_attributes:
        if attribute == "qal":
            text = getattr(word, "description")
        else:
            text = getattr(word, attribute)

        if text:
            snippets.append(textwrap.dedent(f"""
                <span style="font-size: 600;
                            color: var(--flashcard-text-minor);
                            font-style: italic;">
                {attribute}:&nbsp;&nbsp;
                </span>
                {make_html_for_description(text)}
            """).replace("\n", ""))

    if snippets:
        separator = textwrap.dedent("""
            <span style="font-size: 400; color: var(--flashcard-text-minor);">
            &nbsp;&semi;&nbsp;
            </span>
        """).replace("\n", "")
        html = textwrap.dedent(f"""{separator.join(snippets)}""")

    return Markup(html)


# Matches any description of a word with multiple meanings that are
# prefixed with a number followed by a dot. For instance:
# "1. First meaning 2. Second meaning 3. Third meaning".
_regex_multiple_meanings = re.compile(
    r"(?P<number>(0|[1-9][0-9]*\.))\s(?P<text>[^\.0-9]+\s*)"
)

def make_html_for_description(text: str) -> Markup:
    """Formats a word's description accordingly.
    
    When a word's description has multiple meanings prefixed with a
    number followed by a dot, each number should look understated,
    while the content that follows is highlighted normally.

    Otherwise (in case of a single meaning, i.e., when the regular
    expression does not match), format the description normally.

    Parameters
    ----------
    text : str
        Description of the word.

    Returns
    -------
    flask.Markup
        Valid HTML string.
    """
    snippets = []

    for match in _regex_multiple_meanings.finditer(text):
        snippets.append(textwrap.dedent(f"""
            <span style="font-size: 400; color: var(--flashcard-text-minor);">
            {match["number"]}&nbsp;
            </span>
            <span style="font-size: 600; color: var(--flashcard-text);">
            {format_any_stray_hebrew(match["text"]).capitalize()}
            </span>
        """))

    if not snippets:
        return Markup(textwrap.dedent(f"""
            <span style="font-size: 600; color: var(--flashcard-text);">
            {format_any_stray_hebrew(text)}
            </span>
        """))

    return Markup("&nbsp;&nbsp;".join(snippets).replace("\n", ""))


# Matches any Hebrew characters, including all Hebrew diacritics
_regex_hebrew = re.compile(u"[\u0590-\u05ff\ufb1d-\ufb4f]+")

def format_any_stray_hebrew(text: str) -> Markup:
    """Encases any contiguous Hebrew characters with a <span> tag with
    a 'flashcard-back-hebrew' CSS class.

    Normally, any Hebrew strings in the flashcard should be formatted
    explicitly (e.g., a custom construct form for a noun). However, in
    some edge cases there are stray Hebrew characters in the (normally
    in English) description, which then are not formatted properly.

    Note that this cannot be entirely solved by defining a CSS
    @font-family with a custom unicode range, since we also need to
    set a custom font-size.

    For example, the following string:

        'The Hebrew םולש means peace.'

    Is converted to the output:

        'The Hebrew <span class="flashcard-back-hebrew">םולש</span>
        means peace.'
    """
    def _set_proper_css_class(match: re.Match) -> str:
        return textwrap.dedent(f"""
            <span class="flashcard-back-hebrew">{match.group(0)}</span>
        """)

    return Markup(_regex_hebrew.sub(_set_proper_css_class, text))
