#!/usr/bin/env bash
# v6 mega-run: kernel artifacts -> conformal calibration -> full eval -> agent
# loop -> semantic judge. Each python stage re-fetches weights if /tmp lost them;
# the heavy stages each run in ONE process so nothing big rests on disk.
set -uo pipefail
cd "$(dirname "$0")/.."
source /home/z/my-project/.secrets/env
export KAGGLE_ACCESS_TOKEN=$(sed -n 's/^export KAGGLE_API_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)
mkdir -p /tmp/kv6-out

# stage 0: kernel artifacts (idempotent)
if [ ! -f /tmp/kv6-out/spanguard-fm-large/char_guard.pt ]; then
  kaggle kernels output kragglenote2forwork/spanguard-fm-v6 -p /tmp/kv6-out 2>&1 | tail -1
  ls -la /tmp/kv6-out/ | head -8
fi

export SPANGUARD_FM_MODEL=/tmp/kv6-out/spanguard-fm-large
export SPANGUARD_TASKGATE=/tmp/kv6-out/spanguard-taskgate
export SPANGUARD_CHAR_MODEL=/tmp/kv6-out/spanguard-char
export SPANGUARD_CHAR_MODEL_V3=/tmp/kv6-out/spanguard-char-v3
export SPANGUARD_CHAR_MODEL_V4=/tmp/kv6-out/spanguard-char-v4
export SPANGUARD_MODEL=/tmp/kv6-out/spanguard-span

python3 scripts/v6_calibration_and_eval.py
