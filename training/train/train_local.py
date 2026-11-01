"""Local training (recovery path): the three-model spanguard family on CPU.

Kaggle dataset mounts proved unreliable today (attachment dropped), so this
script trains the full family locally from the committed generator + recovered
teacher labels:
  1. spanguard-span-mdistil  - BIO span tagger (the guard's detector)
  2. spanguard-docguard-mdistil - doc-level attack classifier
  3. spanguard-toolguard-mdistil - tool-call argument guard
Smaller schedule than the GPU kernel (seq 288, 2 epochs) — committed as the
reproducible fallback; the Kaggle kernels remain the full-scale reference.

Artifacts land in data/models/<name>/ with a training_meta.json each.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import Dataset
from transformers import (AutoModelForSequenceClassification,
                          AutoModelForTokenClassification, AutoTokenizer,
                          DataCollatorForTokenClassification,
                          DataCollatorWithPadding, Adafactor, Trainer,
                          TrainingArguments)

REPO = Path(__file__).resolve().parents[2]
BASE = "distilbert-base-multilingual-cased"
OUT_ROOT = REPO / "data" / "models"
OUT_ROOT.mkdir(parents=True, exist_ok=True)
MAX_LEN = 288
STRIDE = 64
LABELS = ["O", "B-INJ", "I-INJ"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
SEED = 42
torch.set_num_threads(2)
t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_rows(rel: str) -> list[dict]:
    p = REPO / rel
    return [json.loads(l) for l in open(p, encoding="utf-8")]


# ------------------------------------------------------------------ span model
tok = AutoTokenizer.from_pretrained(BASE, use_fast=True)


def encode_doc(doc, tokenizer):
    text = doc["text"]
    spans = [(s["start"], s["end"]) for s in doc.get("spans", [])]
    enc = tokenizer(text, return_offsets_mapping=True, truncation=True, max_length=MAX_LEN,
                    stride=STRIDE, return_overflowing_tokens=True)
    rows = []
    for w, offsets in enumerate(enc["offset_mapping"]):
        labels = []
        prev_in = False
        for (s, e) in offsets:
            if e <= s:
                labels.append(-100)
                prev_in = False
                continue
            hit = any(gs < e and s < ge for gs, ge in spans)
            if not hit:
                labels.append(LABEL2ID["O"])
                prev_in = False
                continue
            if prev_in:
                labels.append(LABEL2ID["I-INJ"])
            else:
                labels.append(LABEL2ID["B-INJ"])
            prev_in = True
        rows.append({"input_ids": enc["input_ids"][w], "attention_mask": enc["attention_mask"][w],
                     "labels": labels})
    return rows


class RowDataset(Dataset):
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        return self.rows[i]


def span_f1_local(model, docs, max_len=MAX_LEN):
    tp = fp = fn = 0
    for d in docs:
        text = d["text"]
        enc = tok(text, return_offsets_mapping=True, truncation=True, max_length=max_len,
                  stride=STRIDE, return_overflowing_tokens=True, return_tensors="pt")
        offsets = enc.pop("offset_mapping")[0].tolist()
        enc.pop("overflow_to_sample_mapping", None)
        with torch.no_grad():
            logits = model(**enc).logits
        preds = logits.argmax(-1)[0].tolist()
        spans, cur = [], None
        for i, (s, e) in enumerate(offsets):
            if e <= s:
                if cur:
                    spans.append(cur); cur = None
                continue
            lab = LABELS[int(preds[i])]
            if lab == "B-INJ":
                if cur:
                    spans.append(cur)
                cur = [s, e]
            elif lab == "I-INJ" and cur:
                cur[1] = e
            else:
                if cur:
                    spans.append(cur); cur = None
        if cur:
            spans.append(cur)
        gold = [(s["start"], s["end"]) for s in d.get("spans", [])]
        used = set()
        for gs, ge in gold:
            hit = False
            for i, (ps, pe) in enumerate(spans):
                iou = max(0, min(ge, pe) - max(gs, ps)) / max(1, max(ge, pe) - min(gs, ps))
                if iou >= 0.5 and i not in used:
                    used.add(i); hit = True; break
            tp += hit
            fn += not hit
        fp += len(spans) - len(used)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4),
            "tp": tp, "fp": fp, "fn": fn}


def train_span():
    log("span model: loading data")
    train_docs = load_rows("data/corpus/labelled/train.jsonl")
    dev_docs = load_rows("data/corpus/labelled/dev.jsonl")
    train_rows: list[dict] = []
    for d in train_docs:
        train_rows.extend(encode_doc(d, tok))
    dev_rows: list[dict] = []
    for d in dev_docs:
        dev_rows.extend(encode_doc(d, tok))
    log(f"span windows: train {len(train_rows)} dev {len(dev_rows)}")
    model = AutoModelForTokenClassification.from_pretrained(
        BASE, num_labels=3, id2label={i: l for i, l in enumerate(LABELS)}, label2id=LABEL2ID)
    args = TrainingArguments(
        output_dir="/tmp/ckpt-span", per_device_train_batch_size=4,
        gradient_accumulation_steps=2, per_device_eval_batch_size=8,
        num_train_epochs=2, eval_strategy="epoch", save_strategy="no",
        logging_steps=100, report_to=[], seed=SEED, dataloader_num_workers=0,
        optim="adafactor",
    )
    collator = DataCollatorForTokenClassification(tok, padding=True, label_pad_token_id=-100)
    trainer = Trainer(model=model, args=args, train_dataset=RowDataset(train_rows),
                      eval_dataset=RowDataset(dev_rows), data_collator=collator)
    trainer.train()
    metrics = span_f1_local(model, dev_docs)
    log(f"span dev metrics: {metrics}")
    out = OUT_ROOT / "spanguard-span-mdistil"
    model.save_pretrained(out)
    tok.save_pretrained(out)
    n_teacher = sum(1 for d in train_docs if any(s.get("teacher") for s in d.get("spans", [])))
    json.dump({"model_name": BASE, "params_m": 135, "max_len": MAX_LEN, "stride": STRIDE,
               "labels": LABELS, "train_docs": len(train_docs), "train_windows": len(train_rows),
               "dev_docs": len(dev_docs), "teacher_labeled_docs": n_teacher,
               "dev_span_metrics": metrics, "epochs": 2, "batch_size": 8, "lr": 5e-5,
               "seed": SEED, "runtime_min": round((time.time() - t0) / 60, 1),
               "trained_on": "local CPU (recovery build; Kaggle GPU kernels committed as reference)"},
              open(out / "training_meta.json", "w"), indent=2)
    del model, trainer
    return metrics


# ------------------------------------------------------------------ classifiers
sys.path.insert(0, str(REPO / "training" / "train"))
from toolcall_gen import gen_toolcall  # noqa: E402


class ClfDataset(Dataset):
    def __init__(self, rows, tokenizer, max_len):
        self.enc = tokenizer([r["text"] for r in rows], truncation=True, max_length=max_len)
        self.labels = [1 if r["label"] in ("attack", 1, True) else 0 for r in rows]

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        item = dict(self.enc[i])
        item["labels"] = self.labels[i]
        return item


def eval_binary_local(model, rows, tokenizer, max_len):
    from transformers import DataCollatorWithPadding  # noqa: PLC0415

    lat = []
    tp = fp = fn = tn = 0
    model.eval()
    for d in rows:
        t = time.monotonic()
        enc = tokenizer(d["text"], truncation=True, max_length=max_len, return_tensors="pt")
        with torch.no_grad():
            p = model(**enc).logits.softmax(-1)[0, 1].item()
        lat.append((time.monotonic() - t) * 1000)
        pred = p >= 0.5
        gold = d["label"] in ("attack", 1, True)
        tp += pred and gold
        fp += pred and not gold
        fn += (not pred) and gold
        tn += (not pred) and (not gold)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    lats = sorted(lat)
    return {"docs": len(rows), "precision": round(prec, 4), "recall": round(rec, 4),
            "f1": round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0,
            "false_block_rate": round(fp / max(1, fp + tn), 4),
            "latency_ms_p50": round(__import__("statistics").median(lat), 1),
            "latency_ms_p95": round(lats[int(0.95 * len(lats))], 1)}


def train_classifier(name, train_rows, eval_rows, max_len, epochs=2, bs=8):
    log(f"{name}: train {len(train_rows)} eval {len(eval_rows)}")
    model = AutoModelForSequenceClassification.from_pretrained(BASE, num_labels=2)
    args = TrainingArguments(output_dir=f"/tmp/ckpt-{name}", per_device_train_batch_size=4,
                             gradient_accumulation_steps=2, per_device_eval_batch_size=8,
                             learning_rate=5e-5, num_train_epochs=epochs,
                             eval_strategy="epoch", save_strategy="no", logging_steps=100,
                             report_to=[], seed=SEED, dataloader_num_workers=0,
                             optim="adafactor")
    trainer = Trainer(model=model, args=args, train_dataset=ClfDataset(train_rows, tok, max_len),
                      eval_dataset=ClfDataset(eval_rows, tok, max_len),
                      data_collator=DataCollatorWithPadding(tok))
    trainer.train()
    metrics = eval_binary_local(model, eval_rows, tok, max_len)
    log(f"{name} metrics: {metrics}")
    out = OUT_ROOT / f"spanguard-{name}"
    model.save_pretrained(out)
    tok.save_pretrained(out)
    del model, trainer
    return metrics


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    results = {}
    if which in ("all", "span"):
        results["span"] = train_span()
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
    if which in ("all", "docguard"):
        train_docs = load_rows("data/corpus/labelled/train.jsonl")
        dev_docs = load_rows("data/corpus/labelled/dev.jsonl")
        tr = [{"text": d["text"], "label": 1 if d.get("spans") else 0} for d in train_docs]
        dv = [{"text": d["text"], "label": 1 if d.get("spans") else 0} for d in dev_docs]
        m = train_classifier("docguard", tr, dv, 288)
        json.dump({"model": "spanguard-docguard", "task": "doc-level attack classification",
                   "dev": m, "trained_on": "local CPU"},
                  open(OUT_ROOT / "spanguard-docguard" / "training_meta.json", "w"), indent=2)
        results["docguard"] = m
    if which in ("all", "toolguard"):
        tr = gen_toolcall(seed=909, n=2400)
        dv = gen_toolcall(seed=910, n=300)
        te = gen_toolcall(seed=911, n=400)
        (OUT_ROOT / "spanguard-toolguard").mkdir(parents=True, exist_ok=True)
        json.dump(te, open(OUT_ROOT / "spanguard-toolguard" / "toolcall_test_set.json", "w"),
                  ensure_ascii=False, indent=1)
        m = train_classifier("toolguard", tr, te, 256)
        json.dump({"model": "spanguard-toolguard", "task": "tool-call argument injection guard",
                   "test": m, "generator": "training/train/toolcall_gen.py gen_toolcall, seeds 909/910/911",
                   "trained_on": "local CPU"},
                  open(OUT_ROOT / "spanguard-toolguard" / "training_meta.json", "w"), indent=2)
        results["toolguard"] = m
    log("ALL DONE: " + json.dumps({k: v.get("f1") for k, v in results.items()}))


if __name__ == "__main__":
    main()
