"""Data collection and preparation for the FakeNewsNet and LIAR datasets.

Run `python -m ml.data` to download the raw files and build the train/validation/test splits.
"""
import io
import zipfile
from urllib.parse import urlparse

import pandas as pd
import requests
from sklearn.model_selection import train_test_split

import config
from ml.preprocessing import ensure_nltk_resources, preprocess

LIAR_COLUMNS = [
    "id", "label", "statement", "subject", "speaker", "speaker_job", "state", "party",
    "barely_true_count", "false_count", "half_true_count", "mostly_true_count",
    "pants_fire_count", "context",
]
SPLITS = ("train", "valid", "test")


# ---------------------------------------------------------------- collection
def download_datasets(force=False):
    """Download FakeNewsNet CSVs and the LIAR archive into data/raw."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name in config.FAKENEWSNET_FILES:
        target = config.RAW_DIR / name
        if force or not target.exists():
            print(f"Downloading FakeNewsNet {name} ...")
            resp = requests.get(config.FAKENEWSNET_URL.format(name=name), timeout=120)
            resp.raise_for_status()
            target.write_bytes(resp.content)

    liar_dir = config.RAW_DIR / "liar"
    if force or not (liar_dir / "train.tsv").exists():
        print("Downloading LIAR dataset ...")
        resp = requests.get(config.LIAR_URL, timeout=300)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            zf.extractall(liar_dir)


def _domain(url):
    if not isinstance(url, str) or not url.strip():
        return ""
    netloc = urlparse(url if "://" in url else "http://" + url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def load_fakenewsnet():
    frames = []
    for name, label in config.FAKENEWSNET_FILES.items():
        df = pd.read_csv(config.RAW_DIR / name, usecols=["id", "news_url", "title"])
        frames.append(pd.DataFrame({
            "text": df["title"],
            "label": label,
            "source": df["news_url"].map(_domain),
            "dataset": "FakeNewsNet-" + name.split("_")[0],
        }))
    return pd.concat(frames, ignore_index=True)


def load_liar():
    """Return {split: DataFrame} keeping LIAR's official train/valid/test split."""
    out = {}
    for split in SPLITS:
        df = pd.read_csv(config.RAW_DIR / "liar" / f"{split}.tsv", sep="\t", header=None,
                         names=LIAR_COLUMNS, quoting=3)
        df = df[df["label"].isin(config.LIAR_LABEL_MAP)]
        out[split] = pd.DataFrame({
            "text": df["statement"],
            "label": df["label"].map(config.LIAR_LABEL_MAP),
            "source": df["speaker"].fillna("").astype(str),
            "dataset": "LIAR",
        })
    return out


# ---------------------------------------------------------------- preparation
def _clean_frame(df):
    df = df.dropna(subset=["text"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0]
    return df.drop_duplicates(subset=["text"])


def build_splits():
    """Combine both datasets, remove noise/duplicates, preprocess and save splits."""
    ensure_nltk_resources()
    fnn = _clean_frame(load_fakenewsnet())
    # FakeNewsNet has no official split: stratified 80 / 10 / 10.
    fnn_train, fnn_rest = train_test_split(fnn, test_size=0.2, stratify=fnn["label"],
                                           random_state=config.RANDOM_STATE)
    fnn_valid, fnn_test = train_test_split(fnn_rest, test_size=0.5, stratify=fnn_rest["label"],
                                           random_state=config.RANDOM_STATE)
    liar = load_liar()
    parts = {
        "train": pd.concat([fnn_train, liar["train"]]),
        "valid": pd.concat([fnn_valid, liar["valid"]]),
        "test": pd.concat([fnn_test, liar["test"]]),
    }

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    seen = set()
    for split in SPLITS:   # drop texts already used by an earlier split (prevents leakage)
        df = _clean_frame(parts[split])
        df = df[~df["text"].isin(seen)]
        seen.update(df["text"])
        df["clean_text"] = df["text"].map(preprocess)
        df = df[df["clean_text"].str.len() > 0].sample(frac=1, random_state=config.RANDOM_STATE)
        df.to_csv(config.PROCESSED_DIR / f"{split}.csv", index=False)
        counts = df["label"].value_counts().to_dict()
        print(f"{split:5s}: {len(df):6d} rows  real={counts.get(0, 0)}  fake={counts.get(1, 0)}")


def load_split(split):
    df = pd.read_csv(config.PROCESSED_DIR / f"{split}.csv", keep_default_na=False)
    df["label"] = df["label"].astype(int)
    return df


if __name__ == "__main__":
    download_datasets()
    build_splits()
