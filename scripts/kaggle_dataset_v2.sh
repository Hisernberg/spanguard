#!/usr/bin/env bash
# Upload data/corpus-v2 as the Kaggle dataset spanguard-corpus-v2 (versioned).
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${KAGGLE_API_TOKEN:-}" ]; then
  KAGGLE_API_TOKEN=$(sed -n 's/^export KAGGLE_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)
  export KAGGLE_API_TOKEN
  mkdir -p ~/.kaggle
  printf '{"username":"kragglenote2forwork","key":"%s"}' "$KAGGLE_API_TOKEN" > ~/.kaggle/kaggle.json
  chmod 600 ~/.kaggle/kaggle.json
fi
DIR=/tmp/kaggle-dataset-corpus-v2
rm -rf "$DIR" && mkdir -p "$DIR"
cp data/corpus-v2/train.jsonl data/corpus-v2/dev.jsonl data/corpus-v2/test.jsonl "$DIR/"
cat > "$DIR/dataset-metadata.json" <<EOF
{
  "title": "spanguard-corpus-v2",
  "id": "kragglenote2forwork/spanguard-corpus-v2",
  "licenses": [{"name": "CC0-1.0"}]
}
EOF
kaggle datasets version -p "$DIR" -m "corpus v2: 14.4k docs, +fr language, template x2 + payload rotation, hard negatives x3, boundary-weight labels prepared" --dir-mode zip || \
kaggle datasets create -p "$DIR" --dir-mode zip
kaggle datasets status kragglenote2forwork/spanguard-corpus-v2 || true
