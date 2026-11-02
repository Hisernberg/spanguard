"""Char-level multi-task guard: shared dilated-conv encoder, two heads —
per-char injection probability (span surface) and doc-level attack probability
(binary surface). ~1.3M parameters, pure torch, sub-ms per short doc on CPU.
Trained by training/train_char.py; served through spanguard.detect.char_guard."""
import json

import torch
from torch import nn

CONFIG = {"channels": 384, "blocks": 5, "kernel": 5, "dilations": [1, 2, 4, 8, 16],
          "emb": 64, "max_chars": 4096, "window": 1024, "stride": 896}


class Block(nn.Module):
    def __init__(self, ch: int, k: int, d: int):
        super().__init__()
        self.dw = nn.Conv1d(ch, ch, k, dilation=d, padding=d * (k - 1) // 2, groups=ch)
        self.pw = nn.Conv1d(ch, ch, 1)
        self.norm = nn.GroupNorm(8, ch)

    def forward(self, x):
        x = x + self.pw(torch.relu(self.norm(self.dw(x))))
        return x


class CharGuardNet(nn.Module):
    def __init__(self, vocab_size: int, cfg: dict = CONFIG):
        super().__init__()
        self.cfg = cfg
        self.emb = nn.Embedding(vocab_size, cfg["emb"], padding_idx=0)
        self.proj = nn.Conv1d(cfg["emb"], cfg["channels"], 1)
        self.blocks = nn.ModuleList(
            [Block(cfg["channels"], cfg["kernel"], d) for d in cfg["dilations"][: cfg["blocks"]]])
        self.span_head = nn.Conv1d(cfg["channels"], 1, 1)
        self.doc_head = nn.Linear(cfg["channels"], 2)

    def features(self, idx: torch.Tensor) -> torch.Tensor:
        x = self.emb(idx).transpose(1, 2)
        x = self.proj(x)
        for b in self.blocks:
            x = b(x)
        return x

    def forward(self, idx: torch.Tensor):
        f = self.features(idx)
        span_logits = self.span_head(f).squeeze(1)          # [B, T]
        doc_logits = self.doc_head(f.mean(dim=2))           # [B, 2]
        return span_logits, doc_logits


def build_vocab(texts: list[str], cap: int = 500) -> dict[str, int]:
    from collections import Counter
    c = Counter(ch for t in texts for ch in t)
    vocab = {"<pad>": 0, "<unk>": 1}
    for ch, _ in c.most_common(cap - 2):
        if not ch.isspace() or ch == " ":
            vocab.setdefault(ch, len(vocab))
    return vocab


def encode(text: str, vocab: dict[str, int], window: int, stride: int) -> torch.Tensor:
    ids = [vocab.get(ch, 1) for ch in text[:CONFIG["max_chars"]]]
    if len(ids) <= window:
        ids = ids + [0] * (window - len(ids))
        return torch.tensor([ids])
    chunks = []
    for i in range(0, len(ids), stride):
        seg = ids[i: i + window]
        if len(seg) < window:
            seg = seg + [0] * (window - len(seg))
        chunks.append(seg)
        if i + window >= len(ids):
            break
    return torch.tensor(chunks)


def load_model(dir_path: str):
    import pathlib
    p = pathlib.Path(dir_path)
    vocab = json.loads((p / "vocab.json").read_text())
    cfg = json.loads((p / "config.json").read_text())["net"]
    net = CharGuardNet(len(vocab), cfg)
    net.load_state_dict(torch.load(p / "char_guard.pt", map_location="cpu", weights_only=True))
    net.eval()
    torch.set_num_threads(2)
    calib = json.loads((p / "calibration.json").read_text())
    return net, vocab, calib
