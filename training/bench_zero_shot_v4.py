#!/usr/bin/env python3
"""Zero-shot washout benchmark: run the v3 models (char-v3, span-v2) on the
corpus-v4 test split BEFORE any v4 training exists, grouped by language and
carrier family. This is the honest weakness measurement the v4 release claims
to fix — committed record lands in eval/results/zero-shot-v4/.

Escape = planted payload survives verbatim after stripping (harness semantics).
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
os.environ.setdefault("SPANGUARD_CHAR_MODEL", str(REPO / "data" / "models" / "spanguard-char-v3"))
os.environ.setdefault("SPANGUARD_MODEL", str(REPO / "data" / "models" / "spanguard-span-mdistil-v2"))

from spanguard.detect.char_guard import char_spans  # noqa: E402
from spanguard.detect.model import SpanModel  # noqa: E402


def escaped(text: str, spans: list[dict], cleaned: str) -> bool:
    return any(text[s["start"]:s["end"]] in cleaned for s in spans)


def main() -> None:
    docs = [json.loads(l) for l in open(REPO / "data" / "corpus-v4" / "test.jsonl", encoding="utf-8")]
    attacked = [d for d in docs if d.get("attack")]
    thr_v3 = json.loads((REPO / "data/models/spanguard-char-v3/calibration.json").read_text()).get("threshold", 0.3)
    span = SpanModel(str(REPO / "data/models/spanguard-span-mdistil-v2"))

    stats = defaultdict(lambda: {"n": 0, "esc_char": 0, "esc_span": 0, "over_char": 0, "over_span": 0})
    for d in attacked:
        for key in (f"lang:{d['lang']}", f"family:{d['attack']}"):
            st = stats[key]
            st["n"] += 1
        t = d["text"]
        c_spans, _ = char_spans(t, threshold=thr_v3)
        cleaned_c = t
        for a, b in sorted(c_spans, reverse=True):
            cleaned_c = cleaned_c[:a] + "[stripped]" + cleaned_c[b:]
        s_spans = span.spans(t, threshold=0.5)
        cleaned_s = t
        for sp in sorted(s_spans, key=lambda x: -x.start):
            cleaned_s = cleaned_s[:sp.start] + "[stripped]" + cleaned_s[sp.end:]
        esc_c, esc_s = escaped(t, d["spans"], cleaned_c), escaped(t, d["spans"], cleaned_s)
        over_c = len(cleaned_c) < len(t) and not d["spans"]
        for key in (f"lang:{d['lang']}", f"family:{d['attack']}"):
            st = stats[key]
            st["esc_char"] += esc_c
            st["esc_span"] += esc_s
    benign = [d for d in docs if not d.get("attack")]
    for d in benign:
        t = d["text"]
        c_spans, _ = char_spans(t, threshold=thr_v3)
        over_c = sum(b - a for a, b in c_spans)
        s_spans = span.spans(t, threshold=0.5)
        over_s = sum(sp.end - sp.start for sp in s_spans)
        for key in (f"lang:{d['lang']}", f"family:carrier-{d['kind']}"):
            stats[key]["n"] += 1
            stats[key]["over_char"] += min(1, over_c)
            stats[key]["over_span"] += min(1, over_s)
    out = {"generated_at": datetime.now().isoformat(timespec="seconds"),
           "models": {"char": "spanguard-char-v3", "span": "spanguard-span-mdistil-v2"},
           "set": "corpus-v4 test (attacked docs + benign carriers)",
           "zero_shot": True,
           "groups": {k: {**v, "escape_char": round(v["esc_char"] / max(1, v["n"]), 4),
                          "escape_span": round(v["esc_span"] / max(1, v["n"]), 4),
                          "overstrip_char": round(v["over_char"] / max(1, v["n"]), 4),
                          "overstrip_span": round(v["over_span"] / max(1, v["n"]), 4)}
                      for k, v in sorted(stats.items())}}
    dest = REPO / "eval" / "results" / "zero-shot-v4" / "record.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    for k in sorted(out["groups"]):
        g = out["groups"][k]
        print(f"{k:28s} n={g['n']:4d} charEsc {g['escape_char']:.3f} spanEsc {g['escape_span']:.3f} "
              f"charOver {g['overstrip_char']:.3f} spanOver {g['overstrip_span']:.3f}")
    print("record:", dest)


if __name__ == "__main__":
    main()
