"""Kaggle training kernel: distilbert-base-multilingual-cased span tagger (SLM, 135M).

Runs on Kaggle GPU. Reads the Spanguard corpus dataset, builds BIO labels from
char spans, trains with fp16, evaluates span F1 on the dev split, and writes the
model + training_meta.json to /kaggle/working for download. No secrets needed:
the model is pushed to HuggingFace from the sandbox afterwards.

Self-contained on purpose (kernel = reproducible artifact committed to the repo).
"""

import json
import os
import time

import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)

MODEL_NAME = "distilbert-base-multilingual-cased"
MAX_LEN = 384
STRIDE = 64
LABELS = ["O", "B-INJ", "I-INJ"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
OUT = "/kaggle/working/spanguard-span-mdistil"
DATA = "/kaggle/input/spanguard-corpus-v2"

t_start = time.time()


def load(split):
    """Locate a split by basename under the dataset mount, waiting out dataset
    version reprocessing (the mount can lag for minutes after a version push)."""
    deadline = time.time() + 420
    while True:
        wanted = []
        if os.path.isdir(DATA):
            for root, _dirs, files in os.walk(DATA):
                for f in files:
                    if f == f"{split}.jsonl":
                        wanted.append(os.path.join(root, f))
        if wanted:
            break
        if time.time() > deadline:
            listing = os.listdir("/kaggle/input") if os.path.isdir("/kaggle/input") else []
            raise FileNotFoundError(f"{split}.jsonl not found under {DATA}; /kaggle/input: {listing}")
        print(f"[wait] dataset mount empty, retrying in 60s ({split})")
        time.sleep(60)
    for p in wanted:  # teacher-labelled version wins for train/dev
        if "labelled" in p:
            path = p
            break
    else:
        path = min(wanted)
    docs = [json.loads(l) for l in open(path, encoding="utf-8")]
    print(split, len(docs), "<-", path)
    return docs


train_docs = load("train")
dev_docs = load("dev")

tok = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)


def encode_doc(doc):
    """Tokenize with sliding windows; BIO labels aligned via offset mapping."""
    text = doc["text"]
    spans = [(s["start"], s["end"]) for s in doc.get("spans", [])]
    enc = tok(text, return_offsets_mapping=True, truncation=True, max_length=MAX_LEN,
              stride=STRIDE, return_overflowing_tokens=True)
    windows = []
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
            any(gs <= s < ge for gs, ge in spans) and not prev_in
            # B if this token starts a gold span (or continues after a gap)
            if any(gs <= s < ge for gs, ge in spans) and (not prev_in or s == 0):
                labels.append(LABEL2ID["B-INJ"])
            else:
                labels.append(LABEL2ID["I-INJ"] if prev_in else LABEL2ID["B-INJ"])
            prev_in = True
        windows.append({"input_ids": enc["input_ids"][w], "attention_mask": enc["attention_mask"][w], "labels": labels})
    return windows


class DocDataset(Dataset):
    def __init__(self, docs):
        self.rows = []
        for d in docs:
            self.rows.extend(encode_doc(d))

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        return self.rows[i]


train_ds = DocDataset(train_docs)
dev_ds = DocDataset(dev_docs)
print("windows:", len(train_ds), len(dev_ds))

model = AutoModelForTokenClassification.from_pretrained(
    MODEL_NAME, num_labels=len(LABELS), id2label={i: l for i, l in enumerate(LABELS)},
    label2id=LABEL2ID)

args = TrainingArguments(
    output_dir="/kaggle/working/ckpt",
    per_device_train_batch_size=32,
    per_device_eval_batch_size=64,
    learning_rate=5e-5,
    num_train_epochs=3,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    fp16=torch.cuda.is_available(),
    logging_steps=50,
    report_to=[],
    seed=42,
)

collator = DataCollatorForTokenClassification(tok, padding=True, label_pad_token_id=-100)

trainer = Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=dev_ds,
                  data_collator=collator)
trainer.train()


# ---- decode spans from predictions, compute span F1 on the DEV docs -------------
def predict_spans(doc):
    text = doc["text"]
    enc = tok(text, return_offsets_mapping=True, truncation=True, max_length=MAX_LEN,
              stride=STRIDE, return_overflowing_tokens=True, padding="max_length",  # uneven last window crashes tensor stacking
              return_tensors="pt")
    offsets = enc.pop("offset_mapping")[0].tolist()
    enc.pop("overflow_to_sample_mapping", None)
    with torch.no_grad():
        logits = model(**{k: v.cuda() if torch.cuda.is_available() else v for k, v in enc.items()}).logits
    probs = logits.softmax(-1)[0].cpu().numpy()
    preds = probs.argmax(-1)
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
    return spans


def span_f1(docs, thresh_chars=0):
    tp = fp = fn = 0
    for d in docs:
        gold = [(s["start"], s["end"]) for s in d.get("spans", [])]
        pred = [tuple(s) for s in predict_spans(d)]
        used = set()
        for gs, ge in gold:
            hit = False
            for i, (ps, pe) in enumerate(pred):
                iou = max(0, min(ge, pe) - max(gs, ps)) / max(1, max(ge, pe) - min(gs, ps))
                if iou >= 0.5 and i not in used:
                    used.add(i); hit = True; break
            tp += hit
            fn += not hit
        fp += len(pred) - len(used)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return round(p, 4), round(r, 4), round(f, 4), {"tp": tp, "fp": fp, "fn": fn}


p, r, f, counts = span_f1(dev_docs)
print("DEV span P/R/F1:", p, r, f, counts)

model.save_pretrained(OUT)
tok.save_pretrained(OUT)

n_att = sum(1 for d in train_docs if d.get("spans"))
n_teacher = sum(1 for d in train_docs if any(s.get("teacher") for s in d.get("spans", [])))
meta = {
    "model_name": MODEL_NAME, "params_m": 135, "max_len": MAX_LEN, "stride": STRIDE,
    "labels": LABELS, "train_docs": len(train_docs), "train_windows": len(train_ds),
    "dev_docs": len(dev_docs), "attacked_train_docs": n_att, "teacher_labeled_docs": n_teacher,
    "dev_span_metrics": {"precision": p, "recall": r, "f1": f, **counts},
    "epochs": 3, "batch_size": 32, "lr": 5e-5, "seed": 42,
    "runtime_min": round((time.time() - t_start) / 60, 1),
    "trained_on": "Kaggle GPU (P100/T4), fp16",
}
json.dump(meta, open(os.path.join(OUT, "training_meta.json"), "w"), indent=2)
print(json.dumps(meta, indent=2))
