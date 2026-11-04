#!/usr/bin/env bash
# Recovery-session eval chain: family tool-call -> hero record -> llm detect -> baselines.
set -uo pipefail
cd /home/z/my-project/spanguard
echo "== $(date +%H:%M) family tool-call eval"
python3 training/eval_family_toolcall.py > /tmp/chain-family.log 2>&1
echo "== $(date +%H:%M) hero record (rules + fast)"
SPANGUARD_MODEL="$PWD/data/models/spanguard-span-mdistil" \
python3 -m spanguard eval --detectors spanguard-rules,spanguard-fast \
  --sets handwritten,agent-traffic,public-deepset --tag 2026-11-01-full > /tmp/chain-hero.log 2>&1
echo "== $(date +%H:%M) llm detect"
python3 training/eval_llm_detect.py --agent-limit 300 --public-limit 120 > /tmp/chain-llm.log 2>&1
echo "== $(date +%H:%M) baselines"
python3 training/eval_baselines_local.py > /tmp/chain-baselines.log 2>&1
echo "== $(date +%H:%M) CHAIN3 DONE"
ls eval/results/
