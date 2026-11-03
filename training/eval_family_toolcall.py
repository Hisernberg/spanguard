"""Evaluate the trained model family on the held-out tool-call set.

Both classifiers (docguard, toolguard) score the same generated tool-call test
set, so the toolguard's specialization is measurable against the doc-level
model. Writes eval/results/<date>-family/run.json (run-record schema).
"""

from __future__ import annotations

import datetime as dt
import json
import statistics
import time
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parents[1]
MODELS = REPO / "data" / "models"
TEST = MODELS / "spanguard-toolguard-mdistil" / "toolcall_test_set.json"
torch.set_num_threads(2)


def eval_calls(model_dir: Path, rows: list[dict], max_len: int) -> dict:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, dtype=torch.float32).eval()
    lat = []
    tp = fp = fn = tn = 0
    per_tool: dict = {}
    for d in rows:
        t0 = time.monotonic()
        enc = tok(d["text"], truncation=True, max_length=max_len, return_tensors="pt")
        with torch.no_grad():
            p = float(model(**enc).logits.softmax(-1)[0, 1])
        lat.append((time.monotonic() - t0) * 1000)
        pred = p >= 0.5
        gold = d["label"] == "attack"
        agg = per_tool.setdefault(d["tool"], {"n": 0, "attack": 0, "caught": 0, "false": 0})
        agg["n"] += 1
        if gold:
            agg["attack"] += 1
            agg["caught"] += pred
        elif pred:
            agg["false"] += 1
        tp += pred and gold
        fp += pred and not gold
        fn += (not pred) and gold
        tn += (not pred) and (not gold)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    lats = sorted(lat)
    return {
        "docs": len(rows), "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4),
        "false_block_rate": round(fp / max(1, fp + tn), 4),
        "latency_ms_p50": round(statistics.median(lat), 1),
        "latency_ms_p95": round(lats[int(0.95 * len(lats))], 1),
        "per_tool": {k: {"attacks": v["attack"],
                         "block_recall": round(v["caught"] / v["attack"], 4) if v["attack"] else None,
                         "false_blocks": v["false"]} for k, v in sorted(per_tool.items())},
    }


def main() -> None:
    rows = json.loads(TEST.read_text())
    print(f"held-out tool calls: {len(rows)} ({sum(r['label'] == 'attack' for r in rows)} attacks)")
    systems = {}
    for name, max_len in (("spanguard-toolguard", 256), ("spanguard-docguard", 288)):
        d = MODELS / f"{name}-mdistil"
        if not (d / "config.json").exists():
            print(f"skip {name}: not trained yet")
            continue
        m = eval_calls(d, rows, max_len)
        print(f"[{name}] rec {m['recall']:.3f} false-block {m['false_block_rate']:.3f} "
              f"F1 {m['f1']:.3f} p50 {m['latency_ms_p50']}ms")
        systems[name] = {
            "sets": {"tool-call-args": m},
            "model": f"Nabidnur/{name}-mdistil",
        }
    if not systems:
        print("no family models trained yet — nothing to record")
        return
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    run_dir = REPO / "eval" / "results" / f"{stamp}-family"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps({
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "environment": {"platform": "local CPU (recovery build)", "device": "cpu",
                        "threads": torch.get_num_threads()},
        "systems": systems,
        "dataset": "training/train/toolcall_gen.py seeds 909/910/911 (train/dev/test); held-out test=911",
    }, indent=2), encoding="utf-8")
    print("wrote", run_dir / "run.json")


if __name__ == "__main__":
    main()
