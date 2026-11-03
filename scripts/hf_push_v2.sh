#!/usr/bin/env bash
# Publish the corpus-v2 retrained span model (from the Kaggle kernel output) to HF.
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_TOKEN=$(sed -n 's/^export HF_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)

python3 - <<'EOF'
import json
import os
from pathlib import Path

from huggingface_hub import HfApi

api = HfApi(token=os.environ["HF_TOKEN"])
REPO_ID = "Nabidnur/spanguard-span-mdistil-v2"
DIR = Path("data/models/spanguard-span-mdistil-v2")
meta = json.loads((DIR / "training_meta.json").read_text()) if (DIR / "training_meta.json").exists() else {}
hw = meta.get("dev_span_metrics", {})

card = f"""---
license: apache-2.0
language: [en, de, hu, fr]
tags: [prompt-injection, ai-agent-security, meta-global-ai-hackathon-2026, distilbert]
base_model: distilbert-base-multilingual-cased
library_name: transformers
---

# spanguard-span-mdistil-v2 — corpus-v2 retrain with boundary-weighted loss

Same 135M `distilbert-base-multilingual-cased` backbone as
[spanguard-span-mdistil](https://huggingface.co/Nabidnur/spanguard-span-mdistil) — a
controlled comparison. What changed is the data and the loss:

- **corpus-v2**: 14,400 deterministic fictional docs (en/de/hu/**fr**), 2x per-family
  templates with rotating exfil URLs/secrets, **3x hard negatives** (quoted attack
  examples in runbooks, benign base64/hex, homoglyph brand names).
- **Boundary-weighted token loss**: tokens at span edges (B-INJ, the O-token before a
  span, the first O-token after) get **3x CE weight** — span boundaries are what
  surgical stripping needs. Custom Trainer in `training/train/kaggle_train_v2.py`.
- 4 epochs, batch 32, lr 5e-5, seed 42, fp16, best-by-eval-loss checkpointing.

## Dev span metrics (IoU >= 0.5)

precision {hw.get('precision', '-')} · recall {hw.get('recall', '-')} · F1 {hw.get('f1', '-')} ({json.dumps(hw.get('tp', '-'))}/{hw.get('fp', '-')}/{hw.get('fn', '-')})

Trained on a free Kaggle GPU (P100/T4); kernel + corpus are committed in the repo.
Fictional data only.
"""
(DIR / "model_card.md").write_text(card)

api.create_repo(REPO_ID, exist_ok=True, private=False)
for f in ["config.json", "tokenizer_config.json", "vocab.txt", "tokenizer.json",
          "special_tokens_map.json", "model.safetensors", "training_meta.json", "model_card.md"]:
    if (DIR / f).exists():
        api.upload_file(path_or_fileobj=DIR / f, path_in_repo=f, repo_id=REPO_ID)
print("published:", f"https://huggingface.co/{REPO_ID}")
EOF
