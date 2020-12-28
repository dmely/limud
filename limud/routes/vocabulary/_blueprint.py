from flask import Blueprint


vocabulary = Blueprint(
    "vocabulary", __name__,
    url_prefix="/vocabulary",
    template_folder="templates",
    static_folder="static",
)
