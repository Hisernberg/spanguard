"""Runtime wrapper for the char-level multi-task guard (spanguard-char).
Windows the text, thresholds per-char probs at the calibrated point, merges to
spans, and exposes guard(text) -> Result like the other detectors."""
from pathlib import Path

import torch

from ..types import Finding, Result
from .char_model import encode, load_model

DEFAULT_DIR = "data/models/spanguard-char"
_edge_ctx = {}


def _load(dir_path: str | None):
    import os
    key = dir_path or os.environ.get("SPANGUARD_CHAR_MODEL") or DEFAULT_DIR
    if key not in _edge_ctx:
        base = Path(key) if os.path.isabs(key) or key.startswith("data") else Path(__file__).parents[3] / key
        _edge_ctx[key] = load_model(str(base))
    return _edge_ctx[key]


def char_spans(text: str, dir_path: str | None = None, threshold: float | None = None):
    net, vocab, calib = _load(dir_path)
    thr = threshold if threshold is not None else calib.get("threshold", 0.5)
    window = net.cfg["window"]
    stride = net.cfg["stride"]
    idxs = encode(text, vocab, window, stride)
    with torch.no_grad():
        span_logits, doc_logits = net(idxs)
    probs = span_logits.sigmoid()
    bits: list[int] = []
    for w in range(probs.shape[0]):
        bits.extend((probs[w] >= thr).int().tolist())
    bits = bits[: len(text)]
    spans, start = [], None
    for i, b in enumerate(bits):
        if b and start is None:
            start = i
        elif not b and start is not None:
            if i - start >= 2:
                spans.append((max(0, start - 1), min(len(text), i + 1)))
            start = None
    if start is not None and len(bits) - start >= 2:
        spans.append((max(0, start - 1), len(text)))
    doc_p = float(doc_logits.softmax(-1)[0, 1])
    return spans, doc_p


def char_guard_system(mode: str = "char", model_dir: str | None = None):
    def fn(doc: dict):
        spans, _doc_p = char_spans(doc["text"], dir_path=model_dir)
        findings = [Finding(start=a, end=b, length=b - a, kind="char-span",
                            source="spanguard-char", confidence=1.0, sha256="")
                    for a, b in spans]
        cleaned = doc["text"]
        for f in sorted(findings, key=lambda x: x.start, reverse=True):
            cleaned = cleaned[: f.start] + "[stripped]" + cleaned[f.end:]
        return Result(original=doc["text"], cleaned=cleaned, stripped=findings)
    return fn
