#!/usr/bin/env bash
# After the Kaggle train kernel completes: fetch the span model artifact, push it to
# Hugging Face, and run the local spanguard-fast eval to produce the run record.
set -euo pipefail
cd "$(dirname "$0")/.."
export KAGGLE_API_TOKEN="${KAGGLE_API_TOKEN:-$(sed -n 's/^export KAGGLE_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)}"
export HF_TOKEN=$(sed -n 's/^export HF_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)

echo "== fetch kernel output"
rm -rf /tmp/kaggle-out/train && mkdir -p /tmp/kaggle-out/train
kaggle kernels output kragglenote2forwork/spanguard-train -p /tmp/kaggle-out/train

MODEL_DIR=$(find /tmp/kaggle-out/train -maxdepth 2 -name config.json | head -1 | xargs dirname)
echo "model dir: $MODEL_DIR"
ls "$MODEL_DIR"

echo "== push to Hugging Face"
python3 - "$MODEL_DIR" <<'EOF'
import json, sys, os
from huggingface_hub import HfApi
model_dir = sys.argv[1]
meta_path = os.path.join(model_dir, "training_meta.json")
meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
card = open("training/train/model_card.md").read()
card = card.replace("**Decontamination**: eval sets are generated from disjoint seeds and checked by content hash.",
                    "**Decontamination**: eval sets are generated from disjoint seeds and checked by content hash.\n\n## Training metadata\n\n```json\n"
                    + json.dumps(meta, indent=2)[:1200] + "\n```")
api = HfApi(token=os.environ["HF_TOKEN"])
repo = "Nabidnur/spanguard-span-mdistil"
api.create_repo(repo, exist_ok=True, private=False)
api.upload_file(path_or_fileobj=card.encode(), path_in_repo="README.md", repo_id=repo, repo_type="model")
api.upload_folder(folder_path=model_dir, repo_id=repo, repo_type="model")
print("pushed to", repo)
EOF

echo "== local eval (spanguard-fast)"
export SPANGUARD_MODEL="$MODEL_DIR"
python3 -m spanguard eval --detectors spanguard-fast --sets handwritten,agent-traffic,public-deepset --tag 2026-11-01-fast
echo done
