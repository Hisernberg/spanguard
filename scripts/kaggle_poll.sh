#!/usr/bin/env bash
# Poll kernels; when a GPU slot frees (train complete), push the family kernel.
# Downloads all outputs when everything reaches a terminal state.
set -uo pipefail
export KAGGLE_API_TOKEN="${KAGGLE_API_TOKEN:-$(sed -n 's/^export KAGGLE_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)}"
cd "$(dirname "$0")/.."
FAMILY_PUSHED=0

for i in $(seq 1 90); do
  T=$(kaggle kernels status kragglenote2forwork/spanguard-train 2>&1 | tail -1)
  B=$(kaggle kernels status kragglenote2forwork/spanguard-baselines 2>&1 | tail -1)
  F=$(kaggle kernels status kragglenote2forwork/spanguard-family 2>&1 | tail -1)
  echo "$(date +%H:%M:%S) train: ${T##* } | baselines: ${B##* } | family: ${F##* }"
  if [ "$FAMILY_PUSHED" = 0 ]; then
    if [[ "$T" == *COMPLETE* || "$T" == *ERROR* ]]; then
      echo "GPU slot freeing — pushing family kernel"
      bash scripts/kaggle_push.sh 2>&1 | grep -E "family|Maximum" || true
      FAMILY_PUSHED=1
    fi
  fi
  TDONE=0; BDONE=0; FDONE=0
  [[ "$T" == *COMPLETE* || "$T" == *ERROR* ]] && TDONE=1
  [[ "$B" == *COMPLETE* || "$B" == *ERROR* ]] && BDONE=1
  [[ "$F" == *COMPLETE* || "$F" == *ERROR* || "$F" == *404* || "$FAMILY_PUSHED" = 0 ]] && FDONE=1
  if [ "$TDONE" = 1 ] && [ "$BDONE" = 1 ] && [ "$FDONE" = 1 ]; then break; fi
  sleep 60
done

mkdir -p /tmp/kaggle-out/train /tmp/kaggle-out/base /tmp/kaggle-out/family
kaggle kernels output kragglenote2forwork/spanguard-train -p /tmp/kaggle-out/train 2>&1 | tail -1
kaggle kernels output kragglenote2forwork/spanguard-baselines -p /tmp/kaggle-out/base 2>&1 | tail -1
kaggle kernels output kragglenote2forwork/spanguard-family -p /tmp/kaggle-out/family 2>&1 | tail -1
ls -la /tmp/kaggle-out/train /tmp/kaggle-out/base /tmp/kaggle-out/family | head -24
