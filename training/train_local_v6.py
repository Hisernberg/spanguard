#!/usr/bin/env python3
"""Local CPU training for v6: fm-v6 (medium config) + task-gate.

Kaggle credentials died with the sandbox recycle, so the v6 stack trains
locally: same architecture family, honest scope — fm-v6 uses channels 512 /
blocks 6 / emb 96 (~2.2M params), window 512, corpus-v4 subsample (9k) + the
full v6 addendum (6k docs + 14k gate pairs), 2 epochs on 4 CPU threads.
Everything else (conformal calibration, gate runtime, eval) is unchanged.

Run: python3 training/train_local_v6.py          (~60-80 min on this box)
Out: data/models/spanguard-fm-v6/, data/models/spanguard-taskgate/
"""
import json
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from spanguard.detect.char_model import CharGuardNet, build_vocab  # noqa: E402

torch.set_num_threads(4)
OUT = REPO / "data" / "models"
t_start = time.time()


def load(split: str) -> list[dict]:
    p = REPO / "data" / split
    docs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(split, len(docs), flush=True)
    return docs


# ---------------------------------------------------------------- fm-v6
train_v4 = load("corpus-v4/train.jsonl")
train_add = [json.loads(l) for l in (REPO / "data/corpus-v6-addendum/train_add.jsonl")
             .read_text(encoding="utf-8").splitlines() if l.strip()]
dev_docs = load("corpus-v4/dev.jsonl")[:600]
rng = random.Random(606)
rng.shuffle(train_v4)
train_docs = train_v4[:9000] + train_add
print("fm-v6 train total:", len(train_docs), flush=True)

vocab = build_vocab([d["text"] for d in train_docs[:6000]], cap=600)
cfg = {"channels": 512, "blocks": 8, "kernel": 5,
       "dilations": [1, 2, 4, 8, 16, 32, 64, 128], "emb": 96,
       "max_chars": 2048, "window": 512, "stride": 448}
net = CharGuardNet(len(vocab), cfg)
n_params = sum(p.numel() for p in net.parameters())
print("fm-v6 params:", n_params, flush=True)

WINDOW, STRIDE = cfg["window"], cfg["stride"]
EDGE, BOUNDARY_W = 3, 3.0


def char_labels(doc, n):
    lab = [0] * n
    for s in doc.get("spans", []):
        for i in range(max(0, s["start"]), min(n, s["end"])):
            lab[i] = 1
    return lab


def edge_weights(doc, n):
    w = [1.0] * n
    for s in doc.get("spans", []):
        for i in list(range(max(0, s["start"] - EDGE), s["start"] + EDGE)) + \
                 list(range(s["end"] - EDGE, min(n, s["end"] + EDGE))):
            if 0 <= i < n:
                w[i] = BOUNDARY_W
    return w


def encode(text, v, window):
    ids = [v.get(ch, 1) for ch in text[: cfg["max_chars"]]]
    return torch.tensor((ids + [0] * window)[:window])


def merge_spans(bits, text):
    spans, start = [], None
    for i, b in enumerate(bits):
        if b and start is None:
            start = i
        elif not b and start is not None:
            spans.append((start, i)); start = None
    if start is not None:
        spans.append((start, len(bits)))
    return [(max(0, a - 1), min(len(text), b + 1)) for a, b in spans if b - a >= 2]


opt = torch.optim.AdamW(net.parameters(), lr=8e-4, weight_decay=0.01)
EPOCHS, BATCH = 2, 12
sched = torch.optim.lr_scheduler.CosineAnnealingLR(
    opt, T_max=EPOCHS * (len(train_docs) // BATCH + 1))
gen = torch.Generator().manual_seed(42)

step, t0 = 0, time.time()
for epoch in range(EPOCHS):
    order = torch.randperm(len(train_docs), generator=gen).tolist()
    for bi in range(0, len(order), BATCH):
        batch = [train_docs[i] for i in order[bi: bi + BATCH]]
        idxs, sp_l, dc_l, wts = [], [], [], []
        for d in batch:
            text = d["text"][: cfg["max_chars"]]
            idxs.append(encode(text, vocab, WINDOW))
            sp_l.append(torch.tensor(char_labels(d, WINDOW), dtype=torch.float))
            wts.append(torch.tensor(edge_weights(d, WINDOW)))
            dc_l.append(1 if d.get("spans") else 0)
        idxs = torch.stack(idxs)
        span_logits, doc_logits = net(idxs)
        pad = (idxs != 0).float()
        loss = (F.binary_cross_entropy_with_logits(
            span_logits, torch.stack(sp_l), weight=torch.stack(wts),
            reduction="none") * pad).sum() / pad.sum().clamp(min=1) \
            + F.cross_entropy(doc_logits, torch.tensor(dc_l))
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step(); sched.step(); step += 1
        if step % 50 == 0:
            rate = step * BATCH / ((time.time() - t0) / 60)
            print(f"ep{epoch} step{step} loss {loss.item():.4f} "
                  f"{rate:.0f} docs/min eta "
                  f"{(EPOCHS * len(train_docs) - step * BATCH) / max(rate, 1):.0f} min",
                  flush=True)

net.eval()
fm_dir = OUT / "spanguard-fm-v6"
fm_dir.mkdir(parents=True, exist_ok=True)
torch.save(net.state_dict(), fm_dir / "char_guard.pt")
(fm_dir / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False))
(fm_dir / "config.json").write_text(json.dumps(
    {"net": cfg, "params": n_params, "fm": True, "version": "fm-v6-local",
     "corpus": "corpus-v4 subsample 9k + corpus-v6-addendum 6k"}, indent=1))

sweep = {}
with torch.no_grad():
    for thr in [0.3, 0.5]:
        tp = leak = planted = fp = benign_n = sb = doc_tp = doc_fp = doc_fn = 0
        for d in dev_docs:
            text = d["text"][: cfg["max_chars"]]
            idx = torch.tensor([encode(text, vocab, WINDOW)])
            sl, dl = net(idx)
            probs = sl.sigmoid()[0].tolist()[: len(text)]
            bits = [int(p >= thr) for p in probs]
            pred = merge_spans(bits, text)
            gold = [(s["start"], s["end"]) for s in d.get("spans", [])]
            planted += len(gold)
            for a, b in gold:
                if not any(a < pb and pa < b for pa, pb in pred):
                    leak += 1
            for pa, pb in pred:
                if any(pa < gb and ga < pb for ga, gb in gold):
                    tp += 1
                else:
                    fp += 1
            doc_pred = bool(pred) or float(dl.softmax(-1)[0, 1]) >= 0.5
            if gold:
                doc_tp += doc_pred; doc_fn += not doc_pred
            else:
                benign_n += 1
                doc_fp += doc_pred
                sb += sum(pb - pa for pa, pb in pred)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / max(1, tp + leak)
        sweep[str(thr)] = {"span_f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
                           "escape": round(leak / planted, 4) if planted else 0.0,
                           "overstrip_chars": round(sb / benign_n, 2) if benign_n else 0.0,
                           "doc_f1": None}
        print(thr, sweep[str(thr)], flush=True)
best_thr = min(sweep, key=lambda t: sweep[t]["escape"] + sweep[t]["overstrip_chars"] / 100)
(fm_dir / "calibration.json").write_text(json.dumps(
    {"threshold": float(best_thr), "sweep": sweep, "boundary_weight": BOUNDARY_W,
     "fm": True, "corpus": "corpus-v4 subsample + v6 addendum"}, indent=1))
(fm_dir / "training_meta.json").write_text(json.dumps(
    {"version": "fm-v6-local", "params": n_params, "cfg": cfg,
     "train_docs": len(train_docs), "epochs": EPOCHS, "batch": BATCH,
     "best_thr": float(best_thr), "dev_sweep": sweep,
     "runtime_min": round((time.time() - t_start) / 60, 1),
     "hardware": "CPU 4 threads (Kaggle token expired; local retrain)"}, indent=1))
print("fm-v6 done, thr", best_thr, "in",
      round((time.time() - t_start) / 60, 1), "min", flush=True)

# ---------------------------------------------------------------- task-gate
SEP = "\u27e6TASK\u27e7"
gate_train = [json.loads(l) for l in (REPO / "data/corpus-v6-addendum/taskgate_train.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]
gate_dev = [json.loads(l) for l in (REPO / "data/corpus-v6-addendum/taskgate_dev.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()]


def gate_text(d):
    s, e = d["span"]["start"], d["span"]["end"]
    lo, hi = max(0, s - 120), min(len(d["context"]), e + 120)
    return d["task"][:200] + SEP + d["context"][lo:hi]


gvocab = build_vocab([gate_text(d) for d in gate_train[:6000]], cap=400)
GW = 384


class GateBlock(torch.nn.Module):
    def __init__(self, ch, k, d):
        super().__init__()
        self.dw = torch.nn.Conv1d(ch, ch, k, dilation=d, padding=d * (k - 1) // 2, groups=ch)
        self.pw = torch.nn.Conv1d(ch, ch, 1)
        self.norm = torch.nn.GroupNorm(8, ch)

    def forward(self, x):
        return x + self.pw(torch.relu(self.norm(self.dw(x))))


class GateNet(torch.nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.emb = torch.nn.Embedding(vocab_size, 64, padding_idx=0)
        self.proj = torch.nn.Conv1d(64, 256, 1)
        self.blocks = torch.nn.ModuleList([GateBlock(256, 5, d) for d in [1, 2, 4, 8]])
        self.head = torch.nn.Linear(256, 2)

    def forward(self, idx):
        x = self.emb(idx).transpose(1, 2)
        x = self.proj(x)
        for b in self.blocks:
            x = b(x)
        return self.head(x.mean(dim=2))


gnet = GateNet(len(gvocab))
print("gate params:", sum(p.numel() for p in gnet.parameters()), flush=True)
gopt = torch.optim.AdamW(gnet.parameters(), lr=1e-3, weight_decay=0.01)
gacc = []
for epoch in range(3):
    order = torch.randperm(len(gate_train), generator=gen).tolist()
    gnet.train()
    tot = correct = 0
    for bi in range(0, len(order), 48):
        batch = [gate_train[i] for i in order[bi: bi + 48]]
        idxs = torch.stack([torch.tensor(encode(gate_text(d), gvocab, GW)) for d in batch])
        y = torch.tensor([d["label"] for d in batch])
        loss = F.cross_entropy(gnet(idxs), y)
        gopt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(gnet.parameters(), 1.0)
        gopt.step()
        tot += len(batch); correct += int((gnet(idxs).argmax(-1) == y).sum())
    gnet.eval()
    with torch.no_grad():
        dtc = dtn = 0
        for bi in range(0, len(gate_dev), 64):
            batch = gate_dev[bi: bi + 64]
            idxs = torch.stack([torch.tensor(encode(gate_text(d), gvocab, GW)) for d in batch])
            y = torch.tensor([d["label"] for d in batch])
            dtc += int((gnet(idxs).argmax(-1) == y).sum()); dtn += len(batch)
    gacc.append(round(dtc / dtn, 4))
    print(f"gate ep{epoch} train-acc {correct / tot:.3f} dev-acc {dtc / dtn:.4f}", flush=True)

gate_dir = OUT / "spanguard-taskgate"
gate_dir.mkdir(parents=True, exist_ok=True)
torch.save(gnet.state_dict(), gate_dir / "gate.pt")
(gate_dir / "vocab.json").write_text(json.dumps(gvocab, ensure_ascii=False))
(gate_dir / "config.json").write_text(json.dumps({"window": GW, "sep": SEP,
                                                  "version": "taskgate-v6"}, indent=1))
(gate_dir / "gate_meta.json").write_text(json.dumps(
    {"params": sum(p.numel() for p in gnet.parameters()),
     "dev_acc_by_epoch": gacc, "train_pairs": len(gate_train),
     "dev_pairs": len(gate_dev),
     "labels": {0: "strip (off-task or injection)", 1: "keep (task-relevant)"},
     "hardware": "CPU 4 threads"}, indent=1))
print("ALL DONE in", round((time.time() - t_start) / 60, 1), "min", flush=True)
