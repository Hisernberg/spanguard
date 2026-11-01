#!/usr/bin/env bash
# Push the Spanguard corpus dataset + training/baselines kernels to Kaggle, then
# start the training kernel. Requires KAGGLE_CONFIG_DIR with kaggle.json.
set -euo pipefail
cd "$(dirname "$0")/.."   # repo root
export KAGGLE_CONFIG_DIR="${KAGGLE_CONFIG_DIR:-/home/z/my-project/.secrets/kaggle}"

STAGE=/tmp/kaggle-dataset
rm -rf "$STAGE" && mkdir -p "$STAGE/corpus" "$STAGE/labelled" "$STAGE/fixtures"
cp data/corpus/train.jsonl data/corpus/dev.jsonl data/corpus/test.jsonl "$STAGE/corpus/"
cp data/corpus/labelled/train.jsonl data/corpus/labelled/dev.jsonl "$STAGE/labelled/"
cp eval/fixtures/handwritten-en.jsonl eval/fixtures/handwritten-de.jsonl eval/fixtures/handwritten-hu.jsonl \
   eval/fixtures/public-deepset.jsonl "$STAGE/fixtures/"
cp data/corpus/labelled/manifest.json "$STAGE/labelled/" 2>/dev/null || true

cat > "$STAGE/dataset-metadata.json" <<'EOF'
{
  "title": "Spanguard Corpus",
  "id": "kragglenote2forwork/spanguard-corpus",
  "licenses": [{ "name": "CC0-1.0" }]
}
EOF

kaggle datasets create -p "$STAGE" --dir-mode zip || kaggle datasets version -p "$STAGE" --dir-mode zip -m "corpus update"
echo "dataset pushed"

TRAIN_DIR=/tmp/kaggle-kernel-train
BASE_DIR=/tmp/kaggle-kernel-base
mkdir -p "$TRAIN_DIR" "$BASE_DIR"
cp training/train/kaggle_train.py "$TRAIN_DIR/train.py"
cat > "$TRAIN_DIR/kernel-metadata.json" <<'EOF'
{
  "id": "kragglenote2forwork/spanguard-train",
  "language": "python",
  "kernel_type": "script",
  "is_private": "true",
  "enable_gpu": "true",
  "enable_internet": "true",
  "dataset_data_sources": ["kragglenote2forwork/spanguard-corpus"],
  "competition_data_sources": [],
  "kernel_data_sources": [],
  "model_data_sources": []
}
EOF
kaggle kernels push -p "$TRAIN_DIR"
echo "train kernel pushed"

cp training/train/kaggle_baselines.py "$BASE_DIR/baselines.py"
cp "$TRAIN_DIR/kernel-metadata.json" "$BASE_DIR/kernel-metadata.json"
sed -i 's/spanguard-train/spanguard-baselines/' "$BASE_DIR/kernel-metadata.json"
kaggle kernels push -p "$BASE_DIR"
echo "baselines kernel pushed"
kaggle kernels status kragglenote2forwork/spanguard-train || true
