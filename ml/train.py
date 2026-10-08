"""Train, validate and test every model, then write models/metrics.json.

Usage:
    python -m ml.train                      # all models
    python -m ml.train --models cnn lstm    # a subset (existing metrics are kept for the rest)
"""
import argparse
import json
import time

import numpy as np

import config
from ml import classical, deep
from ml.data import load_split
from ml.evaluation import best_threshold, evaluate
from ml.preprocessing import basic_clean

ALL_MODELS = ["logistic_regression", "random_forest", "svm", "cnn", "lstm", "roberta"]
DISPLAY_NAMES = {
    "logistic_regression": "Logistic Regression (TF-IDF)",
    "random_forest": "Random Forest (TF-IDF)",
    "svm": "Support Vector Machine (TF-IDF)",
    "cnn": "Convolutional Neural Network (CNN)",
    "lstm": "Long Short-Term Memory (BiLSTM)",
    "roberta": "RoBERTa (Transformer)",
}


def _record(metrics, name, model_probs_valid, model_probs_test, valid, test, seconds):
    model_probs_valid, model_probs_test = np.asarray(model_probs_valid), np.asarray(model_probs_test)
    # The decision threshold is tuned on validation data only; the test set stays untouched.
    threshold = best_threshold(valid["label"], model_probs_valid)
    by_dataset = {}
    for ds, part in test.groupby(test["dataset"].str.split("-").str[0]):
        by_dataset[ds] = evaluate(part["label"], model_probs_test[part.index], threshold)
    metrics["models"][name] = {
        "display_name": DISPLAY_NAMES[name],
        "threshold": threshold,
        "validation": evaluate(valid["label"], model_probs_valid, threshold),
        "test": evaluate(test["label"], model_probs_test, threshold),
        "test_by_dataset": by_dataset,
        "train_seconds": round(seconds, 1),
    }
    np.savez_compressed(config.MODELS_DIR / f"probs_{name}.npz", valid=model_probs_valid, test=model_probs_test)
    t = metrics["models"][name]["test"]
    print(f"==> {name} (threshold {threshold:.2f}): acc={t['accuracy']:.4f} prec={t['precision']:.4f} "
          f"rec={t['recall']:.4f} f1={t['f1']:.4f}")
    _save(metrics)


def _save(metrics):
    scored = {n: m["validation"]["f1"] for n, m in metrics["models"].items()}
    metrics["best_model"] = max(scored, key=scored.get) if scored else None
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    config.METRICS_FILE.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def main(selected):
    train, valid, test = (load_split(s).reset_index(drop=True) for s in ("train", "valid", "test"))
    print(f"train={len(train)} valid={len(valid)} test={len(test)}")
    metrics = {"models": {}}
    if config.METRICS_FILE.exists():
        metrics = json.loads(config.METRICS_FILE.read_text(encoding="utf-8"))
    metrics["dataset"] = {"train": len(train), "valid": len(valid), "test": len(test),
                          "sources": ["FakeNewsNet (PolitiFact, GossipCop)", "LIAR"]}

    classical_names = [m for m in selected if m in classical.NAMES]
    if classical_names:
        start = time.time()
        trained = classical.train_classical(train["clean_text"], train["label"], classical_names)
        for name, pipe in trained.items():
            classical.save(name, pipe)
            _record(metrics, name, pipe.predict_proba(valid["clean_text"])[:, 1],
                    pipe.predict_proba(test["clean_text"])[:, 1], valid, test, time.time() - start)

    deep_names = [m for m in selected if m in deep.ARCHITECTURES]
    if deep_names:
        vocab = deep.Vocabulary.build(train["clean_text"])
        print(f"Vocabulary size: {len(vocab.itos)}")
        for name in deep_names:
            start = time.time()
            model = deep.train_deep(name, vocab, train["clean_text"], train["label"],
                                    valid["clean_text"], valid["label"], evaluate)
            deep.save(name, model, vocab)
            wrapper = deep.DeepModel(name)
            _record(metrics, name, wrapper.predict_proba(valid["clean_text"]),
                    wrapper.predict_proba(test["clean_text"]), valid, test, time.time() - start)

    if "roberta" in selected:
        from ml import transformer  # heavy import, only when needed
        start = time.time()
        rv, rt = valid["text"].map(basic_clean), test["text"].map(basic_clean)
        model = transformer.train_roberta(train["text"].map(basic_clean), train["label"],
                                          rv, valid["label"], evaluate)
        _record(metrics, "roberta", model.predict_proba(rv), model.predict_proba(rt),
                valid, test, time.time() - start)

    print(f"Best model (validation F1): {metrics['best_model']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", choices=ALL_MODELS, default=ALL_MODELS)
    main(parser.parse_args().models)
