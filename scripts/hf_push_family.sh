#!/usr/bin/env bash
# Push all trained family models to Hugging Face + write model cards.
# Run after scripts/compute_chain.sh finishes the training steps.
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_TOKEN=$(sed -n 's/^export HF_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)

python3 - <<'EOF'
import json
from pathlib import Path

from huggingface_hub import HfApi

REPO = Path(".")
api = HfApi(token=__import__("os").environ["HF_TOKEN"])
USER = "Nabidnur"

CARDS = {
    "spanguard-span-mdistil": ("training/train/model_card.md", "token-classification"),
    "spanguard-docguard-mdistil": (None, "text-classification"),
    "spanguard-toolguard-mdistil": (None, "text-classification"),
}

def card_for(name: str, meta: dict) -> str:
    base = f"""---
license: apache-2.0
language: [en, de, hu]
tags: [prompt-injection, ai-agent-security, meta-global-ai-hackathon-2026, distilbert]
base_model: distilbert-base-multilingual-cased
library_name: transformers
pipeline_tag: {CARDS[name][1]}
---

# {name}

Part of the [spanguard](https://github.com/Hisernberg/spanguard) model family —
small guards for AI-agent traffic, distilled from the same deterministic fictional
corpus (en/de/hu, 10 attack families + benign traps). Runs on CPU.

## Training metadata

```json
{json.dumps(meta, indent=2)[:1400]}
```

## Usage

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
tok = AutoTokenizer.from_pretrained("{USER}/{name}")
model = AutoModelForSequenceClassification.from_pretrained("{USER}/{name}")
enc = tok(TEXT, return_tensors="pt")
p_attack = model(**enc).logits.softmax(-1)[0, 1].item()  # >= 0.5 -> attack
```

## Limitations

Trained on fictional agent traffic (en/de/hu). A trained guard is a mitigation, not a
guarantee — run your own evaluation on your traffic. Apache-2.0.
"""
    return base

for name, (card_path, _pt) in CARDS.items():
    d = REPO / "data" / "models" / name
    if not (d / "config.json").exists():
        print("skip", name, "(not trained)")
        continue
    meta = json.loads((d / "training_meta.json").read_text()) if (d / "training_meta.json").exists() else {}
    repo_id = f"{USER}/{name}"
    api.create_repo(repo_id, exist_ok=True, private=False)
    card = card_path and (REPO / card_path).read_text() or card_for(name, meta)
    api.upload_file(path_or_fileobj=card.encode(), path_in_repo="README.md",
                    repo_id=repo_id, repo_type="model")
    api.upload_folder(folder_path=str(d), repo_id=repo_id, repo_type="model")
    print("pushed", repo_id)
EOF
