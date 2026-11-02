#!/usr/bin/env bash
# Final eval chain: llm sidecar -> llm record -> baselines -> family (clean) -> report.
set -uo pipefail
cd /home/z/my-project/spanguard
echo "== $(date +%H:%M) llm sidecar generation"
python3 training/eval_llm_detect.py --agent-limit 300 --public-limit 120 > /tmp/c4-llm.log 2>&1
echo "== $(date +%H:%M) llm record via harness"
python3 -m spanguard.eval.cli --detectors llm-self-detect \
  --sets handwritten,agent-traffic,public-deepset --tag 2026-11-02-llm > /tmp/c4-llmrec.log 2>&1
echo "== $(date +%H:%M) open baselines"
python3 training/eval_baselines_local.py > /tmp/c4-baselines.log 2>&1
echo "== $(date +%H:%M) family re-run (clean latency)"
python3 training/eval_family_toolcall.py > /tmp/c4-family.log 2>&1
echo "== $(date +%H:%M) report render"
python3 -m spanguard report > /tmp/c4-report.log 2>&1
echo "== $(date +%H:%M) CHAIN4 DONE"
