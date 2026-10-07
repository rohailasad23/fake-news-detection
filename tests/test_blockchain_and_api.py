"""Integration tests: a throwaway in-memory Ganache chain + the Flask API.

Requires `npm install` in blockchain/. Model-dependent tests are skipped until models are trained.
"""
import shutil
import subprocess
import time

import pytest
from web3 import Web3

import config
from blockchain.ledger import Ledger

PORT = 8599
GANACHE = config.BLOCKCHAIN_DIR / "node_modules" / ".bin" / "ganache"


@pytest.fixture(scope="module")
def ledger(tmp_path_factory):
    exe = shutil.which("ganache", path=str(GANACHE.parent))
    if exe is None:
        pytest.skip("Ganache not installed (run `npm install` in blockchain/)")
    proc = subprocess.Popen([exe, "--wallet.deterministic", "--server.port", str(PORT), "--logging.quiet"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{PORT}"
    for _ in range(60):
        if Web3(Web3.HTTPProvider(url)).is_connected():
            break
        time.sleep(0.5)
    original = config.DEPLOYMENT_FILE
    config.DEPLOYMENT_FILE = tmp_path_factory.mktemp("chain") / "deployment.json"
    try:
        yield Ledger(rpc_url=url).connect()
    finally:
        config.DEPLOYMENT_FILE = original
        proc.terminate()
        proc.wait(timeout=10)


TEXT = "Scientists confirm that drinking seawater cures all known diseases overnight"


def test_trusted_sources_seeded(ledger):
    assert "reuters.com" in ledger.trusted_sources()
    assert ledger.is_trusted("bbc.com")


def test_register_and_trace(ledger):
    before = ledger.verify(TEXT, "fakesite.net")
    assert before["status"] == "Unverified" and not before["previously_recorded"]

    record, created = ledger.register(TEXT, "fakesite.net", "", "Fake", 0.9312, "svm")
    assert created and record["source"] == "fakesite.net" and record["label"] == "Fake"
    assert record["confidence"] == pytest.approx(0.9312)
    assert record["tx_hash"].startswith("0x") and record["integrity_verified"]

    # Re-registering identical (case/whitespace-insensitive) content is a no-op: origin is immutable.
    again, created = ledger.register(TEXT.upper(), "reuters.com", "", "Real", 0.6, "svm")
    assert not created and again["source"] == "fakesite.net"

    # Claiming a different source for recorded content is flagged.
    assert ledger.verify(TEXT, "reuters.com")["status"] == "Source Mismatch"
    assert ledger.get_record(record["content_hash"])["source"] == "fakesite.net"


def test_verified_source(ledger):
    v = ledger.verify("Parliament passes the annual budget after long debate", "", "https://www.reuters.com/x")
    assert v["status"] == "Verified" and v["claimed_source"] == "reuters.com"
    assert ledger.verify("Some other unrelated headline here", "")["status"] == "No Source"


def test_add_remove_source(ledger):
    ledger.add_trusted_source("https://www.example-news.org/")
    assert ledger.is_trusted("example-news.org")
    ledger.remove_trusted_source("example-news.org")
    assert not ledger.is_trusted("example-news.org")


def test_contract_rejects_duplicates(ledger):
    h = Web3.keccak(text="dup")
    ledger._send(ledger.contract.functions.registerNews(h, "a", "", "Real", 5000, "x"))
    with pytest.raises(Exception):
        ledger.contract.functions.registerNews(h, "b", "", "Fake", 5000, "x").call({"from": ledger.account})


# ---------------------------------------------------------------- Flask API
@pytest.fixture(scope="module")
def client(ledger):
    import app as app_module
    app_module.ledger = ledger
    return app_module.app.test_client()


def test_api_validation(client):
    assert client.post("/api/analyze", json={"text": ""}).status_code == 400
    assert client.post("/api/analyze", json={"text": "too short"}).status_code == 400
    assert client.post("/api/analyze", data="nope").status_code == 400
    assert client.get("/api/records/0x1234").status_code == 400
    assert client.get("/api/records/0x" + "ab" * 32).status_code == 404


def test_api_status_and_sources(client):
    s = client.get("/api/status").get_json()
    assert s["blockchain"]["connected"]
    assert "reuters.com" in client.get("/api/sources").get_json()["sources"]


def test_api_analyze_end_to_end(client):
    import app as app_module
    if not app_module.predictor.available_models:
        pytest.skip("No trained models")
    text = "Breaking: celebrity secretly replaced by a body double, insiders claim"
    for model in app_module.predictor.available_models:
        r = client.post("/api/analyze", json={"text": text, "source": "gossipsite.com", "model": model})
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        assert body["prediction"]["label"] in ("Real", "Fake")
        assert 0.5 <= body["prediction"]["confidence"] <= 1
        assert body["blockchain"]["available"]
        assert body["blockchain"]["record"]["content_hash"].startswith("0x")
    records = client.get("/api/records").get_json()
    assert records["total"] >= 1
    traced = client.post("/api/verify", json={"text": text, "source": "bbc.com"}).get_json()
    assert traced["status"] == "Source Mismatch"
