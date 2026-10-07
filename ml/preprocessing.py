"""Text preprocessing with NLTK: cleaning, tokenization, stop-word removal and normalization."""
import re
import string
from functools import lru_cache

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

import config

NLTK_RESOURCES = {
    "punkt": "tokenizers/punkt",
    "punkt_tab": "tokenizers/punkt_tab",
    "stopwords": "corpora/stopwords",
    "wordnet": "corpora/wordnet",
    "omw-1.4": "corpora/omw-1.4",
}

config.NLTK_DIR.mkdir(parents=True, exist_ok=True)
if str(config.NLTK_DIR) not in nltk.data.path:
    nltk.data.path.insert(0, str(config.NLTK_DIR))

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_HTML_RE = re.compile(r"<[^>]+>")
_NON_ALPHA_RE = re.compile(r"[^a-z\s]")
_SPACE_RE = re.compile(r"\s+")


def ensure_nltk_resources():
    """Download the NLTK corpora/models this module needs (only if missing)."""
    for name, path in NLTK_RESOURCES.items():
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(name, download_dir=str(config.NLTK_DIR), quiet=True)


@lru_cache(maxsize=1)
def _stop_words():
    ensure_nltk_resources()
    # Negations change meaning ("not true"), so they are kept.
    return frozenset(stopwords.words("english")) - {"no", "not", "nor"}


@lru_cache(maxsize=1)
def _lemmatizer():
    ensure_nltk_resources()
    return WordNetLemmatizer()


def basic_clean(text):
    """Remove URLs, HTML tags and extra whitespace while keeping natural sentence form.

    Used for RoBERTa, whose sub-word tokenizer relies on casing, punctuation and stop words.
    """
    text = "" if text is None else str(text)
    text = _URL_RE.sub(" ", text)
    text = _HTML_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def tokenize(text):
    """Full NLP pipeline returning normalized tokens.

    lowercase -> strip URLs/HTML -> remove punctuation, digits & special characters ->
    NLTK word tokenization -> stop-word removal -> WordNet lemmatization.
    """
    text = basic_clean(text).lower()
    text = text.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
    text = _NON_ALPHA_RE.sub(" ", text)
    stops = _stop_words()
    lemmatizer = _lemmatizer()
    return [
        lemmatizer.lemmatize(tok)
        for tok in word_tokenize(text)
        if tok not in stops and len(tok) > 1
    ]


def preprocess(text):
    """Return the cleaned, normalized text as a single space-joined string."""
    return " ".join(tokenize(text))
