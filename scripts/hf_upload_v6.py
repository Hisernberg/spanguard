#!/usr/bin/env python3
"""Ship v6 to HuggingFace with 429-tolerant retries.

Uploads, in order:
1. Nabidnur/spanguard-fm-v6      (weights + calibration_v2 + meta)
2. Nabidnur/spanguard-taskgate   (gate weights + meta)
3. Nabidnur/spanguard-suite      (records + charts under records/v6-*, models are separate repos)

Run AFTER the mega-run so calibration_v2.json is in the model dir.
"""
import os
import sys
import time
from pathlib import Path

from huggingface_hub import HfApi

REPO = Path(__file__).resolve().parents[1]
api = HfApi(token=os.environ["HF_TOKEN"])

FM = REPO / "data" / "models" / "spanguard-fm-v6"
GATE = REPO / "data" / "models" / "spanguard-taskgate"
SUITE_RECORDS = REPO / "eval" / "results"
SUITE_ASSETS = REPO / "docs" / "assets"


def up(repo, **kw):
    for i in range(8):
        try:
            api.create_repo(repo, exist_ok=True, private=False)
            api.upload_folder(repo_id=repo, **kw)
            print("uploaded:", repo, kw.get("path_in_repo", "<root>"), flush=True)
            return True
        except Exception as e:  # noqa: BLE001
            print(f"retry {i + 1} {repo}: {str(e)[:110]}", flush=True)
            time.sleep(75)
    print("GAVE UP:", repo, flush=True)
    return False


ok = True
ok &= up("Nabidnur/spanguard-fm-v6", folder_path=str(FM),
         commit_message="v6: SPG-FM (2.23M, corpus-v4 + v6 addendum, CPU retrain) + "
                        "split-conformal calibration_v2 (alpha sweep shipped)")
ok &= up("Nabidnur/spanguard-taskgate", folder_path=str(GATE),
         commit_message="v6: task-conditioned gate (292k) — keep/strip for band spans given the task")
for rec in sorted(SUITE_RECORDS.glob("*v6*")):
    if rec.is_dir():
        ok &= up("Nabidnur/spanguard-suite", folder_path=str(rec),
                 path_in_repo=f"records/{rec.name}",
                 commit_message=f"v6 record {rec.name}")
for img in sorted(SUITE_ASSETS.glob("v6_*.png")):
    ok &= up("Nabidnur/spanguard-suite", path_or_fileobj=str(img),
             path_in_repo=f"records/v6-charts/{img.name}",
             commit_message=f"v6 chart {img.name}")
sys.exit(0 if ok else 1)
