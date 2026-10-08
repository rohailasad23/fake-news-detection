"""Loads trained models and classifies news text as Real or Fake."""
import json
import threading

import config
from ml.preprocessing import basic_clean, preprocess
from ml.train import ALL_MODELS, DISPLAY_NAMES


class ModelNotAvailable(Exception):
    pass


def _rescale(prob, threshold):
    """Map a model probability so its tuned decision threshold sits at 0.5.

    The displayed Real/Fake percentages then agree with the label: whichever side of the
    threshold the model falls on is the side above 50%.
    """
    if prob < threshold:
        return 0.5 * prob / threshold
    return 0.5 + 0.5 * (prob - threshold) / (1 - threshold)


class Predictor:
    def __init__(self):
        self._models = {}
        self._lock = threading.Lock()
        self.reload_metrics()

    def reload_metrics(self):
        self.metrics = {"models": {}, "best_model": None}
        if config.METRICS_FILE.exists():
            self.metrics = json.loads(config.METRICS_FILE.read_text(encoding="utf-8"))

    @property
    def available_models(self):
        """Trained models in a stable display order."""
        return [m for m in ALL_MODELS if m in self.metrics.get("models", {})]

    @property
    def default_model(self):
        return self.metrics.get("best_model") or (self.available_models or [None])[0]

    def _get(self, name):
        if name not in self.available_models:
            raise ModelNotAvailable(f"Model '{name}' has not been trained. Run `python -m ml.train`.")
        with self._lock:
            if name not in self._models:
                if name == "roberta":
                    from ml.transformer import RobertaModel
                    self._models[name] = RobertaModel()
                elif name in ("cnn", "lstm"):
                    from ml.deep import DeepModel
                    self._models[name] = DeepModel(name)
                else:
                    from ml.classical import ClassicalModel
                    self._models[name] = ClassicalModel(name)
            return self._models[name]

    def predict(self, text, model_name=None):
        model_name = model_name or self.default_model
        if model_name is None:
            raise ModelNotAvailable("No trained model found. Run `python -m ml.train` first.")
        clean = preprocess(text)
        if model_name != "roberta" and not clean:
            raise ValueError("The text contains no meaningful words after preprocessing.")
        model_input = basic_clean(text) if model_name == "roberta" else clean
        raw_prob = float(self._get(model_name).predict_proba([model_input])[0])
        threshold = self.metrics["models"][model_name].get("threshold", 0.5)
        fake_prob = _rescale(raw_prob, threshold)
        is_fake = raw_prob >= threshold
        return {
            "label": config.LABEL_NAMES[int(is_fake)],
            "confidence": round(fake_prob if is_fake else 1 - fake_prob, 4),
            "probabilities": {"Real": round(1 - fake_prob, 4), "Fake": round(fake_prob, 4)},
            "model": model_name,
            "model_display_name": DISPLAY_NAMES[model_name],
            "processed_text": clean,
        }
