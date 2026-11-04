#!/usr/bin/env bash
# v6 mega-run: HF model restore -> conformal calibration (alpha sweep) -> full
# guard eval -> agent loop -> latency. One bash invocation so nothing large
# rests on disk between steps (this sandbox reclaims big files).
set -uo pipefail
cd "$(dirname "$0")/.."
source /home/z/my-project/.secrets/env
mkdir -p /tmp/kv6-out

python3 - <<'PY'
import os
from huggingface_hub import snapshot_download
tok = os.environ.get("HF_TOKEN")
for repo, dest in [("Nabidnur/spanguard-char", "/tmp/kv6-out/spanguard-char"),
                   ("Nabidnur/spanguard-char-v3", "/tmp/kv6-out/spanguard-char-v3"),
                   ("Nabidnur/spanguard-char-v4", "/tmp/kv6-out/spanguard-char-v4"),
                   ("Nabidnur/spanguard-span-mdistil-v2", "/tmp/kv6-out/spanguard-span")]:
    if not os.path.exists(os.path.join(dest, "char_guard.pt")) and \
       not os.path.exists(os.path.join(dest, "model.safetensors")):
        snapshot_download(repo, local_dir=dest, token=tok)
        print("restored", dest, flush=True)
    else:
        print("cached", dest, flush=True)
PY

export SPANGUARD_FM_MODEL="$PWD/data/models/spanguard-fm-v6"
export SPANGUARD_TASKGATE="$PWD/data/models/spanguard-taskgate"
export SPANGUARD_CHAR_MODEL=/tmp/kv6-out/spanguard-char
export SPANGUARD_CHAR_MODEL_V3=/tmp/kv6-out/spanguard-char-v3
export SPANGUARD_CHAR_MODEL_V4=/tmp/kv6-out/spanguard-char-v4
export SPANGUARD_MODEL=/tmp/kv6-out/spanguard-span

python3 scripts/v6_calibration_and_eval.py
