# AI-Powered Fake News Detection and Source Traceability Using Blockchain

Final Year Project (BS Software Engineering), National University of Modern Languages, Multan.
Fatima Aamir (MLT-0000125) · Hijab Fatima (MLT-0000115) · Supervisor: Ms. Sanam Nayab

The system classifies a news article or headline as **Real** or **Fake** using AI/NLP, and records the
news source on an **Ethereum** blockchain ledger. Each news record gets a unique hash, so its origin can
be traced and cannot be altered.

## Architecture (proposal Figure 1)

| Workflow step (proposal §5) | Implementation |
|---|---|
| 1. Data collection | `ml/data.py` downloads **FakeNewsNet** (PolitiFact + GossipCop) and **LIAR**, then labels them Real/Fake |
| 2. Data preprocessing | `ml/preprocessing.py` (**NLTK**): removes URLs, HTML, punctuation, digits and special characters; tokenization; stop-word removal; lowercasing and WordNet lemmatization |
| 3. Feature extraction | **TF-IDF** (scikit-learn) for the classical models; learned **word embeddings** for CNN/LSTM; RoBERTa sub-word embeddings |
| 4. Model training | **RoBERTa**, **CNN** and **LSTM** (PyTorch), plus Logistic Regression, Random Forest and SVM baselines (scikit-learn). Results in `ml/train.py` and `models/metrics.json` |
| 5. Fake news detection | `ml/predictor.py` returns Real/Fake with a confidence score. The model with the best validation F1 is used by default |
| 6. Blockchain source traceability | `blockchain/contracts/NewsRegistry.sol` (Solidity smart contract on Ethereum), driven by `blockchain/ledger.py` (web3.py). Records the keccak256 content hash, source, AI verdict, timestamp and submitter. Existing records cannot be overwritten. The contract also keeps a registry of verified sources |
| 7. User interface | Flask backend (`app.py`) with an HTML/CSS/JavaScript frontend (`templates/`, `static/`). The frontend is plain HTML/CSS/vanilla JS with no frameworks: a cinematic intro, animated analysis, a confidence gauge, and the ledger shown as a chain of blocks. Fonts load from Google Fonts, with system fonts as an offline fallback |

### Source verification status
| Status | Meaning |
|---|---|
| **Verified** | The source (or the recorded origin) is in the on-chain registry of verified publishers |
| **Unverified** | A source was given, but it is not a verified publisher |
| **Source Mismatch** | The same content is already on the ledger under a *different* original source |
| **No Source** | No source was supplied |

Every on-chain record is also checked for integrity: the stored record is compared against the
immutable `NewsRegistered` event emitted in its registration transaction.

## Results (held-out test set, 3,451 samples)

| Model | Accuracy | Precision (Fake) | Recall (Fake) | F1 (Fake) | FakeNewsNet acc. | LIAR acc. |
|---|---|---|---|---|---|---|
| Logistic Regression (TF-IDF) | 73.7% | 57.0% | 67.1% | 61.7% | 83.1% | 57.9% |
| Random Forest (TF-IDF) — default | 69.7% | 51.3% | 74.9% | 60.9% | 79.8% | 52.5% |
| SVM (TF-IDF) | 75.4% | 66.9% | 43.2% | 52.5% | 84.3% | 60.2% |
| CNN | 65.7% | 47.4% | 81.3% | 59.9% | 74.1% | 51.4% |
| BiLSTM | 71.3% | 53.5% | 67.9% | 59.8% | 81.7% | 53.6% |
| RoBERTa* | 73.3% | 60.3% | 44.3% | 51.1% | 83.2% | 56.5% |

The default model is the one with the best validation F1-score.
\*RoBERTa was fine-tuned for one epoch on a random 6,000-row subset, because the development machine has only
3.9 GB of RAM and no GPU. On a GPU machine, train it on the full split (`ROBERTA_MAX_TRAIN=0`, `ROBERTA_EPOCHS=3`).

Results fall short of the proposal's expected 90–95%. That range comes from studies on article-level datasets,
whereas this project uses headline/statement-level data. LIAR in particular is a known hard benchmark: binary
results reported on its short political statements are typically in the 60–70% range. On FakeNewsNet the models reach about 80–84%.

## Technologies
Python · scikit-learn · PyTorch · Hugging Face Transformers (RoBERTa) · NLTK · Pandas ·
Ethereum (Solidity 0.8.19, Ganache local node, web3.py, py-solc-x) · Flask · HTML/CSS/JavaScript

## Setup and run

Prerequisites: Python 3.10+ and Node.js 18+ (Node is needed only for the local Ethereum node, Ganache).

```bash
# 1. Python environment
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 2. Data: download FakeNewsNet + LIAR, preprocess, create train/valid/test splits
python -m ml.data

# 3. Train and evaluate all models
python -m ml.train
#   or a subset:  python -m ml.train --models logistic_regression svm cnn lstm
#   RoBERTa on a CPU-only / low-RAM machine: fine-tune on a random subset of the training rows
#   (Windows PowerShell: $env:ROBERTA_MAX_TRAIN="6000"; python -m ml.train --models roberta)

# 4. Start the local Ethereum node (separate terminal, keep it running)
cd blockchain
npm install
npm run chain

# 5. Start the web app (the contract is compiled and deployed automatically on first use)
python app.py
# open http://127.0.0.1:5000
```

The blockchain data persists in `blockchain/chain-data/`. To use another Ethereum network (for example
the Sepolia testnet), set `ETH_RPC_URL` and `ETH_PRIVATE_KEY` before starting the app.

### Managing verified sources (contract owner)
```bash
python -m blockchain.manage sources
python -m blockchain.manage add-source dawn.com
python -m blockchain.manage remove-source dawn.com
python -m blockchain.manage status
```

### Tests
```bash
python -m pytest -v
```
The blockchain tests start their own temporary Ganache chain.

## REST API
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/analyze` | `{text, source?, source_url?, model?, record?}`: AI classification + source verification, and records the item on the ledger |
| POST | `/api/verify` | `{text, source?}`: trace content on the ledger without writing to it |
| GET | `/api/records?limit=` | most recent ledger records |
| GET | `/api/records/<hash>` | look up a record by its content hash |
| GET | `/api/sources` | verified source registry |
| GET | `/api/models` | trained models and their evaluation metrics |
| GET | `/api/status` | model and blockchain status |

## Project structure
```
app.py                 Flask backend
config.py              settings (paths, hyper-parameters, RPC URL, default verified sources)
ml/                    data, preprocessing, classical/deep/transformer models, training, predictor
blockchain/            Solidity contract, web3 ledger service, admin CLI, Ganache node
templates/, static/    HTML / CSS / JavaScript frontend
models/                trained models + metrics.json
tests/                 unit and integration tests
```
