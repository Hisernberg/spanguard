#!/usr/bin/env python3
"""Build the extended-v6 fixture: 500 docs, the v6 scale-up of the adversarial
story. 250 attack / 250 benign across 7 languages and every carrier shape:

- adv-paraphrase: v6 paraphrase-matrix attacks (synonym slots, interruptions,
  role-play prefaces, quoted-memo framing, mixed-language payloads) — fresh
  seed 4242, disjoint from the training addendum (seed 611);
- classic v4 families drawn from the corpus-v4 TEST split only;
- cross-language injections: payload language != carrier language;
- hard benign: user-voice requests, action items, SOPs, support threads,
  CTAs, invoices (the exact shapes the fm doc head over-fires on);
- standard benign carriers from the corpus-v4 test split.

Every id is checked against the training surface (corpus-v4 train+dev, v6
addendum) and dropped on collision. Seed-locked, deterministic.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "training"))

import gen_corpus_v4 as v4  # noqa: E402
import gen_corpus_v6 as v6  # noqa: E402

N_ATTACK, N_BENIGN = 250, 250


def main() -> None:
    rng = random.Random(4242)
    v4_test = [json.loads(l) for l in
               (REPO / "data/corpus-v4/test.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    train_ids: set[str] = set()
    for split in ["train.jsonl", "dev.jsonl"]:
        for line in (REPO / "data/corpus-v4" / split).read_text(encoding="utf-8").splitlines():
            if line.strip():
                train_ids.add(json.loads(line)["id"])
    add_dir = REPO / "data/corpus-v6-addendum"
    if (add_dir / "train_add.jsonl").exists():
        for line in (add_dir / "train_add.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                train_ids.add(json.loads(line)["id"])

    langs = list(v6.BENIGN_REQUEST)
    docs: list[dict] = []

    # 1. adv-paraphrase attacks (fresh generator seed)
    seen: set[str] = set()
    while sum(1 for d in docs if d.get("attack")) < 100:
        d = v6._adv_doc(rng, rng.choice(langs))
        if d["id"] in train_ids or d["id"] in seen:
            continue
        seen.add(d["id"])
        docs.append(d)

    # 2. classic v4 families from the TEST split only
    pool = [d for d in v4_test if d.get("attack")]
    rng.shuffle(pool)
    for d in pool:
        if sum(1 for x in docs if x.get("attack")) >= 175:
            break
        if d["id"] in train_ids or d["id"] in seen:
            continue
        seen.add(d["id"])
        docs.append(d)

    # 3. cross-language: latin-script benign carrier + non-latin payload (and reverse)
    xl_done = 0
    while xl_done < 75:
        base = v4.make_doc_v4(rng, rng.choice(["en", "de", "hu", "fr"]), None)
        payload = v6._paraphrase_override(rng)
        if xl_done % 2:
            base = v4.make_doc_v4(rng, rng.choice(["ar", "ja", "bn"]), None)
            payload = v6._paraphrase_override(rng)
        text = base["text"] + "\n" + payload
        did = __import__("hashlib").sha256(text.encode()).hexdigest()[:16]
        if did in train_ids or did in seen:
            continue
        seen.add(did)
        docs.append({"id": did, "lang": base["lang"], "kind": base.get("kind", "email"),
                     "text": text, "attack": "adv-crosslang", "negative": False,
                     "spans": [{"start": len(base["text"]) + 1, "end": len(text),
                                "family": "adv-crosslang"}]})
        xl_done += 1

    # 4. hard benign (fresh seed, same generator as training but disjoint ids)
    while sum(1 for d in docs if not d.get("attack")) < 175:
        d = v6._benign_doc(rng, rng.choice(langs))
        if d["id"] in train_ids or d["id"] in seen:
            continue
        seen.add(d["id"])
        docs.append(d)

    # 5. standard benign carriers from the TEST split
    pool = [d for d in v4_test if not d.get("attack")]
    rng.shuffle(pool)
    for d in pool:
        if sum(1 for x in docs if not x.get("attack")) >= 250:
            break
        if d["id"] in train_ids or d["id"] in seen:
            continue
        seen.add(d["id"])
        docs.append(d)

    rng.shuffle(docs)
    out = REPO / "eval" / "fixtures" / "extended-v6.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")

    fams: dict[str, int] = {}
    langs_c: dict[str, int] = {}
    planted = 0
    for d in docs:
        key = "benign" if not d.get("attack") else d["attack"]
        fams[key] = fams.get(key, 0) + 1
        langs_c[d["lang"]] = langs_c.get(d["lang"], 0) + 1
        planted += len(d.get("spans") or [])
    manifest = {"docs": len(docs), "attack": sum(1 for d in docs if d.get("attack")),
                "benign": sum(1 for d in docs if not d.get("attack")),
                "planted_spans": planted, "families": fams, "languages": langs_c,
                "seed": 4242, "disjoint_from": ["corpus-v4 train+dev", "corpus-v6-addendum"]}
    (REPO / "eval" / "fixtures" / "extended-v6-manifest.json").write_text(
        json.dumps(manifest, indent=1))
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    sys.exit(main())
