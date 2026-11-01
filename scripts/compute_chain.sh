#!/usr/bin/env bash
# Training-first chain: span -> docguard -> toolguard, then LLM detect + baselines.
set -uo pipefail
cd /home/z/my-project/spanguard
echo "== $(date +%H:%M) span"
python3 training/train/train_local.py span > /tmp/chain-span.log 2>&1
echo "== $(date +%H:%M) docguard"
python3 training/train/train_local.py docguard > /tmp/chain-docguard.log 2>&1
echo "== $(date +%H:%M) toolguard"
python3 training/train/train_local.py toolguard > /tmp/chain-toolguard.log 2>&1
echo "== $(date +%H:%M) llm detect"
python3 training/eval_llm_detect.py --agent-limit 300 --public-limit 120 > /tmp/chain-llm.log 2>&1
echo "== $(date +%H:%M) baselines"
python3 training/eval_baselines_local.py > /tmp/chain-baselines.log 2>&1
echo "== $(date +%H:%M) CHAIN DONE"
ls data/models/
