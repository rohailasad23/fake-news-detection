"""PyTorch CNN and LSTM text classifiers using learned word embeddings."""
import json
from collections import Counter

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

import config

PAD, UNK = 0, 1


class Vocabulary:
    def __init__(self, itos):
        self.itos = itos
        self.stoi = {w: i for i, w in enumerate(itos)}

    @classmethod
    def build(cls, clean_texts, min_freq=config.VOCAB_MIN_FREQ):
        counts = Counter(tok for t in clean_texts for tok in t.split())
        words = sorted(w for w, c in counts.items() if c >= min_freq)
        return cls(["<pad>", "<unk>"] + words)

    def encode(self, clean_text, max_len=config.MAX_SEQ_LEN):
        ids = [self.stoi.get(tok, UNK) for tok in clean_text.split()][:max_len]
        return ids + [PAD] * (max_len - len(ids))

    def encode_many(self, clean_texts):
        return torch.tensor([self.encode(t) for t in clean_texts], dtype=torch.long)

    def save(self, path):
        path.write_text(json.dumps(self.itos), encoding="utf-8")

    @classmethod
    def load(cls, path):
        return cls(json.loads(path.read_text(encoding="utf-8")))


class TextCNN(nn.Module):
    """Kim-style CNN: parallel 1-D convolutions over word embeddings + max-pooling."""

    def __init__(self, vocab_size, embed_dim=config.EMBED_DIM, n_filters=100,
                 kernel_sizes=(2, 3, 4, 5), dropout=0.5):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=PAD)
        self.convs = nn.ModuleList(nn.Conv1d(embed_dim, n_filters, k) for k in kernel_sizes)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(n_filters * len(kernel_sizes), 1)

    def forward(self, x):
        emb = self.embedding(x).transpose(1, 2)                  # (B, E, T)
        pooled = [torch.relu(conv(emb)).max(dim=2).values for conv in self.convs]
        return self.fc(self.dropout(torch.cat(pooled, dim=1))).squeeze(1)


class TextLSTM(nn.Module):
    """Bidirectional LSTM over word embeddings; final hidden states feed the classifier."""

    def __init__(self, vocab_size, embed_dim=config.EMBED_DIM, hidden=128, dropout=0.5):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=PAD)
        self.lstm = nn.LSTM(embed_dim, hidden, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden * 2, 1)

    def forward(self, x):
        lengths = (x != PAD).sum(dim=1).clamp(min=1).cpu()
        packed = nn.utils.rnn.pack_padded_sequence(self.embedding(x), lengths,
                                                   batch_first=True, enforce_sorted=False)
        _, (h, _) = self.lstm(packed)
        return self.fc(self.dropout(torch.cat([h[-2], h[-1]], dim=1))).squeeze(1)


ARCHITECTURES = {"cnn": TextCNN, "lstm": TextLSTM}


@torch.no_grad()
def _predict(model, X, batch_size=512):
    model.eval()
    return np.concatenate([torch.sigmoid(model(X[i:i + batch_size])).numpy()
                           for i in range(0, len(X), batch_size)])


def train_deep(name, vocab, train_texts, train_labels, valid_texts, valid_labels, eval_fn):
    """Train a CNN/LSTM, keeping the epoch with the best validation F1."""
    torch.manual_seed(config.RANDOM_STATE)
    model = ARCHITECTURES[name](len(vocab.itos))
    X_train, X_valid = vocab.encode_many(train_texts), vocab.encode_many(valid_texts)
    y_train = torch.tensor(np.asarray(train_labels), dtype=torch.float32)
    loader = DataLoader(TensorDataset(X_train, y_train), batch_size=config.DL_BATCH_SIZE, shuffle=True)

    pos_weight = (y_train == 0).sum() / (y_train == 1).sum().clamp(min=1)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optim = torch.optim.Adam(model.parameters(), lr=config.DL_LR)

    best_f1, best_state = -1.0, None
    for epoch in range(1, config.DL_EPOCHS + 1):
        model.train()
        total = 0.0
        for xb, yb in loader:
            optim.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            optim.step()
            total += loss.item() * len(xb)
        f1 = eval_fn(valid_labels, _predict(model, X_valid))["f1"]
        print(f"  [{name}] epoch {epoch}: loss={total / len(y_train):.4f} valid_f1={f1:.4f}")
        if f1 > best_f1:
            best_f1 = f1
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    return model


def save(name, model, vocab):
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), config.MODELS_DIR / f"{name}.pt")
    vocab.save(config.MODELS_DIR / "vocab.json")


class DeepModel:
    """Inference wrapper: expects preprocessed (clean) text."""

    def __init__(self, name):
        self.name = name
        self.vocab = Vocabulary.load(config.MODELS_DIR / "vocab.json")
        self.model = ARCHITECTURES[name](len(self.vocab.itos))
        self.model.load_state_dict(torch.load(config.MODELS_DIR / f"{name}.pt", map_location="cpu"))
        self.model.eval()

    def predict_proba(self, clean_texts):
        return _predict(self.model, self.vocab.encode_many(list(clean_texts)))
