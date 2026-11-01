"""Kaggle model-family kernel: two more SLM guards for the spanguard family.

1. spanguard-docguard-mdistil — doc-level attack classifier (safe/attack) on the
   main corpus. The one-bit baseline that whole-document gateways use; we train
   it with the SAME data so the span-vs-classifier comparison is apples-to-apples.
2. spanguard-toolguard-mdistil — tool-call guard: classifies a function/tool CALL
   (name + JSON arguments) as benign or malicious (instructions injected into
   argument values). Ships with its own held-out benchmark (block-recall vs
   false-block).

Both are distilbert-base-multilingual-cased (135M), trained on a free GPU from a
deterministic generator committed in this file. Fictional data only.
"""

import json
import statistics
import os
import random
import time

import torch
from torch.utils.data import Dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          DataCollatorWithPadding, Trainer, TrainingArguments)

BASE = "distilbert-base-multilingual-cased"
import sys as _sys
_sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from toolcall_gen import gen_toolcall  # noqa: E402
DATA = "/kaggle/input/spanguard-corpus-v2"
WD = "/kaggle/working"
t0 = time.time()

tok = AutoTokenizer.from_pretrained(BASE)


def wait_for(path_fragment: str, deadline_s: int = 420) -> str:
    deadline = time.time() + deadline_s
    while True:
        if os.path.isdir(DATA):
            for root, _dirs, files in os.walk(DATA):
                for f in files:
                    if f == path_fragment:
                        return os.path.join(root, f)
        if time.time() > deadline:
            raise FileNotFoundError(f"{path_fragment} not found under {DATA}")
        print("[wait] dataset mount empty, retrying in 60s")
        time.sleep(60)


# ------------------------------------------------------------------ tool-call corpus
# ------------------------------------------------------------------ training helpers
class TextDataset(Dataset):
    def __init__(self, rows, tokenizer, max_len):
        self.enc = tokenizer([r["text"] for r in rows], truncation=True, max_length=max_len)
        self.labels = [1 if r["label"] in ("attack", 1, True) else 0 for r in rows]

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        item = dict(self.enc[i])
        item["labels"] = self.labels[i]
        return item


def train_classifier(model_name, train_rows, dev_rows, max_len, out_dir, epochs=3, bs=32):
    model = AutoModelForSequenceClassification.from_pretrained(BASE, num_labels=2)
    args = TrainingArguments(
        output_dir="/kaggle/working/ckpt-" + out_dir,
        per_device_train_batch_size=bs, per_device_eval_batch_size=64,
        learning_rate=5e-5, num_train_epochs=epochs,
        eval_strategy="epoch", save_strategy="no",
        fp16=torch.cuda.is_available(), logging_steps=50, report_to=[], seed=42,
    )
    tr = TextDataset(train_rows, tok, max_len)
    dv = TextDataset(dev_rows, tok, max_len)
    trainer = Trainer(model=model, args=args, train_dataset=tr, eval_dataset=dv,
                      data_collator=DataCollatorWithPadding(tok))
    trainer.train()
    model.save_pretrained(os.path.join(WD, out_dir))
    tok.save_pretrained(os.path.join(WD, out_dir))
    return model


def eval_binary(model, rows, max_len, bs=64):
    device = next(model.parameters()).device
    lat = []
    tp = fp = fn = tn = 0
    lat_rows = []
    for d in rows:
        t = time.monotonic()
        enc = tok(d["text"], truncation=True, max_length=max_len, return_tensors="pt").to(device)
        with torch.no_grad():
            p = model(**enc).logits.softmax(-1)[0, 1].item()
        dt = (time.monotonic() - t) * 1000
        lat.append(dt)
        lat_rows.append(dt)
        pred = p >= 0.5
        gold = d["label"] in ("attack", 1, True)
        tp += pred and gold
        fp += pred and not gold
        fn += (not pred) and gold
        tn += (not pred) and (not gold)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    lats = sorted(lat_rows)
    return {"docs": len(rows), "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4),
            "false_block_rate": round(fp / max(1, fp + tn), 4),
            "latency_ms_p50": round(statistics.median(lat), 1) if lat else None,
            "latency_ms_p95": round(lats[int(0.95 * len(lats))], 1) if lats else None}




# ---- 1. doc-level classifier on the main corpus ----------------------------------
train_path = wait_for("train.jsonl")
train_docs = [json.loads(l) for l in open(train_path, encoding="utf-8")]
# binary labels: attacked=1, benign traps + clean=0; drop nothing (traps ARE the hard negatives)
train_rows = [{"text": d["text"], "label": 1 if d.get("spans") else 0} for d in train_docs]
dev_path = wait_for("dev.jsonl")
dev_docs = [json.loads(l) for l in open(dev_path, encoding="utf-8")]
dev_rows = [{"text": d["text"], "label": 1 if d.get("spans") else 0} for d in dev_docs]
print("docguard rows:", len(train_rows), len(dev_rows))

doc_model = train_classifier("docguard", train_rows, dev_rows, 320, "spanguard-docguard-mdistil")
doc_metrics = eval_binary(doc_model, dev_rows, 320)
print("docguard dev:", json.dumps(doc_metrics))
json.dump({"model": "spanguard-docguard-mdistil", "task": "doc-level attack classification",
           "dev": doc_metrics}, open(os.path.join(WD, "docguard_meta.json"), "w"), indent=2)
del doc_model
torch.cuda.empty_cache() if torch.cuda.is_available() else None

# ---- 2. tool-call guard -----------------------------------------------------------
tc_train = gen_toolcall(seed=909, n=2400)
tc_dev = gen_toolcall(seed=910, n=300)
tc_test = gen_toolcall(seed=911, n=400)
json.dump(tc_test, open(os.path.join(WD, "toolcall_test_set.json"), "w"), ensure_ascii=False, indent=1)
print("toolcall rows:", len(tc_train), len(tc_dev), len(tc_test))

tc_model = train_classifier("toolguard", tc_train, tc_dev, 256, "spanguard-toolguard-mdistil")
tc_metrics = eval_binary(tc_model, tc_test, 256)
print("toolguard test:", json.dumps(tc_metrics))
json.dump({"model": "spanguard-toolguard-mdistil", "task": "tool-call argument injection guard",
           "test": tc_metrics,
           "generator": "this file, seeds 909/910/911 (train/dev/test), deterministic"},
          open(os.path.join(WD, "toolguard_meta.json"), "w"), indent=2)

print("TOTAL runtime min:", round((time.time() - t0) / 60, 1))
