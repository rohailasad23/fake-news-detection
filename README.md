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
| **RoBERTa (default)** | **77.8%** | **63.5%** | 69.7% | **66.4%** | **87.0%** | **62.2%** |
| Logistic Regression (TF-IDF) | 74.8% | 59.4% | 62.5% | 60.9% | 84.4% | 58.4% |
| SVM (TF-IDF) | 73.0% | 55.6% | 71.1% | 62.4% | 83.3% | 55.5% |
| Random Forest (TF-IDF) | 72.4% | 55.5% | 62.4% | 58.8% | 82.2% | 55.8% |
| BiLSTM | 71.1% | 53.1% | 68.9% | 60.0% | 81.5% | 53.4% |
| CNN | 71.0% | 53.5% | 59.1% | 56.2% | 80.5% | 54.8% |

- The default model is the one with the best validation F1-score.
- Each model's decision threshold is tuned on the **validation** set to maximise macro-F1, because the data is
  imbalanced (about 31% fake). The test set is used only for the final numbers above. The confidence shown in the
  app is the model probability rescaled so that this threshold sits at 50%.
- RoBERTa (`roberta-base`) was fine-tuned for 2 epochs on the full training split with class-weighted loss. The
  embeddings and the lower 8 of 12 encoder layers were frozen so training fits a CPU-only machine with 3.9 GB of
  RAM (about 80 minutes per epoch). On a GPU, set `ROBERTA_FREEZE_LAYERS=0` for full fine-tuning.

Results fall short of the proposal's expected 90–95%. That range comes from studies on article-level datasets,
whereas this project uses headline/statement-level data. LIAR in particular is a known hard benchmark: binary
results reported on its short political statements are typically in the 60–70% range. On FakeNewsNet the best
model reaches 87%.

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
#   RoBERTa settings (environment variables): ROBERTA_EPOCHS (default 1), ROBERTA_FREEZE_LAYERS (default 8),
#   ROBERTA_MAX_TRAIN (0 = all rows). The reported model used, in Windows PowerShell:
#   $env:ROBERTA_EPOCHS="2"; python -m ml.train --models roberta

# 4. Start the local Ethereum node (separate terminal, keep it running)
cd blockchain
npm install
npm run chain

# 5. Start the web app (the contract is compiled and deployed automatically on first use)
python app.py
# open http://127.0.0.1:5000
```

**One-click start (Windows):** after the setup above, double-click `start.bat`. It starts Ganache and the web
app in two windows and opens the browser once the app is ready. Close the two windows to stop.

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
