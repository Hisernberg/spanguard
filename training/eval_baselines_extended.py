#!/usr/bin/env python3
"""Run the binary baselines (protectai deberta-v2, horizon small/base) on the
extended-attacks fixture, producing a record the eval harness can consume via
`baseline:<path>` (doc-level flags, strip-all semantics — same as the standard
baseline runs).

This is the buried-signal comparison: whole-sequence binary classifiers vs
spanguard's windowed span models on the 2026 carrier shapes.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REPO = Path(__file__).resolve().parents[1]
torch.set_num_threads(2)

CANDIDATES = [
    ("data/models/protectai", "protectai-deberta-v2"),
    ("data/models/horizon-small", "horizon-small"),
    ("data/models/horizon-base", "horizon-base"),
]
_ATTACK_RX = ("attack", "injection", "unsafe", "malicious", "jailbreak")


def attack_index(id2label) -> int:
    labels = [str(v).lower() for v in id2label.values()]
    for i, lab in enumerate(labels):
        if any(rx in lab for rx in _ATTACK_RX):
            return i
    return len(labels) - 1


def run_system(model_dir: str, tag: str, docs: list[dict]) -> dict:
    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, dtype=torch.float32).eval()
    idx = attack_index(model.config.id2label)
    flags, lat = {}, []
    for d in docs:
        t0 = time.monotonic()
        enc = tok(d["text"][:2000], truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            p = float(model(**enc).logits.softmax(-1)[0, idx])
        lat.append((time.monotonic() - t0) * 1000)
        flags[d["id"]] = bool(p >= 0.5)
    escaped = sum(1 for d in docs if d.get("attack") and not flags[d["id"]])
    planted = sum(len(d.get("spans") or []) for d in docs if d.get("attack"))
    fp = sum(1 for d in docs if not d.get("attack") and flags[d["id"]])
    print(f"[{tag}] escaped {escaped}/{sum(1 for d in docs if d.get('attack'))} "
          f"| false-flag {fp}/{sum(1 for d in docs if not d.get('attack'))} | p50 {sorted(lat)[len(lat)//2]:.0f}ms")
    return {"_flags": flags, "escape": escaped, "false_flags": fp,
            "latency_ms_p50": round(sorted(lat)[len(lat) // 2], 1)}


def main() -> None:
    fixtures = REPO / "eval" / "fixtures"
    docs = [json.loads(l) for l in open(fixtures / "extended-attacks.jsonl", encoding="utf-8")]
    out = {"tag": "baselines-extended",
           "generated_at": datetime.now().isoformat(timespec="seconds"),
           "set": "extended-attacks", "n_docs": len(docs), "systems": {}}
    for model_dir, tag in CANDIDATES:
        try:
            out["systems"][tag] = run_system(REPO / model_dir, tag, docs)
        except Exception as exc:  # noqa: BLE001
            print(f"[{tag}] FAILED: {exc}")
            out["systems"][tag] = {"available": False, "error": str(exc)[:200]}
    dest = REPO / "eval" / "results" / "baselines-extended" / "record.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    print("record:", dest)


if __name__ == "__main__":
    sys.exit(main())
