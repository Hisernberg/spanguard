#!/usr/bin/env python3
"""Build the extended-v4 fixture: committed eval set for the v4 carrier
families (log-poison, code-comment, rag-chunk) plus ar/ja in-domain docs and
benign carriers of every shape. Seed-locked from corpus-v4 test (seed 404,
disjoint from train 808 / dev 909). Deterministic.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FAMS = ["log-poison", "code-comment", "rag-chunk"]
PER_FAMILY = 16
PER_LANG_CAP = 5


def main() -> None:
    rng = random.Random(4040)
    docs = [json.loads(l) for l in (REPO / "data/corpus-v4/test.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    attacked, carriers = [], []
    for fam in FAMS:
        pool = [d for d in docs if d.get("attack") == fam]
        rng.shuffle(pool)
        picked, per_lang = [], {}
        for d in pool:
            if per_lang.get(d["lang"], 0) >= PER_LANG_CAP:
                continue
            picked.append(d)
            per_lang[d["lang"]] = per_lang.get(d["lang"], 0) + 1
            if len(picked) >= PER_FAMILY:
                break
        attacked += picked
    # ar/ja attacked docs from the v3 families too (in-domain language check)
    arja = [d for d in docs if d.get("attack") and d["lang"] in ("ar", "ja") and d["attack"] not in FAMS]
    rng.shuffle(arja)
    attacked += arja[:24]
    benign = [d for d in docs if not d.get("attack")]
    rng.shuffle(benign)
    carriers = benign[:36]
    out = attacked + carriers
    with open(REPO / "eval" / "fixtures" / "extended-v4.jsonl", "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(d, ensure_ascii=False) + "\n" for d in out)
    fams: dict[str, int] = {}
    langs: dict[str, int] = {}
    planted = 0
    for d in out:
        key = "benign" if not d.get("attack") else d["attack"]
        fams[key] = fams.get(key, 0) + 1
        langs[d["lang"]] = langs.get(d["lang"], 0) + 1
        planted += len(d.get("spans") or [])
    print("docs:", len(out), "| planted spans:", planted)
    print("fams:", json.dumps(fams, sort_keys=True))
    print("langs:", json.dumps(langs, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
