#!/usr/bin/env python3
"""SPG-FM v5: the SpanGuard domain foundational model.

One model, one pass, no router: a single char-level multi-task network trained
on the FULL corpus-v4 (all 7 languages x 18 carrier families x 16k docs) that
outputs BOTH the document-level attack probability and the char-level payload
spans. v2/v3/v4 shipped one small expert per domain plus a regex router; SPG-FM
replaces the whole stack — it is trained on the union of every domain the
router used to dispatch, so in-domain coverage no longer depends on the router
being right.

Capacity bump vs char-v4: channels 384->512, blocks 5->6, emb 64->96
(~1.7M params — still ~2-4 ms/doc on CPU, still under 8 MB on disk).

Resumable: saves a checkpoint every 500 steps (model + optimizer + step) and
restarts from the newest one when re-run — a sandbox recycle costs minutes,
not the full run. Checkpoints are also mirrored to download/ as insurance.

Outputs the same artifacts as train_char.py (char_guard.pt, vocab.json,
config.json, calibration.json) so the runtime can load it unchanged.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from spanguard.detect.char_model import CharGuardNet, build_vocab, encode  # noqa: E402

REPO = Path(__file__).parent.parent
BOUNDARY_W = 3.0
EDGE = 3
CHECKPOINT_EVERY = 500
MIRROR = Path("/home/z/my-project/download/spanguard-fm-checkpoints")


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
    out = []
    for a, b in spans:
        if b - a < 2:
            continue
        out.append((max(0, a - 1), min(len(text), b + 1)))
    return out


def save_checkpoint(net, opt, sched, step, out_dir, vocab) -> None:
    ck = {"step": step, "model": net.state_dict(), "opt": opt.state_dict(),
          "sched": sched.state_dict()}
    torch.save(ck, out_dir / "checkpoint.pt")
    try:
        MIRROR.mkdir(parents=True, exist_ok=True)
        torch.save(ck, MIRROR / "checkpoint.pt")
        (MIRROR / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False))
    except OSError:
        pass
    print(f"[ckpt] step {step} saved", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-limit", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--out", default="data/models/spanguard-fm-1")
    ap.add_argument("--corpus", default="data/corpus-v4")
    args = ap.parse_args()

    docs = [json.loads(l) for l in open(f"{args.corpus}/train.jsonl", encoding="utf-8")]
    if args.train_limit:
        docs = docs[: args.train_limit]
    dev_all = [json.loads(l) for l in open(f"{args.corpus}/dev.jsonl", encoding="utf-8")]
    dev = dev_all[:800]
    print(f"train {len(docs)} dev {len(dev)}", flush=True)

    vocab = build_vocab([d["text"] for d in docs[:4000]])
    print("vocab:", len(vocab), flush=True)
    cfg = {"channels": 512, "blocks": 6, "kernel": 5,
           "dilations": [1, 2, 4, 8, 16, 32], "emb": 96,
           "max_chars": 4096, "window": 1024, "stride": 896}
    net = CharGuardNet(len(vocab), cfg=cfg)
    n_params = sum(p.numel() for p in net.parameters())
    print("params:", n_params, flush=True)
    opt = torch.optim.AdamW(net.parameters(), lr=8e-4, weight_decay=0.01)
    total_steps = args.epochs * (len(docs) // args.batch + 1)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=total_steps)
    torch.set_num_threads(4)

    out_dir = REPO / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False))

    window, stride = 1024, 896
    start_step = 0
    ck_path = out_dir / "checkpoint.pt"
    if ck_path.exists():
        ck = torch.load(ck_path, map_location="cpu", weights_only=False)
        net.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        sched.load_state_dict(ck["sched"])
        start_step = ck["step"]
        print(f"resumed from checkpoint at step {start_step}", flush=True)

    t0 = time.time()
    step = 0
    for epoch in range(args.epochs):
        order = torch.randperm(len(docs)).tolist()
        for bi in range(0, len(order), args.batch):
            if step < start_step:
                step += 1
                sched.step()
                continue
            batch = [docs[i] for i in order[bi: bi + args.batch]]
            idxs, spans_l, doc_l, weights = [], [], [], []
            for d in batch:
                text = d["text"][:4096]
                idxs.append(encode(text, vocab, window, stride)[0])
                lab = char_labels(d)
                lab = (lab + [0] * (window - len(lab)))[:window]
                spans_l.append(torch.tensor(lab, dtype=torch.float))
                weights.append(edge_weights(d, window))
                doc_l.append(1 if d.get("spans") else 0)
            idxs = torch.stack(idxs)
            span_logits, doc_logits = net(idxs)
            pad_mask = (idxs != 0).float()
            loss_s = (F.binary_cross_entropy_with_logits(
                span_logits, torch.stack(spans_l), weight=torch.stack(weights), reduction="none")
                * pad_mask).sum() / pad_mask.sum().clamp(min=1)
            loss_d = F.cross_entropy(doc_logits, torch.tensor(doc_l))
            loss = loss_s + loss_d
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            sched.step()
            step += 1
            if step % 100 == 0:
                done = step - start_step
                rate = done * args.batch / ((time.time() - t0) / 60)
                eta = (total_steps - step) * args.batch / max(rate, 1)
                print(f"ep{epoch} step{step}/{total_steps} loss {loss.item():.4f} "
                      f"(span {loss_s.item():.4f} doc {loss_d.item():.4f}) "
                      f"{rate:.0f} docs/min eta {eta:.0f} min", flush=True)
            if step % CHECKPOINT_EVERY == 0:
                save_checkpoint(net, opt, sched, step, out_dir, vocab)

    torch.save(net.state_dict(), out_dir / "char_guard.pt")
    (out_dir / "config.json").write_text(json.dumps({"net": cfg, "params": n_params, "fm": True,
                                                     "replaces": ["spanguard-char", "spanguard-char-v3",
                                                                  "spanguard-char-v4", "router"]}, indent=1))

    net.eval()
    sweep = {}
    with torch.no_grad():
        for thr in [0.25, 0.3, 0.4, 0.5, 0.6, 0.7]:
            tp = fp = leak = planted = 0
            benign_docs = stripped_benign = 0
            doc_tp = doc_fp = doc_fn = 0
            for d in dev:
                text = d["text"][:4096]
                idxs = encode(text, vocab, window, stride)
                span_logits, doc_logits = net(idxs)
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
                doc_pred = bool(pred) or float(doc_logits.softmax(-1)[0, 1]) >= 0.5
                if doc_attack:
                    doc_tp += doc_pred
                    doc_fn += not doc_pred
                else:
                    benign_docs += 1
                    if doc_pred:
                        doc_fp += 1
                        stripped_benign += sum(pb - pa for pa, pb in pred)
            p = tp / (tp + fp) if tp + fp else 0.0
            r = tp / max(1, tp + leak)
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
    (out_dir / "calibration.json").write_text(json.dumps(
        {"threshold": best_thr, "sweep": sweep, "corpus": args.corpus,
         "boundary_weight": BOUNDARY_W, "fm": True}, indent=1))
    (ck_path).unlink(missing_ok=True)
    print("saved", out_dir, "threshold", best_thr)


if __name__ == "__main__":
    main()
