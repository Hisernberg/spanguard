#!/usr/bin/env bash
# Post-toolguard chain: span re-run, normalize family dir names, llm, baselines, family eval.
set -uo pipefail
cd /home/z/my-project/spanguard
# wait for any running training to finish
while pgrep -f "train_local.py toolguard" > /dev/null; do sleep 30; done
echo "== $(date +%H:%M) normalize family dirs"
for m in docguard toolguard; do
  if [ -d "data/models/spanguard-$m" ] && [ ! -d "data/models/spanguard-$m-mdistil" ]; then
    mv "data/models/spanguard-$m" "data/models/spanguard-$m-mdistil"
    sed -i "s/\"model\": \"spanguard-$m\"/\"model\": \"spanguard-$m-mdistil\"/" "data/models/spanguard-$m-mdistil/training_meta.json" 2>/dev/null || true
  fi
done
ls data/models/
echo "== $(date +%H:%M) span"
python3 training/train/train_local.py span > /tmp/chain-span.log 2>&1
echo "== $(date +%H:%M) llm detect"
python3 training/eval_llm_detect.py --agent-limit 300 --public-limit 120 > /tmp/chain-llm.log 2>&1
echo "== $(date +%H:%M) baselines"
python3 training/eval_baselines_local.py > /tmp/chain-baselines.log 2>&1
echo "== $(date +%H:%M) family tool-call eval"
python3 training/eval_family_toolcall.py > /tmp/chain-family.log 2>&1
echo "== $(date +%H:%M) CHAIN2 DONE"
ls data/models/
