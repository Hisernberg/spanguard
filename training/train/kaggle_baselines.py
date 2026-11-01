"""Kaggle baselines kernel: run open prompt-injection classifiers on the same sets.

Systems (graceful skip on gated/unavailable models):
- protectai/deberta-v3-base-prompt-injection-v2 (open, widely used)
- Horizon-Labs/prompt-injection-guard-small and -base (open)
- meta-llama/Llama-Prompt-Guard-2-22M - gated on HF; attempted last and recorded
  as unavailable unless the runtime has an accepted-license token (HF_TOKEN env).

Binary classifiers use "strip-all" semantics: flagged docs lose 100% of their
characters (the agent gets nothing), clean docs pass through untouched. Outputs
baselines.json in run-record schema with doc P/R/F1, escape/overstrip and CPU
latency per doc, per fixture set.
"""

import json
import os
import statistics
import time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

DATA = "/kaggle/input/spanguard-corpus"
OUT = "/kaggle/working/baselines.json"
torch.set_num_threads(4)

CANDIDATES = [
    ("protectai/deberta-v3-base-prompt-injection-v2", "protectai-deberta-v2"),
    ("Horizon-Labs/prompt-injection-guard-small", "horizon-small"),
    ("Horizon-Labs/prompt-injection-guard-base", "horizon-base"),
    ("meta-llama/Llama-Prompt-Guard-2-22M", "prompt-guard-2-22m"),
]

_ATTACK_RX = ("attack", "injection", "unsafe", "malicious", "jailbreak")


def attack_index(id2label) -> int:
    """Find the class index whose label means attack."""
    labels = [str(v).lower() for v in id2label.values()]
    for i, lab in enumerate(labels):
        if any(rx in lab for rx in _ATTACK_RX):
            return i
    return len(labels) - 1  # fallback: last class (most common convention)


def wait_for_dataset(deadline_s: int = 420) -> dict:
    """Walk the dataset mount by basename, waiting out version reprocessing."""
    wanted = {
        "test.jsonl": "agent-traffic",
        "handwritten-en.jsonl": "handwritten",
        "handwritten-de.jsonl": "handwritten",
        "handwritten-hu.jsonl": "handwritten",
        "public-deepset.jsonl": "public-deepset",
    }
    deadline = time.time() + deadline_s
    while True:
        found = {}
        if os.path.isdir(DATA):
            for root, _dirs, files in os.walk(DATA):
                for f in files:
                    if f in wanted:
                        found.setdefault(wanted[f], []).append(os.path.join(root, f))
        if found or time.time() > deadline:
            return found
        print("[wait] dataset mount empty, retrying in 60s")
        time.sleep(60)


def load_sets():
    found = wait_for_dataset()
    sets = {}
    for name, paths in found.items():
        docs = []
        for p in sorted(set(paths)):
            docs += [json.loads(l) for l in open(p, encoding="utf-8")]
        sets[name] = docs
    print({k: len(v) for k, v in sets.items()})
    return sets


def attack_prob(model, tok, text, device, idx: int):
    enc = tok(text[:2000], truncation=True, max_length=512, return_tensors="pt").to(device)
    with torch.no_grad():
        logits = model(**enc).logits
    probs = logits.softmax(-1)[0]
    return float(probs[idx])


def run_system(model_id, tag, sets, device):
    """Score one baseline model per fixture set (run-record schema)."""
    try:
        tok = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForSequenceClassification.from_pretrained(model_id).to(device).eval()
    except Exception as exc:  # noqa: BLE001 - record and skip
        return {"model": model_id, "tag": tag, "available": False, "error": str(exc)[:300]}

    out_sets = {}
    lat_all = []
    idx = attack_index(model.config.id2label)
    print(f"[{tag}] attack class index: {idx} of {len(model.config.id2label)} ({model.config.id2label})")
    for set_name, docs in sets.items():
        lat = []
        flags = []
        for d in docs:
            t0 = time.monotonic()
            p = attack_prob(model, tok, d["text"], device, idx)
            lat.append((time.monotonic() - t0) * 1000)
            flags.append(p >= 0.5)
        lat_all += lat

        planted = leak = 0
        benign_chars = stripped_benign = 0
        tp = fp = fn = 0
        per_family = {}
        per_lang = {}
        for d, flagged in zip(docs, flags):
            gold = d.get("spans", [])
            lang = d.get("lang", "en")
            fam = d.get("attack") or "?"
            is_attack_doc = bool(gold) or d.get("binary_attack", False)
            per_lang.setdefault(lang, {"n": 0, "planted": 0, "leak": 0})["n"] += 1
            if gold:
                per_family.setdefault(fam, {"planted": 0, "leak": 0})
                for s in gold:
                    planted += 1
                    per_family[fam]["planted"] += 1
                    per_lang[lang]["planted"] += 1
                    if not flagged:  # passed through untouched -> payload survives
                        leak += 1
                        per_family[fam]["leak"] += 1
                        per_lang[lang]["leak"] += 1
            if is_attack_doc:
                tp += flagged
                fn += not flagged
            else:
                if flagged:
                    fp += 1
                    stripped_benign += len(d["text"])
                benign_chars += len(d["text"])

        def prf(tp, fp, fn):
            p = tp / (tp + fp) if tp + fp else 0.0
            r = tp / (tp + fn) if tp + fn else 0.0
            f = 2 * p * r / (p + r) if p + r else 0.0
            return round(p, 4), round(r, 4), round(f, 4)

        dp, dr, df = prf(tp, fp, fn)
        lat_sorted = sorted(lat)
        out_sets[set_name] = {
            "docs": len(docs), "planted": planted,
            "escape_rate": round(leak / planted, 4) if planted else 0.0,
            "overstrip_rate": round(stripped_benign / benign_chars, 4) if benign_chars else 0.0,
            "doc_precision": dp, "doc_recall": dr, "doc_f1": df,
            "latency_ms_p50": round(statistics.median(lat), 1),
            "latency_ms_p95": round(lat_sorted[int(0.95 * len(lat_sorted))], 1),
            "per_family": {k: {"escape_rate": round(v["leak"] / v["planted"], 4) if v["planted"] else 0.0,
                               "planted": v["planted"]} for k, v in sorted(per_family.items())},
            "per_language": {k: {"escape_rate": round(v["leak"] / v["planted"], 4) if v["planted"] else 0.0,
                                 "docs": v["n"]} for k, v in sorted(per_lang.items())},
        }
    return {
        "model": model_id, "tag": tag, "available": True, "sets": out_sets,
        "latency_ms_p50": round(statistics.median(lat_all), 1) if lat_all else None,
        "device": str(device), "threads": torch.get_num_threads(),
    }


def main():
    import datetime as dt

    sets = load_sets()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    results = [run_system(mid, tag, sets, device) for mid, tag in CANDIDATES]
    # run-record schema: {"systems": {tag: {"sets": {...}}}} - consumed by the repo's
    # report generator unchanged.
    systems = {}
    for r in results:
        if r.get("available"):
            systems[r["tag"]] = {"sets": r["sets"], "latency_ms_p50": r["latency_ms_p50"],
                                 "model": r["model"], "device": r["device"]}
        else:
            systems[r["tag"]] = {"available": False, "error": r.get("error", "")}
    json.dump({"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "environment": {"platform": "kaggle", "device": str(device),
                               "threads": torch.get_num_threads(), "torch": torch.__version__},
               "systems": systems},
              open(OUT, "w"), indent=2)
    brief = {t: {s: m["escape_rate"] for s, m in v["sets"].items()} if v.get("sets") else "unavailable"
             for t, v in systems.items()}
    print(json.dumps(brief, indent=1))


if __name__ == "__main__":
    main()
