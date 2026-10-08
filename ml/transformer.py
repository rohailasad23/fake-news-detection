"""RoBERTa fine-tuning for fake news classification (Hugging Face Transformers + PyTorch)."""
import time

import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          get_linear_schedule_with_warmup)

import config

ROBERTA_DIR = config.MODELS_DIR / "roberta"


def _batches(tokenizer, texts, labels=None, batch_size=config.ROBERTA_BATCH_SIZE, shuffle=False):
    idx = list(range(len(texts)))

    def collate(batch_idx):
        enc = tokenizer([texts[i] for i in batch_idx], truncation=True, padding=True,
                        max_length=config.ROBERTA_MAX_LEN, return_tensors="pt")
        if labels is not None:
            enc["labels"] = torch.tensor([int(labels[i]) for i in batch_idx])
        return enc

    return DataLoader(idx, batch_size=batch_size, shuffle=shuffle, collate_fn=collate)


@torch.no_grad()
def _predict(model, tokenizer, texts):
    model.eval()
    probs = []
    for enc in _batches(tokenizer, texts, batch_size=64):
        probs.append(torch.softmax(model(**enc).logits, dim=-1)[:, 1].numpy())
    return np.concatenate(probs) if probs else np.array([])


def _freeze_lower_layers(model, n_layers):
    """Freeze the embeddings and the lowest `n_layers` encoder layers; return trainable params.

    Fine-tuning only the upper layers keeps memory and CPU time low enough to train on the
    full dataset on a machine without a GPU.
    """
    if n_layers > 0:
        for p in model.roberta.embeddings.parameters():
            p.requires_grad = False
        for layer in model.roberta.encoder.layer[:n_layers]:
            for p in layer.parameters():
                p.requires_grad = False
    return [p for p in model.parameters() if p.requires_grad]


def train_roberta(train_texts, train_labels, valid_texts, valid_labels, eval_fn):
    """Fine-tune RoBERTa on lightly cleaned text; saves the epoch with the best validation F1."""
    torch.manual_seed(config.RANDOM_STATE)
    torch.set_num_threads(max(torch.get_num_threads(), 1))
    train_texts, train_labels = list(train_texts), list(train_labels)
    if config.ROBERTA_MAX_TRAIN and len(train_texts) > config.ROBERTA_MAX_TRAIN:
        rng = np.random.default_rng(config.RANDOM_STATE)
        keep = rng.choice(len(train_texts), config.ROBERTA_MAX_TRAIN, replace=False)
        train_texts = [train_texts[i] for i in keep]
        train_labels = [train_labels[i] for i in keep]

    tokenizer = AutoTokenizer.from_pretrained(config.ROBERTA_MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(config.ROBERTA_MODEL_NAME, num_labels=2)
    trainable = _freeze_lower_layers(model, config.ROBERTA_FREEZE_LAYERS)
    loader = _batches(tokenizer, train_texts, train_labels, shuffle=True)
    optim = torch.optim.AdamW(trainable, lr=config.ROBERTA_LR, weight_decay=0.01)
    total_steps = len(loader) * config.ROBERTA_EPOCHS
    sched = get_linear_schedule_with_warmup(optim, int(0.06 * total_steps), total_steps)
    # Class weights counter the Real/Fake imbalance (~69% / 31%).
    counts = np.bincount(np.asarray(train_labels, dtype=int), minlength=2)
    loss_fn = torch.nn.CrossEntropyLoss(weight=torch.tensor(len(train_labels) / (2 * counts), dtype=torch.float32))

    best_f1 = -1.0
    for epoch in range(1, config.ROBERTA_EPOCHS + 1):
        model.train()
        start = time.time()
        for step, enc in enumerate(loader, 1):
            labels = enc.pop("labels")
            loss = loss_fn(model(**enc).logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            optim.step()
            sched.step()
            optim.zero_grad()
            if step % 50 == 0:
                rate = (time.time() - start) / step
                print(f"  [roberta] epoch {epoch} step {step}/{len(loader)} loss={loss.item():.4f} "
                      f"eta={rate * (len(loader) - step) / 60:.1f} min", flush=True)
        f1 = eval_fn(valid_labels, _predict(model, tokenizer, list(valid_texts)))["f1"]
        print(f"  [roberta] epoch {epoch}: valid_f1={f1:.4f}")
        if f1 > best_f1:
            best_f1 = f1
            ROBERTA_DIR.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(ROBERTA_DIR)
            tokenizer.save_pretrained(ROBERTA_DIR)
    return RobertaModel()


class RobertaModel:
    """Inference wrapper: expects lightly cleaned (not stop-word stripped) text."""
    name = "roberta"

    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(ROBERTA_DIR)
        self.model = AutoModelForSequenceClassification.from_pretrained(ROBERTA_DIR)
        self.model.eval()

    def predict_proba(self, texts):
        return _predict(self.model, self.tokenizer, list(texts))


def is_trained():
    return (ROBERTA_DIR / "config.json").exists()
