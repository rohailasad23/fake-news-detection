"""Central configuration for the Fake News Detection & Source Traceability system."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------- data
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
NLTK_DIR = DATA_DIR / "nltk_data"

FAKENEWSNET_FILES = {
    # file name -> label (1 = fake, 0 = real)
    "politifact_fake.csv": 1,
    "politifact_real.csv": 0,
    "gossipcop_fake.csv": 1,
    "gossipcop_real.csv": 0,
}
FAKENEWSNET_URL = "https://raw.githubusercontent.com/KaiDMML/FakeNewsNet/master/dataset/{name}"
LIAR_URL = "https://www.cs.ucsb.edu/~william/data/liar_dataset.zip"

# LIAR has six truthfulness labels; they are collapsed into the binary Real/Fake task.
LIAR_LABEL_MAP = {
    "true": 0, "mostly-true": 0, "half-true": 0,
    "barely-true": 1, "false": 1, "pants-fire": 1,
}

LABEL_NAMES = {0: "Real", 1: "Fake"}
RANDOM_STATE = 42

# ---------------------------------------------------------------- models
MODELS_DIR = BASE_DIR / "models"
METRICS_FILE = MODELS_DIR / "metrics.json"

TFIDF_PARAMS = dict(max_features=50000, ngram_range=(1, 2), sublinear_tf=True, min_df=2)

MAX_SEQ_LEN = 40          # tokens per text for CNN / LSTM (headlines & statements are short)
VOCAB_MIN_FREQ = 2
EMBED_DIM = 128
DL_EPOCHS = 6
DL_BATCH_SIZE = 64
DL_LR = 1e-3

ROBERTA_MODEL_NAME = os.getenv("ROBERTA_MODEL_NAME", "roberta-base")
ROBERTA_MAX_LEN = 64
ROBERTA_EPOCHS = int(os.getenv("ROBERTA_EPOCHS", "1"))
ROBERTA_BATCH_SIZE = 16
ROBERTA_LR = 2e-5
# Optional cap on RoBERTa training rows (CPU training is slow); 0 = use the full training split.
ROBERTA_MAX_TRAIN = int(os.getenv("ROBERTA_MAX_TRAIN", "0"))

# ---------------------------------------------------------------- blockchain
BLOCKCHAIN_DIR = BASE_DIR / "blockchain"
CONTRACT_SOURCE = BLOCKCHAIN_DIR / "contracts" / "NewsRegistry.sol"
DEPLOYMENT_FILE = BLOCKCHAIN_DIR / "deployment.json"
SOLC_VERSION = "0.8.19"
ETH_RPC_URL = os.getenv("ETH_RPC_URL", "http://127.0.0.1:8545")
# Private key of the account that signs transactions. When empty, the first unlocked
# account of the node (e.g. Ganache) is used.
ETH_PRIVATE_KEY = os.getenv("ETH_PRIVATE_KEY", "")

# Publishers registered as verified sources when the contract is first deployed.
# More can be added with `python -m blockchain.manage add-source <domain>`.
DEFAULT_TRUSTED_SOURCES = [
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com",
    "washingtonpost.com", "theguardian.com", "npr.org", "aljazeera.com",
    "cnn.com", "dawn.com", "politifact.com",
]

# ---------------------------------------------------------------- web
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
MAX_TEXT_CHARS = 10000
