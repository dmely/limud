from flask import current_app as app
from flask import url_for
from flask import request
from flask import redirect
from flask import render_template
from flask import session
from flask import Blueprint

from limud.backend.models.vocabulary import create_word_from_form_dict
from limud.backend.models.vocabulary import update_word_from_form_dict
from limud.backend.models.vocabulary import GrammaticalCategory
from limud.backend.models.vocabulary import Word
from limud.extensions import database
from limud.routes.vocabulary._blueprint import vocabulary


@vocabulary.route("/edit/", methods=["GET", "POST"])
def add_word():
    if request.method == "GET":
        app.logger.debug("Editing new word")
        return render_template(
            "edit.html", is_new=1, default_value_category="noun")

    if request.method == "POST":
        app.logger.debug(f"Submitted fields: {request.form}")
        
        word = create_word_from_form_dict(**request.form)
        database.session.add(word)
        database.session.commit()
        
        app.logger.info("Added word: %s to database", word)

        # Go back to a clear edit form in case the user desires
        # to input a lot of words in a row
        return redirect(request.referrer)


@vocabulary.route("/edit/<word_id>", methods=["GET", "POST"])
def edit_word(word_id: str):
    # Where did we come from?
    # - We could only arrive at this page from a flashcard view
    # - The ID of the word being edited is the ID of the word that was being
    #  viewed previously in the flashcard route.
    # - We don't need extra args / query strings in the route below since all
    #  the correct state should still be in flask.session.
    # Note that using the referrer URL does not work because redirect() acts
    # a bit strange.
    referrer_url = url_for("vocabulary.review")

    if not word_id:
        app.logger.error("Invalid: edit word without a word ID! Redirecting.")

        # Do not go back to referrer_url since this should never happen!
        return redirect(url_for("home.index"))

    word = Word.query.get(word_id)
    if word is None:
        app.logger.error("Could not find word with desired ID %s", word_id)

        # Do not go back to referrer_url since this should never happen!
        return redirect(url_for("home.index"))

    app.logger.debug("Loaded word %s for edition", word)

    if request.method == "GET":
        default_values = {
            "default_value_hebrew": word.hebrew,
            "default_value_description": word.description,
            "default_value_chapter": word.chapter,
            "default_value_category": word.category.value,
            "default_value_gender": "",
            "default_value_plabs": "",
            "default_value_sgcst": "",
            "default_value_plcst": "",
            "default_value_nifal": "",
            "default_value_piel": "",
            "default_value_pual": "",
            "default_value_hifil": "",
            "default_value_hofal": "",
            "default_value_hitpael": "",
            "default_value_pladj": "",
            "default_value_femadj": "",
        }
            
        if word.category is GrammaticalCategory.NOUN:
            default_values.update({
                "default_value_gender": word.gender,
                "default_value_plabs": word.plabs,
                "default_value_sgcst": word.sgcst,
                "default_value_plcst": word.plcst,
            })

        if word.category is GrammaticalCategory.ADJECTIVE:
            default_values.update({
                "default_value_pladj": word.pladj,
                "default_value_femadj": word.femadj,
            })

        if word.category is GrammaticalCategory.VERB:
            default_values.update({
                "default_value_nifal": word.nifal,
                "default_value_piel": word.piel,
                "default_value_pual": word.pual,
                "default_value_hifil": word.hifil,
                "default_value_hofal": word.hofal,
                "default_value_hitpael": word.hitpael,
            })

        app.logger.debug("Editing existing word: %s", word)
        return render_template("edit.html", is_new=0, **default_values)

    if request.method == "POST":
        if "delete_button_press" in request.form:
            word_id = word.id

            database.session.delete(word)
            database.session.commit()
            app.logger.warn("Deleted word.")

            # Upon successful delete, remove the reference to the deleted word
            # from the current run...
            session["word_ids"].remove(word_id)
            num_remaining_words = len(session["word_ids"])

            if num_remaining_words:
                # If there is 1 or more word left, also update the index
                # and go back to the preceding flashcard
                session["index"] = (session["index"] - 1) % num_remaining_words
                return redirect(referrer_url)
            else:
                session.pop("index")
                return redirect(url_for("home.index"))

        app.logger.debug(f"Submitted fields: {request.form}")        
        update_word_from_form_dict(word, **request.form)
        database.session.commit()

        app.logger.info("Updated existing word: %s", word)
        return redirect(referrer_url)
