#!/usr/bin/env bash
# Idempotent poll: push the family kernel whenever a GPU slot is free and family
# hasn't started; download all outputs once everything is terminal.
set -uo pipefail
export KAGGLE_API_TOKEN="${KAGGLE_API_TOKEN:-$(sed -n 's/^export KAGGLE_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)}"
cd "$(dirname "$0")/.."

st () { kaggle kernels status "kragglenote2forwork/spanguard-$1" 2>&1 | tail -1; }

for i in $(seq 1 150); do
  T=$(st train); B=$(st baselines); F=$(st family)
  echo "$(date +%H:%M:%S) train:${T##*KernelWorkerStatus.} baselines:${B##*KernelWorkerStatus.} family:${F##*KernelWorkerStatus.}"
  if [[ "$F" != *RUNNING* && "$F" != *QUEUED* && "$F" != *COMPLETE* ]]; then
    if [[ "$T" == *COMPLETE* || "$T" == *ERROR* || "$T" == *CANCEL* ]]; then
      bash scripts/kaggle_push.sh > /tmp/family-push.log 2>&1 || true
    fi
  fi
  if [[ "$T" == *COMPLETE* || "$T" == *ERROR* ]] && [[ "$B" == *COMPLETE* || "$B" == *ERROR* ]] && [[ "$F" == *COMPLETE* || "$F" == *ERROR* ]]; then
    break
  fi
  sleep 60
done

for k in train baselines family; do
  mkdir -p "/tmp/kaggle-out/$k"
  kaggle kernels output "kragglenote2forwork/spanguard-$k" -p "/tmp/kaggle-out/$k" 2>&1 | tail -1
done
ls -la /tmp/kaggle-out/*/ | head -30
