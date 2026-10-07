from blockchain.ledger import content_hash, normalize_source
from ml.preprocessing import basic_clean, preprocess, tokenize


def test_tokenize_removes_noise_and_stopwords():
    tokens = tokenize("BREAKING!!! The <b>senators</b> are voting at https://x.com/abc in 2024...")
    assert tokens == ["breaking", "senator", "voting"]


def test_negations_are_kept():
    assert "not" in tokenize("This is not true")


def test_basic_clean_keeps_natural_text():
    assert basic_clean("Hello <i>World</i>,  see www.a.com now") == "Hello World , see now"


def test_preprocess_empty():
    assert preprocess("") == ""
    assert preprocess(None) == ""


def test_content_hash_ignores_case_and_whitespace():
    assert content_hash("The  Moon is made of cheese") == content_hash("the moon is made   of CHEESE ")
    assert content_hash("a b c") != content_hash("a b d")


def test_normalize_source():
    assert normalize_source("", "https://www.Reuters.com/world/article-1") == "reuters.com"
    assert normalize_source("BBC.com") == "bbc.com"
    assert normalize_source("  Barack   Obama ") == "barack obama"
    assert normalize_source("") == ""
