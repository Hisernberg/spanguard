#!/usr/bin/env python3
"""Extended-domain benchmark: char-v3 (corpus-v3, MCP/skill/buried/polite/bn)
vs char-v2 (corpus-v2) on the corpus-v3 TEST split — the five new families are
pure OOD for char-v2 and in-domain for char-v3.

Reports per-family escape + over-strip + span-F1 for both models. Deterministic;
writes eval/results/<tag>/run.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "training")

NEW_FAMILIES = ["mcp-poison", "skill-file", "buried-multihop", "md-image-exfil", "social-polite"]


def score(model_dir: str, docs: list[dict]) -> dict:
    from spanguard.detect.char_guard import char_spans

    per_family: dict[str, dict] = {}
    tot = {"planted": 0, "escaped": 0, "stripped_benign": 0, "benign": 0,
           "tp": 0, "fp": 0, "fn": 0, "n": 0}
    for d in docs:
        pred, _docp = char_spans(d["text"], dir_path=model_dir)
        planted = d.get("spans") or []
        fam = d["attack"] or "benign"
        st = per_family.setdefault(fam, {"planted": 0, "escaped": 0, "n": 0,
                                         "tp": 0, "fp": 0, "fn": 0, "over_chars": 0})
        st["n"] += 1
        tot["n"] += 1
        if not d["attack"] and not d.get("negative"):
            st["over_chars"] += _benign_stripped(d["text"], pred)
            tot["stripped_benign"] += _benign_stripped(d["text"], pred)
            tot["benign"] += 1
        tp, fp, fn = _match(planted, pred)
        st["planted"] += len(planted)
        st["tp"] += tp
        st["fp"] += fp
        st["fn"] += fn
        tot["planted"] += len(planted)
        tot["tp"] += tp
        tot["fp"] += fp
        tot["fn"] += fn
        cleaned = _apply(d["text"], pred)
        for sp in planted:
            if d["text"][sp["start"]:sp["end"]].lower() in cleaned.lower():
                st["escaped"] += 1
                tot["escaped"] += 1
    out = {"overall": _finish(tot)}
    for fam, st in per_family.items():
        out[fam] = _finish(st)
    return out


def _spans_from_prob(prob: list[float], thr: float) -> list[tuple[int, int]]:
    spans, start = [], None
    for i, p in enumerate(prob):
        if p >= thr and start is None:
            start = i
        elif p < thr and start is not None:
            if i - start >= 3:
                spans.append((start, i))
            start = None
    if start is not None and len(prob) - start >= 3:
        spans.append((start, len(prob)))
    return spans


def _match(planted: list[dict], pred: list[tuple[int, int]]) -> tuple[int, int, int]:
    tp = 0
    used = set()
    for sp in planted:
        for i, (a, b) in enumerate(pred):
            if i in used:
                continue
            if a < sp["end"] and sp["start"] < b:
                tp += 1
                used.add(i)
                break
    return tp, max(0, len(pred) - tp), len(planted) - tp


def _benign_stripped(text: str, pred: list[tuple[int, int]]) -> int:
    return sum(b - a for a, b in pred)


def _apply(text: str, pred: list[tuple[int, int]]) -> str:
    out, cur = [], 0
    for a, b in sorted(pred):
        out.append(text[cur:a] + "[stripped]")
        cur = b
    out.append(text[cur:])
    return "".join(out)


def _finish(st: dict) -> dict:
    p = st["tp"] / (st["tp"] + st["fp"]) if st["tp"] + st["fp"] else 0.0
    r = st["tp"] / (st["tp"] + st["fn"]) if st["tp"] + st["fn"] else 0.0
    return {"n": st["n"], "planted": st["planted"], "escaped": st["escaped"],
            "escape_rate": round(st["escaped"] / st["planted"], 4) if st["planted"] else 0.0,
            "span_precision": round(p, 4), "span_recall": round(r, 4),
            "span_f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
            "over_chars": st.get("over_chars", 0)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="charv3-extended")
    args = ap.parse_args()
    docs = [json.loads(l) for l in open("data/corpus-v3/test.jsonl", encoding="utf-8")]
    docs = [d for d in docs if not d.get("negative")][:400]
    res = {}
    for name, d in [("spanguard-char-v3", "data/models/spanguard-char-v3"),
                    ("spanguard-char", "data/models/spanguard-char")]:
        if not Path(d).exists():
            print("skip", name)
            continue
        res[name] = score(d, docs)
        print(name, json.dumps(res[name]["overall"]))
        for fam in NEW_FAMILIES:
            if fam in res[name]:
                print("  ", fam, json.dumps(res[name][fam]))
    out = Path("eval/results") / f"{args.tag}-{datetime.now().strftime('%H%M')}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "run.json").write_text(json.dumps(
        {"tag": args.tag, "set": "corpus-v3 test (new families + benign carriers)", "n_docs": len(docs),
         "systems": res}, indent=1, ensure_ascii=False))
    print("record:", out)


if __name__ == "__main__":
    main()
