#!/usr/bin/env bash
# Publish SPG-FM-1 (v5 domain foundational model) to Hugging Face with a model card.
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_TOKEN=$(sed -n 's/^export HF_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)

python3 - <<'EOF'
import json
import os
from pathlib import Path

from huggingface_hub import HfApi

api = HfApi(token=os.environ["HF_TOKEN"])
REPO_ID = "Nabidnur/spanguard-fm-1"
DIR = Path("data/models/spanguard-fm-1")
assert (DIR / "char_guard.pt").exists(), "train first: python3 training/train_fm.py"
cal = json.loads((DIR / "calibration.json").read_text())
cfg = json.loads((DIR / "config.json").read_text())
params = cfg.get("params", "1.70M")
sw = cal.get("sweep", {})
sw_txt = json.dumps({k: v["escape"] for k, v in sw.items()}) if sw else "see calibration.json"

card = f"""---
license: apache-2.0
language: [en, de, hu, fr, bn, ar, ja]
tags: [prompt-injection, ai-agent-security, char-level, foundational-model, domain-model, meta-global-ai-hackathon-2026]
library_name: torch
---

# SPG-FM-1 — the SpanGuard domain foundational model (one model, no router)

v5 of the [SpanGuard](https://github.com/Hisernberg/spanguard) family collapses
the v2→v4 pattern (one small expert per domain + a regex router) into a single
char-level multi-task network trained on the **full corpus-v4 union**: every
language (en/de/hu/fr/bn/ar/ja) and every carrier family the router used to
dispatch between — MCP tool poisoning, skill files, buried multi-hop, md-image
exfiltration, polite social engineering, log-file poisoning, code-comment
injection, RAG-chunk poisoning. One forward pass emits both the document
verdict and the payload spans. In-domain coverage no longer depends on the
router being right: there is no routing decision to get wrong.

## Architecture

| | |
|---|---|
| Parameters | {params} (499-char vocab, emb 96, 6 dilated depthwise-separable conv blocks, 512 ch) |
| Receptive field | multi-scale via dilations 1–32; 1024-char windows, stride 896, up to 4096 chars/doc |
| Heads | span (per-char BCE, boundary weight x3) + doc (2-class) |
| Training data | corpus-v4: 16,000 seed-locked docs, 7 languages x 18 carrier families |
| Calibration | dev threshold {cal.get("threshold")} (escape+overstrip argmin); sweep {sw_txt} |
| Latency | ~2–4 ms/doc on CPU (2 threads) |

## Usage

```python
import os
os.environ["SPANGUARD_FM_MODEL"] = "<downloaded dir>"
from spanguard.detect.pipeline import Guard
result = Guard(mode="fm").guard(text)   # doc verdict + payload spans, one model
```

## Status

Benchmark vs the fast-v4 router stack and the binary baselines lands in the
repo's `eval/results/` (v5-fm runs) — the README carries the measured table.
Fictional data only; training code committed (`training/train_fm.py`,
checkpointed + resumable).
"""
(DIR / "model_card.md").write_text(card)

api.create_repo(REPO_ID, exist_ok=True, private=False)
api.upload_file(path_or_fileobj=DIR / "char_guard.pt",
                path_in_repo="char_guard.pt", repo_id=REPO_ID)
for f in ["vocab.json", "config.json", "calibration.json", "model_card.md"]:
    if (DIR / f).exists():
        api.upload_file(path_or_fileobj=DIR / f, path_in_repo=f, repo_id=REPO_ID)
print("published:", f"https://huggingface.co/{REPO_ID}")
EOF
