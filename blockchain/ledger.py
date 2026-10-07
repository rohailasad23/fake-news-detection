"""Ethereum ledger service: compiles/deploys NewsRegistry and records/verifies news sources."""
import json
import re
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse

from web3 import Web3

import config
from ml.preprocessing import basic_clean

_SPACE_RE = re.compile(r"\s+")
_DOMAIN_LIKE_RE = re.compile(r"(https?://)?[\w-]+(\.[\w-]+)+(/\S*)?")


class BlockchainUnavailable(Exception):
    pass


# ---------------------------------------------------------------- hashing / normalisation
def normalize_content(text):
    """Canonical form of the news text so trivial whitespace/case edits map to the same hash."""
    return _SPACE_RE.sub(" ", basic_clean(text).lower()).strip()


def content_hash(text):
    return Web3.keccak(text=normalize_content(text))


def normalize_source(source="", source_url=""):
    """Prefer the publisher domain from the URL; otherwise the lower-cased source name/domain."""
    domain = _domain(source_url)
    if domain:
        return domain
    source = _SPACE_RE.sub(" ", (source or "").strip().lower())
    return _domain(source) if _DOMAIN_LIKE_RE.fullmatch(source) else source


def _domain(url):
    url = (url or "").strip().lower()
    if not url:
        return ""
    netloc = urlparse(url if "://" in url else "http://" + url).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc


# ---------------------------------------------------------------- compile / deploy
def compile_contract():
    import solcx
    if config.SOLC_VERSION not in [str(v) for v in solcx.get_installed_solc_versions()]:
        solcx.install_solc(config.SOLC_VERSION)
    out = solcx.compile_files([str(config.CONTRACT_SOURCE)], output_values=["abi", "bin"],
                              solc_version=config.SOLC_VERSION, evm_version="paris", optimize=True)
    key = next(k for k in out if k.endswith(":NewsRegistry"))
    return out[key]["abi"], out[key]["bin"]


class Ledger:
    def __init__(self, rpc_url=config.ETH_RPC_URL, private_key=config.ETH_PRIVATE_KEY, w3=None):
        self.w3 = w3 or Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        self.private_key = private_key
        self.rpc_url = rpc_url
        self.contract = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------ connection
    @property
    def account(self):
        if self.private_key:
            return self.w3.eth.account.from_key(self.private_key).address
        return self.w3.eth.accounts[0]

    def connect(self):
        """Connect to the node and load (or deploy) the NewsRegistry contract."""
        if self.contract is not None:
            return self
        if not self.w3.is_connected():
            raise BlockchainUnavailable(
                f"Cannot reach Ethereum node at {self.rpc_url}. Start it with `npm run chain` in blockchain/.")
        deployment = self._load_deployment()
        if deployment is None:
            deployment = self.deploy()
        self.contract = self.w3.eth.contract(address=deployment["address"], abi=deployment["abi"])
        return self

    def _load_deployment(self):
        if not config.DEPLOYMENT_FILE.exists():
            return None
        data = json.loads(config.DEPLOYMENT_FILE.read_text(encoding="utf-8"))
        same_chain = data.get("chain_id") == self.w3.eth.chain_id
        if same_chain and self.w3.eth.get_code(data["address"]) not in (b"", b"\x00"):
            return data
        return None  # chain was reset or changed: redeploy

    def deploy(self):
        abi, bytecode = compile_contract()
        factory = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        receipt = self._send(factory.constructor())
        data = {"address": receipt.contractAddress, "abi": abi, "chain_id": self.w3.eth.chain_id,
                "deployed_block": receipt.blockNumber, "rpc_url": self.rpc_url}
        config.DEPLOYMENT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.contract = self.w3.eth.contract(address=data["address"], abi=abi)
        for source in config.DEFAULT_TRUSTED_SOURCES:
            self.add_trusted_source(source)
        print(f"NewsRegistry deployed at {data['address']}")
        return data

    def _send(self, fn):
        """Build, sign (if a private key is configured) and send a transaction; wait for receipt."""
        with self._lock:
            if self.private_key:
                tx = fn.build_transaction({
                    "from": self.account,
                    "nonce": self.w3.eth.get_transaction_count(self.account, "pending"),
                    "chainId": self.w3.eth.chain_id,
                })
                signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            else:
                tx_hash = fn.transact({"from": self.account})
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        if receipt.status != 1:
            raise RuntimeError("Transaction reverted")
        return receipt

    # ------------------------------------------------------------ trusted sources
    def add_trusted_source(self, source):
        source = normalize_source(source)
        if not source:
            raise ValueError("Source must not be empty")
        self._send(self.connect().contract.functions.addTrustedSource(source))
        return source

    def remove_trusted_source(self, source):
        source = normalize_source(source)
        self._send(self.connect().contract.functions.removeTrustedSource(source))
        return source

    def trusted_sources(self):
        return sorted(self.connect().contract.functions.getTrustedSources().call())

    def is_trusted(self, normalized_source):
        return bool(normalized_source) and self.connect().contract.functions.isTrustedSource(
            normalized_source).call()

    # ------------------------------------------------------------ news records
    def get_record(self, chash):
        c = self.connect().contract
        if isinstance(chash, str):
            chash = bytes.fromhex(chash.removeprefix("0x"))
        if not c.functions.isRegistered(chash).call():
            return None
        r = c.functions.getRecord(chash).call()
        record = {
            "content_hash": "0x" + r[0].hex(),
            "source": r[1],
            "source_url": r[2],
            "label": r[3],
            "confidence": r[4] / 10000,
            "model": r[5],
            "timestamp": r[6],
            "registered_at": datetime.fromtimestamp(r[6], tz=timezone.utc).isoformat(),
            "submitter": r[7],
        }
        record.update(self._registration_tx(chash))
        record["integrity_verified"] = self._integrity_ok(record)
        return record

    def _registration_tx(self, chash):
        """Find the transaction that registered this hash via the NewsRegistered event log."""
        deployed_block = json.loads(config.DEPLOYMENT_FILE.read_text(encoding="utf-8")).get("deployed_block", 0)
        logs = self.contract.events.NewsRegistered.get_logs(
            from_block=deployed_block, argument_filters={"contentHash": chash})
        if not logs:
            return {"tx_hash": None, "block_number": None}
        return {"tx_hash": "0x" + logs[0].transactionHash.hex().removeprefix("0x"),
                "block_number": logs[0].blockNumber}

    def _integrity_ok(self, record):
        """Cross-check stored record against the immutable event emitted at registration."""
        if record["tx_hash"] is None:
            return False
        receipt = self.w3.eth.get_transaction_receipt(record["tx_hash"])
        events = self.contract.events.NewsRegistered().process_receipt(receipt)
        return any("0x" + e.args.contentHash.hex() == record["content_hash"]
                   and e.args.source == record["source"] and e.args.label == record["label"]
                   for e in events)

    def register(self, text, source, source_url, label, confidence, model_name):
        """Store the news record on-chain (no-op if the content is already registered)."""
        chash = content_hash(text)
        existing = self.get_record(chash)
        if existing:
            return existing, False
        self._send(self.connect().contract.functions.registerNews(
            chash, normalize_source(source, source_url), (source_url or "").strip(),
            label, int(round(confidence * 10000)), model_name))
        return self.get_record(chash), True

    def verify(self, text, source="", source_url=""):
        """Source verification status for a piece of news content."""
        chash = content_hash(text)
        claimed = normalize_source(source, source_url)
        record = self.get_record(chash)
        origin = record["source"] if record else ""
        trusted = self.is_trusted(claimed)
        origin_trusted = self.is_trusted(origin) if origin else False

        if record and origin and claimed and origin != claimed:
            status, detail = "Source Mismatch", (
                f"This content was first recorded on the ledger from '{origin}', not '{claimed}'.")
        elif trusted:
            status, detail = "Verified", f"'{claimed}' is a verified source on the blockchain registry."
        elif not claimed and record and origin_trusted:
            status, detail = "Verified", f"Originally recorded from verified source '{origin}'."
        elif claimed:
            status, detail = "Unverified", f"'{claimed}' is not in the blockchain registry of verified sources."
        else:
            status, detail = "No Source", "No source was provided, so the origin cannot be verified."
        return {
            "content_hash": "0x" + chash.hex(),
            "claimed_source": claimed,
            "status": status,
            "detail": detail,
            "source_trusted": trusted,
            "previously_recorded": record is not None,
            "record": record,
        }

    def recent_records(self, limit=20):
        c = self.connect().contract
        total = c.functions.recordCount().call()
        hashes = [c.functions.recordHashAt(i).call() for i in range(total - 1, max(total - limit, 0) - 1, -1)]
        return total, [self.get_record(h) for h in hashes]

    def status(self):
        self.connect()
        return {
            "connected": True,
            "rpc_url": self.rpc_url,
            "chain_id": self.w3.eth.chain_id,
            "block_number": self.w3.eth.block_number,
            "contract_address": self.contract.address,
            "account": self.account,
            "record_count": self.contract.functions.recordCount().call(),
        }
