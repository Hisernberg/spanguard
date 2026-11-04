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
thr = cal.get("threshold")

card = f"""---
license: apache-2.0
language: [en, de, hu, fr, bn, ar, ja]
tags: [prompt-injection, ai-agent-security, char-level, span-detection, foundational-model, cpu, meta-global-ai-hackathon-2026]
library_name: torch
pipeline_tag: token-classification
---

# SPG-FM-1 — the SpanGuard domain foundational model (one model, no router)

v5 of the [SpanGuard](https://github.com/Hisernberg/spanguard) family collapses the
v2→v4 pattern (one small expert per domain + a regex router) into a single char-level
multi-task network trained on the **full corpus-v4 union**: every language
(en/de/hu/fr/bn/ar/ja) and every carrier family the router used to dispatch between —
MCP tool poisoning, agent skill files, buried multi-hop payloads, markdown-image
exfiltration, polite social engineering, log-file poisoning, code-comment injection,
RAG-chunk poisoning. One forward pass emits both the **document verdict** and the
**payload spans**. In-domain coverage no longer depends on the router being right:
there is no routing decision to get wrong.

## Measured results (committed run: `eval/results/v5-ship-1548` in the repo)

| set | escape ↓ | over-strip ↓ | doc F1 | span F1 |
|---|---|---|---|---|
| agent traffic · 900 docs | **0.0%** | 5.2% | 0.900 | 0.429 |
| extended attacks · 88 docs · 5 carrier families | **0.0%** | **0.0%** | **1.000** | **0.917** |
| extended carriers v4 · 108 docs · 7 languages | **0.0%** | **0.0%** | **1.000** | **0.901** |
| hand-written attacks · 62 docs (out-of-domain) | 10.4% | 26.4% | 0.893 | 0.152 |
| public prompts · 452 docs (over-strip probe) | 0.0% | 45.4% | 0.643 | — |

Per-language doc escape on extended-v4: **en 0.0 · de 0.0 · hu 0.0 · fr 0.0 · bn 0.0 ·
ar 0.0 · ja 0.0** — one model, no language detection, no router.

The sibling stack [`fast-v4`](https://github.com/Hisernberg/spanguard#the-v5-headline)
(rules + 135M span model + 3-level char router) keeps the fidelity crown on
out-of-domain prose (24.6% / 17.5% over-strip vs this model's 45.4% / 26.4%) and posts
**4.2%** hand-written OOD escape — the two form a deliberate coverage/fidelity pairing,
and the roadmap's task-conditioned stripping attacks the prose over-strip axis directly.

## Architecture

| | |
|---|---|
| Parameters | {params} (499-char vocab, emb 96, 6 dilated depthwise-separable conv blocks, 512 ch) |
| Receptive field | multi-scale via dilations 1–32; 1024-char windows, stride 896, up to 4096 chars/doc |
| Heads | span (per-char BCE, boundary weight ×3) + document (2-class) |
| Training data | corpus-v4: 16,000 seed-locked fictional docs, 7 languages × 18 carrier families |
| Calibration | dev threshold {thr}; dev sweep span P 1.000 / R 0.998, escape 0.19%, over-strip 0.0% |
| Latency | p50 36.7 ms / p95 65.6 ms per doc (2-thread sandbox CPU) |
| Training | committed Kaggle P100 kernel (`training/train/`), ~12,000 docs/min, checkpointed |

## Usage

```python
import os
# download this repo to a local dir, then:
os.environ["SPANGUARD_FM_MODEL"] = "<downloaded dir>"
from spanguard.detect.pipeline import Guard

result = Guard(mode="fm").guard(text)
result.cleaned      # payload spans replaced with typed [stripped:*] markers
result.attacked     # document-level verdict
result.stripped     # findings with offsets + payload hashes
```

Install: `pip install "spanguard @ git+https://github.com/Hisernberg/spanguard.git"`
plus `torch` (CPU wheel is enough). Run the gateway with `SPANGUARD_MODE=fm`.

## Scope & honesty

- Trained and benchmarked on **fictional data only** (deterministic seed-locked
  generator, no personal data, no scraped text).
- The model cannot catch attack phrasings neither the rules, the training distribution
  nor the corpus anticipated; on unseen prose families its document head over-fires and
  strips benign text — both axes are always reported together in the repo's records.
- Out of scope: jailbreaks typed by the app's own user, malware analysis, DLP, and any
  safety guarantee. Stripping is a mitigation, not proof of safety.
"""
(DIR / "model_card.md").write_text(card)

api.create_repo(REPO_ID, exist_ok=True, private=False)
for f in ["char_guard.pt", "vocab.json", "config.json", "calibration.json", "model_card.md"]:
    if (DIR / f).exists():
        api.upload_file(path_or_fileobj=DIR / f, path_in_repo=f, repo_id=REPO_ID)
        print("uploaded", f)
print("published:", f"https://huggingface.co/{REPO_ID}")
EOF
