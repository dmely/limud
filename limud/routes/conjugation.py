import enum
import http
import random
from typing import List

from flask import current_app as app
from flask import url_for
from flask import request
from flask import redirect
from flask import render_template
from flask import session
from flask import Blueprint
from sqlalchemy import and_
from sqlalchemy import or_

from limud.backend.flashcards import format_any_stray_hebrew
from limud.backend.flashcards import FlashcardRunState
from limud.backend.flashcards import FlashcardSide
from limud.backend.models.vocabulary import GrammaticalCategory
from limud.backend.models.vocabulary import Word
from limud.backend.models.vocabulary import create_word_from_form_dict
from limud.backend.models.vocabulary import update_word_from_form_dict
from limud.backend.models.conjugation import get_conjugation
from limud.backend.models.conjugation import label_pronouns
from limud.backend.models.conjugation import label_tense
from limud.backend.models.conjugation import translate_pronouns
from limud.backend.models.conjugation import unpack
from limud.backend.models.conjugation import Binyan
from limud.backend.models.conjugation import Gender
from limud.backend.models.conjugation import Number
from limud.backend.models.conjugation import Person
from limud.backend.models.conjugation import Tense
from limud.backend.models.conjugation import ConjugatedVerb
from limud.extensions import database


conjugation = Blueprint(
    "conjugation", __name__,
    template_folder="templates",
    static_folder="static")


@enum.unique
class PronounLanguage(enum.Enum):
    ENGLISH = "en"
    HEBREW = "he"


@conjugation.route("/conjugation/<binyan>", methods=["GET", "POST"])
def review(binyan: str):
    """Display a conjugation table given a binyan (stem).

    Optionally, each entry may be editable depending on the query
    string parameter 'edit'.

    The query string parameter 'pronouns_lang' determines whether the
    pronouns are printed in English or Hebrew.
    """
    edit = int(request.args.get("edit", 0))
    binyan = Binyan(binyan)
    pronouns_lang = PronounLanguage(request.args.get("pronouns_lang", "he"))

    if request.method == "GET":
        app.logger.debug("Editing conjugation table for %s", binyan)
        edit = int(request.args.get("edit", 0))

        return render_template(
            "table.html",
            edit=edit,
            binyan=binyan,
            pronouns_lang=pronouns_lang.value,
        )

    if request.method == "POST":
        if request.form["button_press"] == "save":
            app.logger.debug(f"Submitted fields: {request.form}")

            for key, hebrew in request.form.items():
                try:
                    bitfield = int(key)
                except ValueError:
                    app.logger.debug("Skipping form item %s ", key)
                    continue

                tense, person, gender, number = unpack(bitfield)

                # First, check if this conjugation (combination of tense,
                # person, gender, number) already exists in the database.
                # 
                # If so, we should retrieve that row and update its
                # columns rather than create a new row.
                conjugation = get_conjugation(
                    binyan=binyan,
                    tense=tense,
                    person=person,
                    gender=gender,
                    number=number,
                )

                if conjugation is None:
                    conjugation = ConjugatedVerb(
                        hebrew=hebrew,
                        binyan=binyan,
                        tense=tense,
                        person=person,
                        gender=gender,
                        number=number,
                    )

                    database.session.add(conjugation)
                    app.logger.info("Adding new conjugation: %s", conjugation)
                else:
                    conjugation.hebrew = hebrew
                    app.logger.info("Updating conjugation: %s", conjugation)

            database.session.commit()
            app.logger.info("Committed full conjugation table to DB.")
            
            return "", http.HTTPStatus.NO_CONTENT


@conjugation.route("/conjugation/practice/", methods=["GET", "POST"])
def practice():
    state = FlashcardRunState.from_flask_session()
    pronouns_lang = PronounLanguage(request.args.get("pronouns_lang", "he"))

    # Process button clicks
    if request.method == "POST":
        if request.form["button_press"] == "flip":
            app.logger.debug("Received request to flip")

            # Note that once a card has been flipped, we cannot flip it back
            state.side = FlashcardSide.FRONT

        # User indicates they got the word right: Remove word from the set of 
        # words being considered. No need to update the index since the length
        # of the word list has changed. Display the prompt side again for the
        # card next in line.
        if request.form["button_press"] == "correct":
            app.logger.debug("Received request for correct")
            state.words.pop(state.index)
            state.progress[0] += 1
            state.side = FlashcardSide.BACK
            
        # User indicates they got the word wrong: Move on to the next word and
        # display the prompt side again for the card next in line.
        if request.form["button_press"] == "incorrect":
            app.logger.debug("Received request for incorrect")
            state.index += 1
            state.progress[0] += 1
            state.side = FlashcardSide.BACK

    if not state.words:
        app.logger.info("Finished current run. Good job!")
        return redirect(url_for("home.index"))

    # New run: Make sure index is valid wrt. new word list length
    if state.index == len(state.words):
        app.logger.info("Finished a run, shuffling remaining words.")
        random.shuffle(state.words)
        state.progress = [0, len(state.words)]
        state.index = 0

    conjugation = ConjugatedVerb.query.get(state.words[state.index])
    app.logger.info("Retrieved word: %s from database", conjugation)
        
    if state.side is FlashcardSide.FRONT:
        content = conjugation.hebrew
        app.logger.debug("Showing front of flashcard ")
    elif state.side is FlashcardSide.BACK:
        query_text_parts = [
            conjugation.binyan.value.capitalize(),
            label_tense(conjugation.tense),
        ]

        if (conjugation.tense is Tense.INFINITIVE_ABSOLUTE or
            conjugation.tense is Tense.INFINITIVE_CONSTRUCT):

            # If the tense is an infinitive, we should disregard pronouns
            # In fact, labeling/translating them will fail, because the
            # null pronoun (person=0, gender=0, number=0) corresponds to
            # a hypothetical 'first person masculine singular', which does
            # not exist in Hebrew!
            pass
        elif pronouns_lang is PronounLanguage.ENGLISH:
            pronouns_string = label_pronouns(
                conjugation.person,
                conjugation.gender,
                conjugation.number,
            )
            pronouns_string = format_any_stray_hebrew(pronouns_string)
            query_text_parts.append(pronouns_string)
        elif pronouns_lang is PronounLanguage.HEBREW:
            pronouns_string = translate_pronouns(
                conjugation.person,
                conjugation.gender,
                conjugation.number,
            )
            pronouns_string = format_any_stray_hebrew(pronouns_string)
            query_text_parts.append(pronouns_string)

        content = ", ".join(query_text_parts) + "?"
        app.logger.debug("Showing back of flashcard")
    else:
        raise ValueError("Invalid value for session variable 'side'!")

    # Save state before leaving function
    state.to_flask_session()
    app.logger.debug(
        "Game state: button press = %s, state = %s",
        request.form.get("button_press", None), state,
    )

    # Note: Unlike "review mode" (flashcards), progress[0] is essentially
    # equal to the index (and not index + 1) to avoid ever showing a full 
    # progress bar to 100%, which would reduce the mental reward to the user
    # for completing a run.
    return render_template("practice.html",
        content=content,
        render_hebrew_large=state.side is FlashcardSide.FRONT,
        render_reveal_button=state.side is FlashcardSide.BACK,
        render_favorite_button=False,
        progress_percent=100 * state.progress[0] / state.progress[1],
    )


@conjugation.route("/conjugation/practice/<binyan>", methods=["GET"])
def practice_binyan(binyan: str):
    """Display conjugations for a binyan in random order as
    flashcards.

    Played as a game like the vocabulary flashcards in order to
    practice.
    """
    binyan = Binyan(binyan)
    verbs = query_binyan_and_shuffle(binyan)
    ids = [verb.id for verb in verbs]

    FlashcardRunState(
        words=ids,
        index=0,
        side=FlashcardSide.BACK,
        progress=[0, len(verbs)],
    ).to_flask_session()

    return redirect(url_for(".practice"))


@conjugation.route("/conjugation/practice/all", methods=["GET"])
def practice_all():
    """Display 'representative form' conjugations for all binyanim in
    random order as flashcards.

    Played as a game like the vocabulary flashcards in order to
    practice.

    For an explanation of what 'representative forms' are, refer to
    the documentation of the function 'query_representative_forms_and_
    shuffle()' below.
    """
    verbs = query_representative_forms_and_shuffle()
    ids = [verb.id for verb in verbs]

    FlashcardRunState(
        words=ids,
        index=0,
        side=FlashcardSide.BACK,
        progress=[0, len(verbs)],
    ).to_flask_session()

    return redirect(url_for(".practice"))


def query_representative_forms_and_shuffle() -> List[ConjugatedVerb]:
    """Generates the 'representative forms' across all binyanim, and
    shuffles the results.

    These forms include the third-person masculine singular perfect,
    the infinitives construct and absolute, and the masculine singular
    (active) participle.

    These forms are useful because the rest of a binyan's conjugation
    can generally be derived morphologically from them. For a longer
    explanation, see 'Learning Biblical Hebrew', Kutz & Josberger.
    """
    verbs = ConjugatedVerb.query.filter(or_(
        ConjugatedVerb.tense == Tense.INFINITIVE_ABSOLUTE,  # Inf. Abs.
        ConjugatedVerb.tense == Tense.INFINITIVE_CONSTRUCT,  # Inf. Cst.
        and_(  # 3 m.s. perfect
            ConjugatedVerb.person == Person.THIRD,
            ConjugatedVerb.gender == Gender.MASCULINE,
            ConjugatedVerb.number == Number.SINGULAR,
            ConjugatedVerb.tense == Tense.PERFECT,
        ),
        and_(  # (active) participle
            ConjugatedVerb.person == Person.SECOND,
            ConjugatedVerb.gender == Gender.MASCULINE,
            ConjugatedVerb.number == Number.SINGULAR,
            ConjugatedVerb.tense == Tense.PARTICIPLE_ACTIVE,
        ),
    )).all()

    # Randomize order
    random.shuffle(verbs)
    app.logger.info("Got %i representative forms across binyanim", len(verbs))

    return verbs


def query_binyan_and_shuffle(binyan: Binyan) -> List[ConjugatedVerb]:
    """
    """
    verbs = ConjugatedVerb.query.filter_by(binyan=binyan).all()
    
    # We expect non-sensical conjugations (e.g., a "first-person
    # infinitive") to be represented by an empty string or None.
    verbs = [verb for verb in verbs if verb.hebrew]

    if app.config["CONJUGATION_PRACTICE_EXCLUDE_WAW_CONSECUTIVES"]:
        app.logger.info("Excluding waw consecutive tenses from practice.")
        verbs = [
            verb for verb in verbs if (
                (verb.tense is not Tense.PERFECT_WAW_CONSECUTIVE) and
                (verb.tense is not Tense.IMPERFECT_WAW_CONSECUTIVE)
            )
        ]

    if app.config["CONJUGATION_PRACTICE_EXCLUDE_JUSSIVE_AND_COHORTATIVES"]:
        app.logger.info("Excluding jussives and cohortatives from practice.")
        verbs = [
            verb for verb in verbs
            if verb.tense is not Tense.JUSSIVE_COHORTATIVE
        ]

    # Randomize order
    random.shuffle(verbs)
    app.logger.info("Got %i verbs for stem %s", len(verbs), binyan)

    return verbs