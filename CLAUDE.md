# Project context: AI Fake News Detection & Source Traceability Using Blockchain

Notes for continuing work on this project in a new chat (last updated 2026-10-18).

## The project
- Final Year Project, BS Software Engineering, NUML Multan. Students: Fatima Aamir (MLT-0000125),
  Hijab Fatima (MLT-0000115). Supervisor: Ms. Sanam Nayab.
- **The proposal is the single source of truth:** `FYP Proposal 3 new updated.pdf` in this repo.
  Use only the technologies it names: Python, scikit-learn, PyTorch, NLTK, Pandas, Ethereum,
  Flask, HTML/CSS/JavaScript; datasets FakeNewsNet + LIAR. No extra frameworks (no React,
  Tailwind, etc.). Do not change requirements without asking.
- Status: **delivered** on 2026-10-10. Work since then is optional polish.

## Architecture
- `ml/data.py` downloads + splits FakeNewsNet (titles; source = URL domain) and LIAR (statements;
  6 labels -> binary: true/mostly-true/half-true = Real). Splits: 27,627 train / 3,451 valid / 3,451 test.
- `ml/preprocessing.py` NLTK: clean, tokenize, stop-words (keeps negations), lemmatize.
- `ml/classical.py` TF-IDF + LR (C=1) / RF / SVM (C=0.1, calibrated). `ml/deep.py` CNN + BiLSTM.
  `ml/transformer.py` RoBERTa (`roberta-base`), lower 8 of 12 layers frozen, class-weighted loss.
- `ml/train.py` trains/evaluates; per-model decision threshold tuned on validation (macro-F1);
  writes `models/metrics.json`; default model = best validation F1. `ml/predictor.py` rescales
  probability so the tuned threshold maps to 50%.
- `blockchain/contracts/NewsRegistry.sol` (Solidity 0.8.19): records keyed by keccak256 of normalised
  text, immutable once written, owner-managed verified-source registry. `blockchain/ledger.py`
  (web3.py): deploy/connect, verify -> Verified / Unverified / Source Mismatch / No Source,
  integrity check against the `NewsRegistered` event. Compiled artifact in `blockchain/build/` (no solc
  download needed). `blockchain/manage.py` admin CLI. Local node: Ganache via `npm run chain`.
- `app.py` Flask REST API (`/api/analyze`, `/api/verify`, `/api/records`, `/api/sources`,
  `/api/models`, `/api/status`). Frontend `templates/index.html`, `static/css/style.css`,
  `static/js/app.js`: vanilla HTML/CSS/JS, "Obsidian & Champagne" dark luxury gold theme
  (Instrument Serif + Inter from Google Fonts), cinematic intro, animations. The user approved this
  theme after rejecting neon/synthwave ones.
- `tests/`: 14 tests (they start their own Ganache on port 8599). Run: `.venv\Scripts\python -m pytest -q`.

Not in git (too large or local): trained weights in `models/` (RoBERTa ~480 MB), `data/`,
`blockchain/node_modules`, `blockchain/chain-data`, `blockchain/deployment.json`, `.venv`, `wheels/`.
They are in the portable zip `fake-news-detection-portable.zip` kept outside the repo
(on the original PC: `D:\fake news detection\`).

## Results (test set)
RoBERTa (default) 77.8% acc, F1(Fake) 0.664, FakeNewsNet 87.0%, LIAR 62.2%. LR 74.8%, SVM 73.0%,
RF 72.4%, BiLSTM 71.1%, CNN 71.0%. Below the proposal's 90–95% target; reason documented in README
(headline-level data, LIAR is hard; dual AI + blockchain trust model is the project's answer).

## How to run (Windows)
- New machine: install Python 3.12 + Node.js LTS, double-click `setup.bat` once, then `start.bat`.
  `RUN_GUIDE.html` is the user-facing guide.
- Manually: `cd blockchain && npm run chain`, and `.venv\Scripts\python app.py`, then http://127.0.0.1:5000

## Moving to a new PC
The portable zip has no `.git` folder. After extracting it as the repo folder, reconnect it to GitHub
without re-downloading anything: `git init`, `git remote add origin https://github.com/rohailasad23/fake-news-detection.git`,
`git fetch origin`, `git reset origin/main` (mixed reset keeps the files), `git restore .` (brings back
tracked files the zip lacks, such as this file), `git branch -u origin/main`. `git status` should then be
clean apart from ignored files. Then run `setup.bat` once and `start.bat`. The user signs in to GitHub
themselves when Git Credential Manager asks on the first push.

## Machine and environment constraints
- The original PC: 3.9 GB RAM, 4 CPU cores, no GPU, slow internet (~100 KB/s). RoBERTa CPU training
  ≈ 80 min/epoch with 8 frozen layers. Launch long training **detached** (PowerShell
  `Start-Process ... -RedirectStandardOutput`) so it survives session restarts; never run another heavy
  torch job or the animated UI preview in parallel.
- Windows venv python spawns a child process that survives `preview_stop`; kill it by start time
  before restarting a server on the same port.
- Flask caches templates (debug off): restart the server after editing `index.html`.

## Working preferences (from the user)
- Communicate in simple language (the user often writes in Roman Urdu; mirror their language).
- Commit with the same author as the existing commits (`git log -1 --format="%an <%ae>"`) via
  `git -c user.name=... -c user.email=...`, ending the message with the Claude co-author line.
  Ask before every push; when approved, push **directly to `main`** after a fast-forward check.
- Never permanently delete files; use the Recycle Bin or ask the user to delete.
- Never handle private keys, seed phrases, API keys or tokens; the user pastes secrets themselves.

## Open items
1. **"Verified sources" hero stat sometimes shows "—"**: on one page load `/api/sources` returned
   503 while other calls succeeded; later calls returned 200 with 12 sources. Suspected cause:
   concurrent requests at page load hitting `Ledger.connect()` / web3 at the same time (connect is
   not locked). Not yet reproduced or fixed. Possible fixes: lock `Ledger.connect()`, log the
   exception in the API error path, retry the stat on the frontend.
2. **Deployment postponed.** Hugging Face Docker Spaces now need PRO (paid). Options discussed:
   Azure for Students (free credit, needs university email; recommended), HF PRO (~$9/month),
   Oracle Cloud Always Free, Google Cloud Run. Blockchain plan: Sepolia testnet + Alchemy RPC +
   MetaMask wallet (not created yet). Needed code changes for deployment: Dockerfile/gunicorn,
   contract address via env var, slow-transaction handling, rate limiting, faster record lookup than a
   full event-log scan, AI disclaimer, SEO.
