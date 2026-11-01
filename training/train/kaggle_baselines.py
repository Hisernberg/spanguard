"""Kaggle baselines kernel: run open prompt-injection classifiers on the same sets.

Systems (graceful skip on gated/unavailable models):
- meta-llama/Llama-Prompt-Guard-2-22M and -90M (Meta's own CPU classifiers)
- protectai/deberta-v3-base-prompt-injection-v2

Binary classifiers use "strip-all" semantics: flagged docs lose 100% of their
characters (the agent gets nothing), clean docs pass through untouched. Outputs
baselines.json with doc P/R/F1, escape/overstrip and CPU latency per doc.
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
    ("meta-llama/Llama-Prompt-Guard-2-22M", "prompt-guard-2-22m"),
    ("meta-llama/Llama-Prompt-Guard-2-90M", "prompt-guard-2-90m"),
    ("protectai/deberta-v3-base-prompt-injection-v2", "protectai-deberta-v2"),
]


def load_sets():
    """Per-fixture-set doc lists, matching the repo's eval sets."""
    mapping = {
        "agent-traffic": ["test.jsonl"],
        "handwritten": ["handwritten-en.jsonl", "handwritten-de.jsonl", "handwritten-hu.jsonl"],
        "public-deepset": ["public-deepset.jsonl"],
    }
    sets = {}
    for name, files in mapping.items():
        docs = []
        for fname in files:
            for base in [DATA, os.path.join(DATA, "corpus"), os.path.join(DATA, "fixtures")]:
                p = os.path.join(base, fname)
                if os.path.exists(p):
                    docs += [json.loads(l) for l in open(p, encoding="utf-8")]
                    break
        if docs:
            sets[name] = docs
    print({k: len(v) for k, v in sets.items()})
    return sets


def attack_prob(model, tok, text, device):
    enc = tok(text[:2000], truncation=True, max_length=512, return_tensors="pt").to(device)
    with torch.no_grad():
        logits = model(**enc).logits
    probs = logits.softmax(-1)[0]
    return float(probs[-1])  # last id = attack class for these models


def run_system(model_id, tag, sets, device):
    """Score one baseline model per fixture set (run-record schema)."""
    try:
        tok = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForSequenceClassification.from_pretrained(model_id).to(device).eval()
    except Exception as exc:  # noqa: BLE001 - record and skip
        return {"model": model_id, "tag": tag, "available": False, "error": str(exc)[:200]}

    out_sets = {}
    lat_all = []
    for set_name, docs in sets.items():
        lat = []
        flags = []
        for d in docs:
            t0 = time.monotonic()
            p = attack_prob(model, tok, d["text"], device)
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
    sets = load_sets()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    import datetime as dt

    results = [run_system(mid, tag, sets, device) for mid, tag in CANDIDATES]
    # run-record schema: {"systems": {tag: {"sets": {...}}}} — consumed by the repo's
    # report generator unchanged. Copy each available system's per-set block verbatim.
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
    print(json.dumps(systems, indent=1)[:2000])


if __name__ == "__main__":
    main()
