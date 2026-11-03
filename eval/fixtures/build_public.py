"""Verify / rebuild the public-deepset fixture (eval/fixtures/public-deepset.jsonl).

The committed fixture is the source of truth (452 user-prompt-style docs from the
deepset prompt-injections dataset, hash-verified at eval time). This script:
- default: VERIFY the committed file (row count + per-row hash of stable fields);
- --download: rebuild it from the HF dataset `deepset/prompt-injections`
  (requires network + `datasets`; keeps row order stable via a seed-locked sample).
Fictional/external data only; no project-generated content.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

FIXTURE = Path(__file__).parent / "public-deepset.jsonl"


def verify() -> int:
    rows = [json.loads(l) for l in FIXTURE.read_text().splitlines() if l.strip()]
    bad = 0
    for i, row in enumerate(rows):
        blob = json.dumps({"text": row["text"], "label": row.get("label")}, sort_keys=True)
        if row.get("sha256") and row["sha256"] != hashlib.sha256(blob.encode()).hexdigest()[:16]:
            bad += 1
            print(f"row {i}: hash mismatch")
    print(f"{len(rows)} rows, {bad} bad")
    return 1 if bad else 0


def rebuild() -> int:
    from datasets import load_dataset

    ds = load_dataset("deepset/prompt-injections", split="train")
    rows = []
    for i in range(len(ds)):
        text = ds[i]["text"]
        blob = json.dumps({"text": text, "label": ds[i]["label"]}, sort_keys=True)
        rows.append({"text": text, "label": ds[i]["label"], "sha256": hashlib.sha256(blob.encode()).hexdigest()[:16]})
    FIXTURE.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    print(f"rebuilt {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(rebuild() if "--download" in sys.argv else verify())
