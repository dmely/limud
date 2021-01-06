-- Vocabulary list and user favorites

DROP TABLE IF EXISTS vocabulary;
DROP TABLE IF EXISTS favorites;

-- All words have the following attributes:
--   id: Global, unique identifier 
--   text: The word itself, in Hebrew
--   description: The extended translation of the word
--   category: Whether the word is a noun, verb, adjective, adverb ...
--     See also the words.GrammaticalCategory Python enum.
--   chapter: Chapter in which the word was introduced.
--
-- In addition, nouns have the following, additional attributes:
--   gender: Whether the word is feminine or masculine.
--     See also the words.NounGender Python enum.
--   plabs: PLural (ABSolute form). Specified when irregular.
--   sgcst: SinGular (ConSTruct form). Specified when irregular.
--   plcst: PLural (ConSTruct form). Specified when irregular.

CREATE TABLE vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    description TEXT NOT NULL,
    category INTEGER NOT NULL,
    chapter INTEGER,
    gender INTEGER
    plabs TEXT,
    sgcst TEXT,
    plcst TEXT
);

CREATE TABLE favorites (
    word_id INTEGER NOT NULL,
    FOREIGN KEY (word_id) REFERENCES vocabulary (id)
);