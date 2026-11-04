"""Kaggle v6 kernel: SPG-FM-Large (3.4M) + task-conditioned gate (v6-B).

Data sources: kragglenote2forwork/spanguard-fm-train (corpus-v4: train/dev.jsonl)
and kragglenote2forwork/spanguard-corpus-v6-addendum (train_add.jsonl,
taskgate_train.jsonl, taskgate_dev.jsonl).

fm-large = the v5 architecture scaled up (channels 640, blocks 8, emb 128) and
trained on corpus-v4 + the v6 addendum (adversarial paraphrases + hard benign
negatives targeting the over-strip axis).

task-gate = small char CNN over "task <SEP> span-context" deciding keep/strip
for spans the fm head is unsure about (v6-B, task-conditioned stripping).

Self-contained (architecture embedded). Outputs to /kaggle/working:
  spanguard-fm-large/{char_guard.pt,vocab.json,config.json,calibration.json,training_meta.json}
  spanguard-taskgate/{gate.pt,vocab.json,config.json,gate_meta.json}
"""
import json
import os
import time
from collections import Counter

import torch
import torch.nn.functional as F
from torch import nn

t_start = time.time()
OUT = "/kaggle/working"


def find(split, *roots):
    deadline = time.time() + 900  # dataset mounts can lag minutes after a version push
    while True:
        for root in roots:
            for dirpath, _dirs, files in os.walk(root):
                if split in files:
                    return os.path.join(dirpath, split)
        if time.time() > deadline:
            listing = os.listdir("/kaggle/input") if os.path.isdir("/kaggle/input") else []
            raise FileNotFoundError(f"{split} not in {roots}; /kaggle/input: {listing}")
        print(f"[wait] {split} not mounted yet, retrying in 60s", flush=True)
        time.sleep(60)


def load(split, *roots):
    docs = [json.loads(l) for l in open(find(split, *roots), encoding="utf-8")]
    print(split, len(docs), flush=True)
    return docs


# ---------------------------------------------------------------- model (embedded)
class Block(nn.Module):
    def __init__(self, ch, k, d):
        super().__init__()
        self.dw = nn.Conv1d(ch, ch, k, dilation=d, padding=d * (k - 1) // 2, groups=ch)
        self.pw = nn.Conv1d(ch, ch, 1)
        self.norm = nn.GroupNorm(8, ch)

    def forward(self, x):
        return x + self.pw(torch.relu(self.norm(self.dw(x))))


class CharGuardNet(nn.Module):
    def __init__(self, vocab_size, cfg):
        super().__init__()
        self.cfg = cfg
        self.emb = nn.Embedding(vocab_size, cfg["emb"], padding_idx=0)
        self.proj = nn.Conv1d(cfg["emb"], cfg["channels"], 1)
        self.blocks = nn.ModuleList(
            [Block(cfg["channels"], cfg["kernel"], d) for d in cfg["dilations"][: cfg["blocks"]]])
        self.span_head = nn.Conv1d(cfg["channels"], 1, 1)
        self.doc_head = nn.Linear(cfg["channels"], 2)

    def forward(self, idx):
        x = self.emb(idx).transpose(1, 2)
        x = self.proj(x)
        for b in self.blocks:
            x = b(x)
        return self.span_head(x).squeeze(1), self.doc_head(x.mean(dim=2))


def build_vocab(texts, cap=600):
    c = Counter(ch for t in texts for ch in t)
    vocab = {"<pad>": 0, "<unk>": 1}
    for ch, _ in c.most_common(cap - 2):
        if not ch.isspace() or ch == " ":
            vocab.setdefault(ch, len(vocab))
    return vocab


def encode(text, vocab, window, max_chars=4096):
    ids = [vocab.get(ch, 1) for ch in text[:max_chars]]
    ids = (ids + [0] * window)[:window]
    return torch.tensor([ids])


# ---------------------------------------------------------------- fm-large
R1, R2 = "/kaggle/input/spanguard-fm-train", "/kaggle/input/spanguard-corpus-v6-addendum"
train_docs = load("train.jsonl", R1, R2) + load("train_add.jsonl", R1, R2)
dev_docs = load("dev.jsonl", R1, R2)[:900]
print("fm-large train total:", len(train_docs), flush=True)

vocab = build_vocab([d["text"] for d in train_docs[:6000]])
cfg = {"channels": 640, "blocks": 8, "kernel": 5,
       "dilations": [1, 2, 4, 8, 16, 32, 64, 128], "emb": 128,
       "max_chars": 4096, "window": 1024, "stride": 896}
net = CharGuardNet(len(vocab), cfg)
n_params = sum(p.numel() for p in net.parameters())
print("fm-large params:", n_params, flush=True)

dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
net.to(dev)
WINDOW, STRIDE = 1024, 896
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
total_steps = EPOCHS * (len(train_docs) // BATCH + 1)
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=total_steps)
rng = torch.Generator().manual_seed(42)

step, t0 = 0, time.time()
for epoch in range(EPOCHS):
    order = torch.randperm(len(train_docs), generator=rng).tolist()
    for bi in range(0, len(order), BATCH):
        batch = [train_docs[i] for i in order[bi: bi + BATCH]]
        idxs, spans_l, doc_l, weights = [], [], [], []
        for d in batch:
            text = d["text"][:4096]
            idxs.append(encode(text, vocab, WINDOW)[0])
            lab = char_labels(d, WINDOW)
            spans_l.append(torch.tensor(lab, dtype=torch.float))
            weights.append(torch.tensor(edge_weights(d, WINDOW)))
            doc_l.append(1 if d.get("spans") else 0)
        idxs = torch.stack(idxs).to(dev)
        span_logits, doc_logits = net(idxs)
        pad_mask = (idxs != 0).float()
        loss_s = (F.binary_cross_entropy_with_logits(
            span_logits, torch.stack(spans_l).to(dev),
            weight=torch.stack(weights).to(dev), reduction="none") * pad_mask
        ).sum() / pad_mask.sum().clamp(min=1)
        loss_d = F.cross_entropy(doc_logits, torch.tensor(doc_l).to(dev))
        loss = loss_s + loss_d
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step(); sched.step(); step += 1
        if step % 100 == 0:
            rate = step * BATCH / ((time.time() - t0) / 60)
            eta = (total_steps - step) * BATCH / max(rate, 1)
            print(f"ep{epoch} step{step}/{total_steps} loss {loss.item():.4f} "
                  f"{rate:.0f} docs/min eta {eta:.0f} min", flush=True)

net.eval()
fm_dir = os.path.join(OUT, "spanguard-fm-large")
os.makedirs(fm_dir, exist_ok=True)
torch.save(net.state_dict(), os.path.join(fm_dir, "char_guard.pt"))
open(os.path.join(fm_dir, "vocab.json"), "w").write(json.dumps(vocab, ensure_ascii=False))
open(os.path.join(fm_dir, "config.json"), "w").write(json.dumps(
    {"net": cfg, "params": n_params, "fm": True, "version": "fm-large-v6",
     "corpus": "corpus-v4 + corpus-v6-addendum"}, indent=1))

sweep = {}
with torch.no_grad():
    for thr in [0.25, 0.3, 0.4, 0.5, 0.6, 0.7]:
        tp = fp = leak = planted = 0
        benign_docs = stripped_benign = 0
        doc_tp = doc_fp = doc_fn = 0
        for d in dev_docs:
            text = d["text"][:4096]
            idxs = encode(text, vocab, WINDOW).to(dev)
            span_logits, doc_logits = net(idxs)
            probs = span_logits.sigmoid()[0].cpu()
            bits = (probs >= thr).int().tolist()[: len(text)]
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
            doc_attack = bool(gold)
            doc_pred = bool(pred) or float(doc_logits.softmax(-1)[0, 1]) >= 0.5
            if doc_attack:
                doc_tp += doc_pred; doc_fn += not doc_pred
            else:
                benign_docs += 1
                if doc_pred:
                    doc_fp += 1
                    stripped_benign += sum(pb - pa for pa, pb in pred)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / max(1, tp + leak)
        doc_p = doc_tp / (doc_tp + doc_fp) if doc_tp + doc_fp else 0.0
        doc_r = doc_tp / (doc_tp + doc_fn) if doc_tp + doc_fn else 0.0
        sweep[str(thr)] = {"span_p": round(p, 4), "span_r": round(r, 4),
                           "escape": round(leak / planted, 4) if planted else 0.0,
                           "overstrip": round(stripped_benign / benign_docs, 4) if benign_docs else 0.0,
                           "doc_f1": round(2 * doc_p * doc_r / (doc_p + doc_r), 4) if doc_p + doc_r else 0.0}
        print(thr, sweep[str(thr)], flush=True)
best_thr = min(sweep, key=lambda t: sweep[t]["escape"] + sweep[t]["overstrip"])
open(os.path.join(fm_dir, "calibration.json"), "w").write(json.dumps(
    {"threshold": float(best_thr), "sweep": sweep, "corpus": "corpus-v4+addendum",
     "boundary_weight": BOUNDARY_W, "fm": True}, indent=1))
meta = {"version": "fm-large-v6", "params": n_params, "cfg": cfg, "train_docs": len(train_docs),
        "epochs": EPOCHS, "batch": BATCH, "best_thr": float(best_thr), "dev_sweep": sweep,
        "runtime_min": round((time.time() - t_start) / 60, 1)}
open(os.path.join(fm_dir, "training_meta.json"), "w").write(json.dumps(meta, indent=1))
print("fm-large done, thr", best_thr, flush=True)

# ---------------------------------------------------------------- task-gate (v6-B)
gate_train = load("taskgate_train.jsonl", R1, R2)
gate_dev = load("taskgate_dev.jsonl", R1, R2)
SEP = "\u27e6TASK\u27e7"


def gate_text(d):
    s, e = d["span"]["start"], d["span"]["end"]
    lo, hi = max(0, s - 120), min(len(d["context"]), e + 120)
    return d["task"][:200] + SEP + d["context"][lo:hi]


gvocab = build_vocab([gate_text(d) for d in gate_train[:6000]], cap=400)
GW = 384


class GateNet(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, 64, padding_idx=0)
        self.proj = nn.Conv1d(64, 256, 1)
        self.blocks = nn.ModuleList([Block(256, 5, d) for d in [1, 2, 4, 8]])
        self.head = nn.Linear(256, 2)

    def forward(self, idx):
        x = self.emb(idx).transpose(1, 2)
        x = self.proj(x)
        for b in self.blocks:
            x = b(x)
        return self.head(x.mean(dim=2))


gnet = GateNet(len(gvocab)).to(dev)
print("gate params:", sum(p.numel() for p in gnet.parameters()), flush=True)
gopt = torch.optim.AdamW(gnet.parameters(), lr=1e-3, weight_decay=0.01)
gacc_hist = []
for epoch in range(3):
    order = torch.randperm(len(gate_train), generator=rng).tolist()
    gnet.train()
    tot, correct, loss_sum, nb = 0, 0, 0.0, 0
    for bi in range(0, len(order), 48):
        batch = [gate_train[i] for i in order[bi: bi + 48]]
        idxs = torch.stack([encode(gate_text(d), gvocab, GW)[0] for d in batch]).to(dev)
        y = torch.tensor([d["label"] for d in batch]).to(dev)
        logits = gnet(idxs)
        loss = F.cross_entropy(logits, y)
        gopt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(gnet.parameters(), 1.0)
        gopt.step()
        loss_sum += loss.item(); nb += 1
        tot += len(batch); correct += (logits.argmax(-1) == y).sum().item()
    gnet.eval()
    with torch.no_grad():
        dtc = dtn = 0
        for bi in range(0, len(gate_dev), 64):
            batch = gate_dev[bi: bi + 64]
            idxs = torch.stack([encode(gate_text(d), gvocab, GW)[0] for d in batch]).to(dev)
            y = torch.tensor([d["label"] for d in batch]).to(dev)
            dtc += (gnet(idxs).argmax(-1) == y).sum().item(); dtn += len(batch)
    gacc_hist.append(round(dtc / dtn, 4))
    print(f"gate ep{epoch} train-acc {correct / tot:.3f} dev-acc {dtc / dtn:.4f}", flush=True)

gate_dir = os.path.join(OUT, "spanguard-taskgate")
os.makedirs(gate_dir, exist_ok=True)
torch.save(gnet.state_dict(), os.path.join(gate_dir, "gate.pt"))
open(os.path.join(gate_dir, "vocab.json"), "w").write(json.dumps(gvocab, ensure_ascii=False))
open(os.path.join(gate_dir, "config.json"), "w").write(json.dumps(
    {"window": GW, "sep": SEP, "version": "taskgate-v6"}, indent=1))
open(os.path.join(gate_dir, "gate_meta.json"), "w").write(json.dumps(
    {"params": sum(p.numel() for p in gnet.parameters()), "dev_acc_by_epoch": gacc_hist,
     "train_pairs": len(gate_train), "dev_pairs": len(gate_dev),
     "labels": {0: "strip (off-task or injection)", 1: "keep (task-relevant)"}}, indent=1))
print("ALL DONE in", round((time.time() - t_start) / 60, 1), "min", flush=True)
