#!/usr/bin/env bash
# Publish the char-level multi-task guard to Hugging Face with a model card.
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_TOKEN=$(sed -n 's/^export HF_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)

python3 - <<'EOF'
import json
import os
from pathlib import Path

from huggingface_hub import HfApi

api = HfApi(token=os.environ["HF_TOKEN"])
REPO_ID = "Nabidnur/spanguard-char"
DIR = Path("data/models/spanguard-char")
assert (DIR / "char_guard.pt").exists(), "train first: python3 training/train_char.py"

card = """---
license: apache-2.0
language: [en, de, hu, fr]
tags: [prompt-injection, ai-agent-security, char-level, meta-global-ai-hackathon-2026]
library_name: torch
---

# spanguard-char — 0.79M-parameter char-level multi-task injection guard

One tiny model, two heads: per-character injection probability (span surface)
and document-level attack probability (binary surface). Part of the
[SpanGuard](https://github.com/Hisernberg/spanguard) family.

## Why char-level

Prompt injections survive tokenizer normalization (homoglyphs, zero-width
chars, base64 blobs). A character-level dilated-conv encoder sees exactly what
the strip operation acts on — raw character offsets — with no subword
smoothing. It is the sub-millisecond tier of the family and a corroboration
signal for the 135M span model inside the `fast-v2` ensemble mode.

## Specs

| | |
|---|---|
| Parameters | 0.79M (embedding 128-char vocab + 5 dilated depthwise-separable conv blocks, 384 ch) |
| Receptive field | 81 chars per window; 1024-char windows, stride 896, up to 4096 chars/doc |
| Heads | span (per-char BCE, boundary weight x3) + doc (2-class) |
| Training data | corpus-v2: 12,000 deterministic fictional agent-traffic docs (en/de/hu/fr), 3x hard negatives |
| Calibration | dev-set threshold sweep committed in `calibration.json` |
| Latency | sub-ms per short document on CPU (2 threads) |
| Hardware | trained on CPU (2-core sandbox) in ~40 minutes |

## Usage

```python
from spanguard.detect.char_guard import char_spans
spans, doc_p = char_spans(text)   # [(start, end)], attack probability
```

Every number and the training code are committed in the repo
(`training/train_char.py`); the corpus is regenerable seed-locked.
Fictional data only.
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
