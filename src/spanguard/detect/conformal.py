"""v6 detection layers: split-conformal span threshold (F) + task-conditioned
gate (B) on top of an SPG-FM model.

Why: fm's only measured loss to the router stack is benign over-strip — the doc
head fires on unseen benign prose. v6 replaces the fixed 0.5 operating point
with two principled layers:

(F) Conformal span threshold. On a calibration set of benign docs we record,
per stratum (structured / prose), the distribution of the strongest candidate
span score. tau is the finite-sample-corrected (1-alpha) quantile, so for a new
exchangeable benign doc P(any span stripped) <= alpha — a bound, not a hope.
Two taus: `tau` (the alpha the operator asked for) and `band_lo` (the alpha=0.25
quantile). Spans above tau are stripped; spans inside [band_lo, tau) are the
uncertain band handed to the task gate; below band_lo nothing happens.

(B) Task-conditioned gate. A small char CNN over "task <SEP> span-context"
decides keep/strip for band spans when the caller passes the user's task
(Guard(task=...)). Trained so label 1 = task-relevant benign instruction
(survives), label 0 = off-task instruction or injection payload (stripped).
Band spans therefore strip when off-task or malicious even though their raw
score missed tau — the escape rate stays low while benign over-strip stays
inside the alpha bound. Without a task the band is simply released (pure
conformal behaviour).

Everything here is post-hoc: the fm weights are unchanged, so the v5 measured
records stay comparable.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import torch

from .char_model import CharGuardNet, encode

CAND_THR = 0.15        # candidate floor: anything weaker is never worth gating
DEFAULT_ALPHA = 0.10   # operator-facing over-strip bound (per benign doc)
BAND_ALPHA = 0.25      # band lower edge quantile


def _resolve_dir(dir_path: str | None) -> Path:
    key = dir_path or os.environ.get("SPANGUARD_FM_MODEL") or "data/models/spanguard-fm-1"
    p = Path(key)
    return p if p.is_absolute() or p.exists() else Path(__file__).parents[3] / key


_CACHE: dict[str, tuple] = {}


def _load_fm_uncached(dir_path: str | None = None):
    p = _resolve_dir(dir_path)
    vocab = json.loads((p / "vocab.json").read_text())
    cfg = json.loads((p / "config.json").read_text())["net"]
    net = CharGuardNet(len(vocab), cfg)
    net.load_state_dict(torch.load(p / "char_guard.pt", map_location="cpu", weights_only=True))
    net.eval()
    torch.set_num_threads(2)
    return net, vocab, p


def load_fm(dir_path: str | None = None):
    """Cached loader — the calibration sweep runs thousands of guard() calls."""
    key = str(_resolve_dir(dir_path))
    if key in _CACHE:
        return _CACHE[key]
    _CACHE[key] = _load_fm_uncached(dir_path)
    return _CACHE[key]


def fm_span_scores(text: str, dir_path: str | None = None, cand_thr: float = CAND_THR):
    """Candidate spans with their max char-probability, plus the doc-head prob.

    Unlike char_guard.char_spans (hard-thresholded, no scores) this returns the
    raw material the conformal policy needs: [(start, end, score)], doc_p.
    Span merge mirrors char_guard: >=2 hot chars, expanded by one char.
    """
    net, vocab, _p = load_fm(dir_path)
    window, stride = net.cfg["window"], net.cfg["stride"]
    idxs = encode(text, vocab, window, stride)
    with torch.no_grad():
        span_logits, doc_logits = net(idxs)
    probs = span_logits.sigmoid()
    bits: list[float] = []
    for w in range(probs.shape[0]):
        bits.extend(probs[w].tolist())
    bits = bits[: len(text)]
    spans: list[tuple[int, int, float]] = []
    start = None
    peak = 0.0
    for i, b in enumerate(bits + [0.0]):
        hot = b >= cand_thr and i < len(text)
        if hot:
            if start is None:
                start, peak = i, b
            else:
                peak = max(peak, b)
        elif start is not None:
            if i - start >= 2:
                spans.append((max(0, start - 1), min(len(text), i + 1), peak))
            start, peak = None, 0.0
    doc_p = float(doc_logits.softmax(-1)[0, 1])
    return spans, doc_p


def _quantile(scores: list[float], alpha: float) -> float:
    """Split-conformal threshold with finite-sample correction: the
    ceil((n+1)(1-alpha))-th smallest score, so P(new benign > tau) <= alpha."""
    if not scores:
        return 1.0
    s = sorted(scores)
    n = len(s)
    k = min(n, max(1, math.ceil((n + 1) * (1 - alpha))))
    return s[k - 1]


def is_structured(text: str) -> bool:
    from .pipeline import is_structured as _is

    return _is(text)


def calibrate(benign_docs: list[str], dir_path: str | None = None,
              alpha: float = DEFAULT_ALPHA) -> dict:
    """Stratified split-conformal calibration on benign docs only."""
    per_stratum: dict[str, list[float]] = {"structured": [], "prose": []}
    for text in benign_docs:
        spans, _doc_p = fm_span_scores(text, dir_path)
        top = max((sc for _a, _b, sc in spans), default=0.0)
        per_stratum["structured" if is_structured(text) else "prose"].append(top)
    out = {"method": "split-conformal", "alpha": alpha, "band_alpha": BAND_ALPHA,
           "cand_thr": CAND_THR, "strata": {}}
    for name, scores in per_stratum.items():
        out["strata"][name] = {
            "tau": round(_quantile(scores, alpha), 4),
            "band_lo": round(_quantile(scores, BAND_ALPHA), 4),
            "n": len(scores),
        }
    return out


class ConformalPolicy:
    """Loads calibration_v2.json from a model dir; decides per-span strip."""

    def __init__(self, dir_path: str | None = None):
        p = _resolve_dir(dir_path)
        cal_path = p / "calibration_v2.json"
        self.cal = json.loads(cal_path.read_text()) if cal_path.exists() else None

    @property
    def available(self) -> bool:
        return self.cal is not None

    def stratum(self, text: str) -> str:
        return "structured" if is_structured(text) else "prose"

    def tau(self, text: str) -> float:
        if not self.cal:
            return 0.5
        return float(self.cal["strata"][self.stratum(text)]["tau"])

    def band_lo(self, text: str) -> float:
        if not self.cal:
            return 0.5
        return float(self.cal["strata"][self.stratum(text)]["band_lo"])

    def decide(self, text: str, score: float) -> str:
        """strip | band | keep — band spans go to the task gate (or are kept)."""
        if score >= self.tau(text):
            return "strip"
        if score >= self.band_lo(text):
            return "band"
        return "keep"


class TaskGate:
    """v6-B runtime: keep/strip for band spans, conditioned on the user's task."""

    def __init__(self, dir_path: str | None = None):
        key = dir_path or os.environ.get("SPANGUARD_TASKGATE") or ""
        p = Path(key) if key else None
        self.net = None
        if p and (Path(p) / "gate.pt").exists():
            vocab = json.loads((p / "vocab.json").read_text())
            cfg = json.loads((p / "config.json").read_text())
            self.net = _GateNet(len(vocab))
            self.net.load_state_dict(torch.load(p / "gate.pt", map_location="cpu",
                                                weights_only=True))
            self.net.eval()
            self.vocab = vocab
            self.window = cfg["window"]
            self.sep = cfg["sep"]

    @property
    def available(self) -> bool:
        return self.net is not None

    def _gate_text(self, task: str, context: str, start: int, end: int) -> str:
        lo, hi = max(0, start - 120), min(len(context), end + 120)
        return task[:200] + self.sep + context[lo:hi]

    def keep(self, task: str, context: str, start: int, end: int) -> bool:
        """True = task-relevant benign instruction (release it), False = strip."""
        if not self.available:
            return False
        ids = [self.vocab.get(ch, 1) for ch in self._gate_text(task, context, start, end)]
        ids = (ids + [0] * self.window)[: self.window]
        idx = torch.tensor([ids])
        with torch.no_grad():
            logits = self.net(idx)
        return int(logits.argmax(-1)[0]) == 1


class _GateNet(torch.nn.Module):
    """Mirror of the kernel's gate architecture (emb 64, ch 256, 4 blocks)."""

    def __init__(self, vocab_size: int):
        super().__init__()
        self.emb = torch.nn.Embedding(vocab_size, 64, padding_idx=0)
        self.proj = torch.nn.Conv1d(64, 256, 1)
        self.blocks = torch.nn.ModuleList(
            _GateBlock(256, 5, d) for d in [1, 2, 4, 8])
        self.head = torch.nn.Linear(256, 2)

    def forward(self, idx: torch.Tensor) -> torch.Tensor:
        x = self.emb(idx).transpose(1, 2)
        x = self.proj(x)
        for b in self.blocks:
            x = b(x)
        return self.head(x.mean(dim=2))


class _GateBlock(torch.nn.Module):
    def __init__(self, ch: int, k: int, d: int):
        super().__init__()
        self.dw = torch.nn.Conv1d(ch, ch, k, dilation=d, padding=d * (k - 1) // 2, groups=ch)
        self.pw = torch.nn.Conv1d(ch, ch, 1)
        self.norm = torch.nn.GroupNorm(8, ch)

    def forward(self, x):
        return x + self.pw(torch.relu(self.norm(self.dw(x))))


def fm_v6_decide(text: str, task: str | None = None, dir_path: str | None = None,
                 gate_dir: str | None = None, policy: ConformalPolicy | None = None,
                 gate: TaskGate | None = None) -> dict:
    """The v6 decision for one document.

    Returns spans to strip [(start, end, score, reason)], doc_p, and the band
    outcomes so tests and the harness can audit every decision.
    """
    policy = policy or ConformalPolicy(dir_path)
    spans, doc_p = fm_span_scores(text, dir_path)
    strip, audit = [], []
    for a, b, sc in spans:
        d = policy.decide(text, sc)
        if d == "band" and task:
            g = gate or TaskGate(gate_dir)
            if g.available:
                keep = g.keep(task, text, a, b)
                audit.append({"span": [a, b], "score": round(sc, 4),
                              "decision": "band-gate-keep" if keep else "band-gate-strip"})
                if not keep:
                    strip.append((a, b, sc, "band-gate-strip"))
                continue
            d = "keep"  # gate unavailable: pure conformal behaviour
        if d == "band":
            d = "keep"  # no task: release the band (conformal bound still holds)
        audit.append({"span": [a, b], "score": round(sc, 4), "decision": d})
        if d == "strip":
            strip.append((a, b, sc, d))
    return {"strip": strip, "doc_p": doc_p, "audit": audit}
