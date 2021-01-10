from flask import current_app as app

from .models import Word
from .models import database


@app.context_processor
def get_all_chapters():
    """Returns all unique chapter IDs, in sorted order.
    
    This is necessary because the main menu of the application
    contains a drop-down menu referencing each chapter that exists in
    the database.

    The query below implements:
        SELECT DISTINCT vocabulary.chapter AS <?> FROM vocabulary
    """
    query = database.session.query(Word.chapter).distinct()
    chapter_ids = sorted(chapter_id for chapter_id, in query.all())

    return {"all_chapters_ids": chapter_ids}