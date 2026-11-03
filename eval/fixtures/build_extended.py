#!/usr/bin/env python3
"""Build the extended-attacks fixture: a committed eval set for the corpus-v3
domain families (MCP tool-description poisoning, agent skill files, buried
multi-hop, markdown-image exfil, polite social engineering) plus benign
carriers of the same shapes (over-strip probe).

Seed-locked selection from the corpus-v3 TEST split (which the v3 models were
NOT trained on — the test seed 303 is disjoint from train 606 / dev 707).
Every doc carries planted span offsets from the generator, so span-level P/R
is scored, not just whole-doc. Deterministic; writes eval/fixtures/extended-attacks.jsonl.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NEW_FAMILIES = ["mcp-poison", "skill-file", "buried-multihop", "md-image-exfil", "social-polite"]
PER_FAMILY_ATTACKED = 14
PER_LANG_CAP = 4


def main() -> None:
    rng = random.Random(9090)
    src = REPO / "data" / "corpus-v3" / "test.jsonl"
    docs = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    attacked, benign = [], []
    for d in docs:
        if d.get("negative") or d.get("attack"):
            continue
        benign.append(d)
    for fam in NEW_FAMILIES:
        pool = [d for d in docs if d.get("attack") == fam]
        rng.shuffle(pool)
        picked, per_lang = [], {}
        for d in pool:
            if per_lang.get(d["lang"], 0) >= PER_LANG_CAP:
                continue
            picked.append(d)
            per_lang[d["lang"]] = per_lang.get(d["lang"], 0) + 1
            if len(picked) >= PER_FAMILY_ATTACKED:
                break
        attacked += picked
    rng.shuffle(benign)
    carriers = benign[: 3 * len(NEW_FAMILIES)]
    # benign carriers of the same shapes: prefer mcp/skill kinds
    shape_benign = [d for d in benign if d.get("kind") in {"mcp-tool-def", "skill-md"}]
    carriers = (shape_benign[:18] + [d for d in benign if d not in shape_benign][:18])[:36]
    out = attacked + carriers
    with open(REPO / "eval" / "fixtures" / "extended-attacks.jsonl", "w", encoding="utf-8") as fh:
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
    print("IDs are hash-of-text from the generator; test split seed 303 (train/dev used 606/707).")


if __name__ == "__main__":
    sys.exit(main())
