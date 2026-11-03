#!/usr/bin/env python3
"""Train the char-level multi-task guard on the v2 corpus (CPU, ~1.3M params).
Boundary-weighted BCE: chars near a span edge get 3x weight — span boundaries are
what surgical stripping needs. Dev-set threshold sweep produces calibration.json.
Usage: python3 training/train_char.py [--train-limit N] [--epochs E]"""
import argparse
import json
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from spanguard.detect.char_model import CharGuardNet, build_vocab, encode

REPO = Path(__file__).parent.parent
BOUNDARY_W = 3.0
EDGE = 3  # chars around a span boundary count as "edge"


def char_labels(doc: dict) -> list[int]:
    lab = [0] * min(len(doc["text"]), 4096)
    for s in doc.get("spans", []):
        for i in range(max(0, s["start"]), min(len(lab), s["end"])):
            lab[i] = 1
    return lab


def edge_weights(doc: dict, n: int) -> torch.Tensor:
    w = torch.ones(n)
    for s in doc.get("spans", []):
        for i in list(range(max(0, s["start"] - EDGE), s["start"] + EDGE)) + \
                 list(range(s["end"] - EDGE, min(n, s["end"] + EDGE))):
            if 0 <= i < n:
                w[i] = BOUNDARY_W
    return w


def merge_spans(bits: list[int], text: str) -> list[tuple[int, int]]:
    spans, start = [], None
    for i, b in enumerate(bits):
        if b and start is None:
            start = i
        elif not b and start is not None:
            spans.append((start, i))
            start = None
    if start is not None:
        spans.append((start, len(bits)))
    # drop 1-2 char blips, expand by one char each side (tokenizer-free slack)
    out = []
    for a, b in spans:
        if b - a < 2:
            continue
        out.append((max(0, a - 1), min(len(text), b + 1)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-limit", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=12)
    ap.add_argument("--out", default="data/models/spanguard-char")
    args = ap.parse_args()

    docs = [json.loads(l) for l in open("data/corpus-v2/train.jsonl", encoding="utf-8")]
    if args.train_limit:
        docs = docs[: args.train_limit]
    dev_all = [json.loads(l) for l in open("data/corpus-v2/dev.jsonl", encoding="utf-8")]
    dev = dev_all[:600]  # sweep subset; full dev stays for the transformer v2
    print(f"train {len(docs)} dev {len(dev)}", flush=True)

    vocab = build_vocab([d["text"] for d in docs[:3000]])
    print("vocab:", len(vocab), flush=True)
    net = CharGuardNet(len(vocab))
    print("params:", sum(p.numel() for p in net.parameters()), flush=True)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=0.01)
    torch.set_num_threads(2)

    window, stride = 1024, 896
    t0 = time.time()
    step = 0
    for epoch in range(args.epochs):
        order = torch.randperm(len(docs)).tolist()
        for bi in range(0, len(order), args.batch):
            batch = [docs[i] for i in order[bi: bi + args.batch]]
            idxs, spans_l, doc_l, weights = [], [], [], []
            for d in batch:
                text = d["text"][:4096]
                idxs.append(encode(text, vocab, window, stride)[0])
                lab = char_labels(d)
                lab = (lab + [0] * (window - len(lab)))[:window]
                spans_l.append(torch.tensor(lab, dtype=torch.float))
                w = edge_weights(d, window)
                weights.append(w)
                doc_l.append(1 if d.get("spans") else 0)
            idxs = torch.stack(idxs)
            span_logits, doc_logits = net(idxs)
            loss_s = (F.binary_cross_entropy_with_logits(
                span_logits, torch.stack(spans_l), weight=torch.stack(weights), reduction="none"))
            # masked mean: ignore padding chars
            pad_mask = (idxs != 0).float()
            loss_s = (loss_s * pad_mask).sum() / pad_mask.sum().clamp(min=1)
            loss_d = F.cross_entropy(doc_logits, torch.tensor(doc_l))
            loss = loss_s + loss_d
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            step += 1
            if step % 100 == 0:
                rate = step * args.batch / ((time.time() - t0) / 60)
                print(f"ep{epoch} step{step} loss {loss.item():.4f} "
                      f"(span {loss_s.item():.4f} doc {loss_d.item():.4f}) "
                      f"{rate:.0f} docs/min", flush=True)

    out = REPO / args.out
    out.mkdir(parents=True, exist_ok=True)
    torch.save(net.state_dict(), out / "char_guard.pt")
    (out / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False))
    (out / "config.json").write_text(json.dumps({"net": net.cfg}, indent=1))

    # ---- dev threshold sweep (calibration) ------------------------------------
    net.eval()
    sweep = {}
    with torch.no_grad():
        for thr in [0.3, 0.4, 0.5, 0.6, 0.7]:
            tp = fp = leak = planted = 0
            benign_docs = stripped_benign = 0
            doc_tp = doc_fp = doc_fn = 0
            for d in dev:
                text = d["text"][:4096]
                idxs = encode(text, vocab, window, stride)
                span_logits, _ = net(idxs)
                probs = span_logits.sigmoid()
                bits = []
                for w_i in range(probs.shape[0]):
                    bits.extend((probs[w_i] >= thr).int().tolist())
                bits = bits[: len(text)]
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
                doc_pred = bool(pred)
                if doc_attack:
                    doc_tp += doc_pred
                    doc_fn += not doc_pred
                else:
                    benign_docs += len(text)
                    if doc_pred:
                        doc_fp += 1
                        stripped_benign += sum(pb - pa for pa, pb in pred)
            p = tp / (tp + fp) if tp + fp else 0.0
            r = tp / max(1, tp + leak)  # recall approx via missed gold spans
            doc_p = doc_tp / (doc_tp + doc_fp) if doc_tp + doc_fp else 0.0
            doc_r = doc_tp / (doc_tp + doc_fn) if doc_tp + doc_fn else 0.0
            sweep[thr] = {
                "span_p": round(p, 4), "span_r": round(r, 4),
                "escape": round(leak / planted, 4) if planted else 0.0,
                "overstrip": round(stripped_benign / benign_docs, 4) if benign_docs else 0.0,
                "doc_f1": round(2 * doc_p * doc_r / (doc_p + doc_r), 4) if doc_p + doc_r else 0.0,
            }
    print(json.dumps(sweep, indent=1))
    best_thr = min(sweep, key=lambda t: sweep[t]["escape"] + sweep[t]["overstrip"])
    (out / "calibration.json").write_text(json.dumps(
        {"threshold": best_thr, "sweep": sweep, "corpus": "corpus-v2", "boundary_weight": BOUNDARY_W},
        indent=1))
    print("saved", out, "threshold", best_thr)


if __name__ == "__main__":
    main()
