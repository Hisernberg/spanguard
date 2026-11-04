#!/usr/bin/env bash
# Publish the organized SpanGuard suite repo — single process: download each
# model's files from its HF repo straight into a /tmp staging tree and upload.
# (Large files do not survive on /home/z between commands in this sandbox.)
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_TOKEN=$(sed -n 's/^export HF_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)

python3 - <<'EOF'
import json
import os
import shutil
import time
import zipfile
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import HfHubHTTPError

api = HfApi(token=os.environ["HF_TOKEN"])
REPO = "Nabidnur/spanguard-suite"
STAGE = Path("/tmp/spanguard-suite")
if STAGE.exists():
    shutil.rmtree(STAGE)
MODELS, EVAL, CHARTS = STAGE / "models", STAGE / "eval", STAGE / "charts"
CORPUS, CODE = STAGE / "corpus", STAGE / "code"
for d in (MODELS, EVAL, CHARTS, CORPUS, CODE):
    d.mkdir(parents=True)

# 1. the four CPU-tier models, file-by-file into the staging tree
for name in ["spanguard-char", "spanguard-char-v3", "spanguard-char-v4", "spanguard-fm-1"]:
    for fn in ["char_guard.pt", "vocab.json", "config.json", "calibration.json"]:
        for attempt in range(4):
            try:
                p = hf_hub_download(f"Nabidnur/{name}", fn,
                                    local_dir=MODELS / name, token=os.environ["HF_TOKEN"])
                break
            except HfHubHTTPError as e:
                time.sleep(20 * (attempt + 1))
        else:
            raise RuntimeError(f"{name}/{fn} unavailable")
    print("model:", name, sorted(x.name for x in (MODELS / name).iterdir()))

# 2. eval records + fixtures
for rec in ["v5-ship-1548", "v4-flagship-1826", "v31-flagship-final-1511", "redteam-v3-0300"]:
    p = Path("eval/results") / rec / "run.json"
    if p.exists():
        (EVAL / f"{rec}.run.json").write_text(p.read_text())
for fix in ["agent-traffic", "extended-attacks", "extended-v4", "handwritten-en",
            "handwritten-de", "handwritten-hu", "public-deepset"]:
    p = Path("eval/fixtures") / f"{fix}.jsonl"
    if p.exists():
        shutil.copy2(p, EVAL / f"fixture-{fix}.jsonl")
print("eval:", len(list(EVAL.iterdir())), "files")

# 3. charts (small files survive, but read from docs/ inside the same process anyway)
for png in sorted(Path("docs/assets").glob("v5_*.png")):
    shutil.copy2(png, CHARTS / png.name)
bench = Path("docs/benchmarks")
if bench.exists():
    for svg in sorted(bench.glob("*.svg")):
        shutil.copy2(svg, CHARTS / svg.name)
print("charts:", len(list(CHARTS.iterdir())))

# 4. corpus manifests + code mirror (built and consumed in-process)
for m in ["data/corpus-manifest.json", "data/corpus-v4-manifest.json"]:
    if Path(m).exists():
        shutil.copy2(m, CORPUS / Path(m).name)
with zipfile.ZipFile(CODE / "spanguard-head.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".pytest_cache",
                                                "website", "node_modules"}
                   and not d.endswith(".egg-info")]
        for f in files:
            if f.endswith(".pyc"):
                continue
            p = Path(root) / f
            if str(p).startswith("./data/models"):
                continue
            z.write(p, os.path.relpath(p, "."))
print("code zip:", (CODE / "spanguard-head.zip").stat().st_size, "bytes")

# 5. the suite model card
card = """---
license: apache-2.0
language: [en, de, hu, fr, bn, ar, ja]
tags: [prompt-injection, ai-agent-security, span-detection, char-level, cpu, benchmark, meta-global-ai-hackathon-2026]
library_name: torch
---

# SpanGuard suite — every model, eval record, chart and fixture in one organized repo

The complete, ready-to-verify package behind [SpanGuard v5.0.0](https://github.com/Hisernberg/spanguard)
(release [v5.0.0](https://github.com/Hisernberg/spanguard/releases/tag/v5.0.0) ·
[live showcase](https://hisernberg.github.io/spanguard/) ·
[demo Space](https://huggingface.co/spaces/Nabidnur/spanguard-demo)).

## Repo map

```
models/            the four CPU-tier guards (each ~5 MB, torch, no GPU needed)
  spanguard-char/      char spans + doc verdict, corpus-v1/v2 tier      (0.79M)
  spanguard-char-v3/   + MCP / skill / buried / md-image / Bangla       (0.79M)
  spanguard-char-v4/   + log / code / rag / Arabic / Japanese           (812k)
  spanguard-fm-1/      SPG-FM-1: one model for every domain (v5)        (1.70M)
eval/              committed run records (release runs per version) + the
                   benchmark fixtures they were measured on (JSONL, fictional)
charts/            the measured v5 charts + the SVG benchmark set
corpus/            corpus manifests — seed-lock proof for the training data
code/              spanguard-head.zip — the full source snapshot (Apache-2.0)
```

The 135M models live in their own repos:
[spanguard-span-mdistil-v2](https://huggingface.co/Nabidnur/spanguard-span-mdistil-v2) (span backbone) ·
[docguard](https://huggingface.co/Nabidnur/spanguard-docguard-mdistil) ·
[toolguard](https://huggingface.co/Nabidnur/spanguard-toolguard-mdistil).

## Measured results (release run `eval/v5-ship-1548.run.json`)

| set | SPG-FM-1 (1.7M) | fast-v4 (rules + 135M span + 3-level router) |
|---|---|---|
| hand-written OOD · 62 docs | 10.4% escape · 26.4% over-strip | **4.2% escape · 17.5%** |
| agent traffic · 900 docs | **0.0% escape** · 5.2% | **0.0% escape** · 5.1% |
| public probe · 452 docs (over-strip only) | 0.0% · 45.4% | 0.0% · **24.6%** |
| extended attacks · 88 docs · 5 families | **0.0%/0.0% · doc F1 1.000 · span F1 0.917** | **0.0%/0.0% · doc F1 1.000** |
| extended-v4 · 108 docs · 7 languages | **0.0%/0.0% · doc F1 1.000 · span F1 0.901** | **0.0%**/0.1% · doc F1 0.993 |
| latency (2-thread CPU) | p50 36.7 ms | p50 14.6 ms |

Per-language doc escape on extended-v4 — SPG-FM-1: **en 0.0 · de 0.0 · hu 0.0 · fr 0.0 ·
bn 0.0 · ar 0.0 · ja 0.0** (one forward pass, no router, no language detection).

## Usage

```python
import os
from huggingface_hub import snapshot_download
os.environ["SPANGUARD_FM_MODEL"] = snapshot_download("Nabidnur/spanguard-suite")
# ^ or point at models/spanguard-fm-1 inside a local clone of this repo
from spanguard.detect.pipeline import Guard

r = Guard(mode="fm").guard(tool_output_text)
r.cleaned      # payload spans replaced with typed [stripped:*] markers
r.attacked     # document-level verdict
r.stripped     # findings with offsets + payload hashes
```

Install: `pip install "spanguard @ git+https://github.com/Hisernberg/spanguard.git"`
(+ CPU torch). Other tiers: `Guard(mode="rules" | "fast" | "fast-v2" | "fast-v3" | "fast-v4")`
with `SPANGUARD_CHAR_MODEL` / `_V3` / `_V4` pointing at the matching `models/` dirs.

## Re-verifying the numbers

```bash
pip install "spanguard @ git+https://github.com/Hisernberg/spanguard.git"
export SPANGUARD_FM_MODEL=<downloaded models/spanguard-fm-1>
export SPANGUARD_CHAR_MODEL=<models/spanguard-char>  SPANGUARD_CHAR_MODEL_V3=<models/spanguard-char-v3>
export SPANGUARD_CHAR_MODEL_V4=<models/spanguard-char-v4>
python3 -m spanguard.eval.cli --detectors spg-fm,spanguard-fast-v4 \\
  --sets handwritten,agent-traffic,public-deepset,extended-attacks,extended-v4 --tag my-run
```

The fixtures this compares against ship in `eval/` — escape and over-strip are always
reported together; a guard that deletes everything escapes 0% and is useless.

## Honesty

- Trained and benchmarked on **fictional data only** (deterministic seed-locked generator;
  manifests in `corpus/` prove the seed lock; no personal data anywhere).
- The known trades are published: fm over-strips out-of-domain benign prose (45.4% / 26.4%);
  the router stack keeps fidelity (24.6% / 17.5%). The v5 orchestration repair and its
  broken intermediates are committed and auditable in the repo's `eval/results/`.
- Out of scope: jailbreaks typed by the app's own user, malware analysis, DLP, and any
  safety guarantee. Stripping is a mitigation, not proof of safety.
- Self-rating: [8.3/10 rubric](https://github.com/Hisernberg/spanguard/blob/main/docs/rating.md).
"""
(STAGE / "README.md").write_text(card)

api.create_repo(REPO, exist_ok=True, private=False)
api.upload_folder(folder_path=str(STAGE), repo_id=REPO, repo_type="model",
                  commit_message="SpanGuard suite v5.0.0: models + eval + charts + corpus + code")
print("published: https://huggingface.co/" + REPO)
EOF
