import random

from flask import current_app as app
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import Blueprint

from limud.backend.flashcards import FlashcardSide
from limud.backend.flashcards import FlashcardSorting
from limud.backend.flashcards import FlashcardRunState
from limud.backend.flashcards import make_flashcard_run
from limud.backend.flashcards import description_as_html
from limud.backend.models.vocabulary import GrammaticalCategory
from limud.backend.models.vocabulary import Word
from limud.backend.models.vocabulary import database
from limud.backend.wiktionary import scrape_page_from_wiktionary
from limud.backend.wiktionary import UnparsablePageError
from limud.backend.wiktionary import WiktionaryWordParse


wotm = Blueprint(
    "wotm", __name__,
    template_folder="templates",
    static_folder="static")


@wotm.route("/wotm/", methods=["GET", "POST"])
def display_wotm():
    """Displays the word most recently scraped from Wiktionary.

    Before accessing this route, proper state must be set in the Flask
    session object. See also the docs of 'FlashcardRunState'.
    """
    state = FlashcardRunState.from_flask_session()
    parse = WiktionaryWordParse(**state.words[state.index])
    word = parse.as_word()
    app.logger.debug("Current word: %s", word)

    # Process button clicks
    if request.method == "POST":
        if request.form["button_press"] == "flip":
            app.logger.debug("Received request to flip")
            state.side = ~state.side

    if state.side is FlashcardSide.FRONT:
        content = word.hebrew
        app.logger.debug("Showing front of WOTM")
    elif state.side is FlashcardSide.BACK:
        content = description_as_html(word)
        app.logger.debug("Showing back of WOTM ")
    else:
        raise ValueError("Invalid value for session variable 'side'!")

    # Save state before leaving function
    state.to_flask_session()

    return render_template("wotm.html",
        content=content,
        render_front_of_flashcard=state.side is FlashcardSide.FRONT,
        origin_url=parse.url,
    )


@wotm.route("/wotm/new")
def display_from_scrapping_random():
    """Scrapes a new word from Wiktionary and displays it.

    This works by initializing some state in the Flask session object
    via the FlashcardRunState helper object, and redirecting to the
    .display_wotm route (which assumes that state has been properly
    set up).
    """
    parses = scrape_page_from_wiktionary(retry=True)
    app.logger.debug("Parsed words: %s", *(p.word for p in parses))

    FlashcardRunState(
        words=parses,
        index=0,
        side=FlashcardSide.FRONT,
        progress=[0, len(parses)],
    ).to_flask_session()

    return redirect(url_for(".display_wotm"))


@wotm.route("/wotm/<word>")
def display_from_scrapping_word(word: str):
    """Scrapes a new word from Wiktionary and displays it.

    This works by initializing some state in the Flask session object
    via the FlashcardRunState helper object, and redirecting to the
    .display_wotm route (which assumes that state has been properly
    set up).
    """
    url = f"https://en.wiktionary.org/w/index.php?title={word}"
    parses = scrape_page_from_wiktionary(url=url)
    app.logger.debug("Parsed words: %s", *(p.word for p in parses))

    FlashcardRunState(
        words=parses,
        index=0,
        side=FlashcardSide.FRONT,
        progress=[0, len(parses)],
    ).to_flask_session()

    return redirect(url_for(".display_wotm"))