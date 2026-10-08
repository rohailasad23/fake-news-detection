"""TF-IDF feature extraction + scikit-learn classifiers (Logistic Regression, Random Forest, SVM)."""
import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

import config


def _classifiers():
    return {
        "logistic_regression": LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced"),
        "random_forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=2, n_jobs=-1,
                                                class_weight="balanced", random_state=config.RANDOM_STATE),
        # LinearSVC has no predict_proba; calibration gives a confidence score.
        "svm": CalibratedClassifierCV(LinearSVC(C=0.1, class_weight="balanced"), cv=3),
    }


NAMES = ("logistic_regression", "random_forest", "svm")


def train_classical(train_texts, train_labels, names=NAMES):
    """Fit one TF-IDF pipeline per requested classifier and return {name: pipeline}."""
    models = {}
    for name, clf in _classifiers().items():
        if name not in names:
            continue
        print(f"Training {name} ...")
        pipe = Pipeline([("tfidf", TfidfVectorizer(**config.TFIDF_PARAMS)), ("clf", clf)])
        pipe.fit(train_texts, train_labels)
        models[name] = pipe
    return models


def save(name, pipeline):
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, config.MODELS_DIR / f"{name}.joblib", compress=3)


def load(name):
    return joblib.load(config.MODELS_DIR / f"{name}.joblib")


class ClassicalModel:
    """Inference wrapper: expects preprocessed (clean) text."""

    def __init__(self, name):
        self.name = name
        self.pipeline = load(name)

    def predict_proba(self, clean_texts):
        return self.pipeline.predict_proba(list(clean_texts))[:, 1]
