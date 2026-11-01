#!/usr/bin/env bash
# Push the training/baselines/family kernels to Kaggle and start them.
# Auth: KAGGLE_API_TOKEN env (Kaggle access token). The corpus dataset
# (kragglenote2forwork/spanguard-corpus) is uploaded by scripts/kaggle_dataset.sh.
set -euo pipefail
cd "$(dirname "$0")/.."   # repo root
if [ -z "${KAGGLE_API_TOKEN:-}" ]; then
  KAGGLE_API_TOKEN=$(sed -n 's/^export KAGGLE_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)
  export KAGGLE_API_TOKEN
fi

push_kernel () {  # $1 slug-suffix, $2 script file, $3 gpu(true/false)
  local DIR="/tmp/kaggle-kernel-$1"
  rm -rf "$DIR" && mkdir -p "$DIR"
  cp "$2" "$DIR/$1.py"
  cat > "$DIR/kernel-metadata.json" <<EOF
{
  "id": "kragglenote2forwork/spanguard-$1",
  "title": "spanguard-$1",
  "code_file": "$1.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": "true",
  "enable_gpu": "$3",
  "enable_internet": "true",
  "dataset_data_sources": ["kragglenote2forwork/spanguard-corpus"],
  "competition_data_sources": [],
  "kernel_data_sources": [],
  "model_data_sources": []
}
EOF
  kaggle kernels push -p "$DIR" && echo "$1 kernel pushed"
}

push_kernel train training/train/kaggle_train.py true
push_kernel baselines training/train/kaggle_baselines.py false
push_kernel family training/train/kaggle_train_family.py true
kaggle kernels status kragglenote2forwork/spanguard-train || true
