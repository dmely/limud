from flask import current_app as app
from flask import url_for
from flask import request
from flask import redirect
from flask import render_template
from flask import Blueprint

from ..models import create_word_from_form_dict
from ..models import database


edit = Blueprint(
    "edit", __name__,
    template_folder="templates",
    static_folder="static")


@edit.route("/edit/", methods=["GET", "POST"])
def form():
    if request.method == "GET":
        return render_template("edit.html")

    if request.method == "POST":
        app.logger.debug(f"Submitted fields: {request.form}")
        
        word = create_word_from_form_dict(**request.form)
        database.session.add(word)
        database.session.commit()
        
        app.logger.info("Added word: %s to database", word)

        return redirect(url_for("home.index"))
