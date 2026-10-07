"""Flask web application: AI fake news detection + blockchain source traceability."""
import logging
import threading

from flask import Flask, jsonify, render_template, request

import config
from blockchain.ledger import BlockchainUnavailable, Ledger
from ml.predictor import ModelNotAvailable, Predictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
predictor = Predictor()
ledger = Ledger()


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


@app.errorhandler(ApiError)
def _api_error(err):
    return jsonify({"error": err.message}), err.status


def _json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object.")
    return data


def _validated_text(data):
    text = str(data.get("text") or "").strip()
    if not text:
        raise ApiError("Please enter a news article or headline.")
    if len(text) > config.MAX_TEXT_CHARS:
        raise ApiError(f"Text is too long (maximum {config.MAX_TEXT_CHARS} characters).")
    if len(text.split()) < 3:
        raise ApiError("Please enter at least 3 words so the text can be analysed.")
    return text


def _blockchain_error(exc):
    log.warning("Blockchain unavailable: %s", exc)
    return {"available": False, "error": str(exc)}


# ---------------------------------------------------------------- pages
@app.get("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------- API
@app.post("/api/analyze")
def analyze():
    """Classify news text and record/verify its source on the blockchain."""
    data = _json_body()
    text = _validated_text(data)
    source = str(data.get("source") or "").strip()[:200]
    source_url = str(data.get("source_url") or "").strip()[:500]
    model = data.get("model") or None

    try:
        prediction = predictor.predict(text, model)
    except ModelNotAvailable as exc:
        raise ApiError(str(exc), 503)
    except ValueError as exc:
        raise ApiError(str(exc))

    try:
        # Verify against the ledger *before* registering, so the status reflects prior history.
        verification = ledger.verify(text, source, source_url)
        if data.get("record", True):
            record, created = ledger.register(text, source, source_url, prediction["label"],
                                              prediction["confidence"], prediction["model"])
            verification["record"] = record
            verification["newly_recorded"] = created
        verification["available"] = True
    except (BlockchainUnavailable, ConnectionError) as exc:
        verification = _blockchain_error(exc)
    except Exception as exc:  # node errors should never hide the AI result
        log.exception("Blockchain operation failed")
        verification = _blockchain_error(exc)

    return jsonify({"prediction": prediction, "blockchain": verification})


@app.post("/api/verify")
def verify():
    """Trace a news item on the ledger without recording it."""
    data = _json_body()
    text = _validated_text(data)
    try:
        result = ledger.verify(text, str(data.get("source") or ""), str(data.get("source_url") or ""))
    except Exception as exc:
        raise ApiError(f"Blockchain unavailable: {exc}", 503)
    return jsonify(result)


@app.get("/api/records/<content_hash>")
def get_record(content_hash):
    h = content_hash.lower().removeprefix("0x")
    if len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
        raise ApiError("Invalid hash: expected 32 bytes in hex (0x + 64 characters).")
    try:
        record = ledger.get_record(h)
    except Exception as exc:
        raise ApiError(f"Blockchain unavailable: {exc}", 503)
    if record is None:
        raise ApiError("No record with this hash exists on the ledger.", 404)
    return jsonify(record)


@app.get("/api/records")
def list_records():
    limit = min(max(request.args.get("limit", 20, type=int), 1), 100)
    try:
        total, records = ledger.recent_records(limit)
    except Exception as exc:
        raise ApiError(f"Blockchain unavailable: {exc}", 503)
    return jsonify({"total": total, "records": records})


@app.get("/api/sources")
def list_sources():
    try:
        return jsonify({"sources": ledger.trusted_sources()})
    except Exception as exc:
        raise ApiError(f"Blockchain unavailable: {exc}", 503)


@app.get("/api/models")
def list_models():
    predictor.reload_metrics()
    m = predictor.metrics
    return jsonify({
        "default_model": predictor.default_model,
        "dataset": m.get("dataset"),
        "models": [{"name": n, **m["models"][n]} for n in predictor.available_models],
    })


@app.get("/api/status")
def status():
    try:
        chain = ledger.status()
    except Exception as exc:
        chain = {"connected": False, "error": str(exc)}
    return jsonify({
        "models": {"available": predictor.available_models, "default": predictor.default_model},
        "blockchain": chain,
    })


def _warm_up():
    """Load the default model in the background so the first request is fast."""
    try:
        if predictor.default_model:
            predictor.predict("warm up the default model", predictor.default_model)
    except Exception:
        log.exception("Model warm-up failed")


if __name__ == "__main__":
    threading.Thread(target=_warm_up, daemon=True).start()
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False)
