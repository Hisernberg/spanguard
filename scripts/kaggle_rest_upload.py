#!/usr/bin/env python3
"""Kaggle dataset create-or-version via the REST API (the 2.x CLI's file-upload
path rejects KGAT tokens; basic auth over /api/v1 works)."""
import json
import os
import sys
from pathlib import Path

import requests

USER = "kragglenote2forwork"
TOKEN = os.environ["KAGGLE_TOKEN"]
AUTH = (USER, TOKEN)
SLUG = "spanguard-corpus-v2"
BASE = "https://www.kaggle.com/api/v1"

data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/kaggle-dataset-corpus-v2")
files = sorted(p for p in data_dir.iterdir() if p.suffix == ".jsonl")
version = "--version" in sys.argv

def upload_one(p: Path) -> str:
    url = f"{BASE}/datasets/upload/file/{p.name}"
    r = requests.get(url, auth=AUTH, params={
        "contentLength": p.stat().st_size,
        "lastModifiedDateUtc": int(p.stat().st_mtime * 1000)})
    r.raise_for_status()
    step = r.json()
    with open(p, "rb") as fh:
        put = requests.put(step["createUrl"], data=fh,
                           headers={"Content-Type": "application/octet-stream"})
    put.raise_for_status()
    print(f"uploaded {p.name} ({p.stat().st_size} bytes)")
    return step["token"]

tokens = [{"name": p.name, "token": upload_one(p)} for p in files]

if version:
    msg = [a for a in sys.argv if a.startswith("--msg=")][0][6:]
    body = {"versionNotes": msg}
    r = requests.post(f"{BASE}/datasets/version/new/{USER}/{SLUG}", auth=AUTH, json=body)
else:
    body = {
        "title": "spanguard-corpus-v2",
        "subtitle": "Deterministic fictional prompt-injection corpus v2",
        "ownerSlug": USER,
        "slug": SLUG,
        "isPrivate": True,
        "licenses": [{"name": "CC0-1.0"}],
        "files": tokens,
    }
    r = requests.post(f"{BASE}/datasets/create/new", auth=AUTH, json=body)
print(r.status_code, r.text[:300])
r.raise_for_status()
print("OK")
