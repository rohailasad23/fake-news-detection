"""Evaluation metrics (Fake = positive class)."""
import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score)


def best_threshold(y_true, fake_probs):
    """Decision threshold that maximises macro-F1 on (validation) data.

    The data is imbalanced (~31% fake), so a fixed 0.5 cut-off is not optimal for every model.
    """
    y_true = np.asarray(y_true).astype(int)
    fake_probs = np.asarray(fake_probs)
    grid = np.round(np.arange(0.10, 0.91, 0.01), 2)
    scores = [f1_score(y_true, (fake_probs >= t).astype(int), average="macro") for t in grid]
    return float(grid[int(np.argmax(scores))])


def evaluate(y_true, fake_probs, threshold=0.5):
    y_true = np.asarray(y_true).astype(int)
    y_pred = (np.asarray(fake_probs) >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    }
