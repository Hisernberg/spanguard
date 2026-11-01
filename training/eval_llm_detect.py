"""Precompute the LLM self-detection baseline: Muse Spark Open inspects every
fixture document and reports attack spans; verdicts land in a sidecar JSON that
the eval harness reads (so scoring is instant and reproducible offline).

Also records per-call latency and the exact token cost at Baseten list prices.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from label_teacher import label_doc, load_key, match_span  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SETS = {
    "handwritten": [REPO / "eval/fixtures/handwritten-en.jsonl", REPO / "eval/fixtures/handwritten-de.jsonl", REPO / "eval/fixtures/handwritten-hu.jsonl"],
    "agent-traffic": [REPO / "eval/fixtures/agent-traffic.jsonl"],
    "public-deepset": [REPO / "eval/fixtures/public-deepset.jsonl"],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="eval/results/llm-self-detect/verdicts.json")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--agent-limit", type=int, default=900)
    ap.add_argument("--public-limit", type=int, default=250)
    args = ap.parse_args()

    api_key = load_key()
    docs = []
    for name, files in SETS.items():
        for p in files:
            if not p.exists():
                continue
            for line in open(p, encoding="utf-8"):
                d = json.loads(line)
                d["_set"] = name
                docs.append(d)
    docs = [d for d in docs if not (d["_set"] == "agent-traffic" and False)]
    agent = [d for d in docs if d["_set"] == "agent-traffic"][: args.agent_limit]
    pub = [d for d in docs if d["_set"] == "public-deepset"][: args.public_limit]
    docs = [d for d in docs if d["_set"] == "handwritten"] + agent + pub
    print("docs:", len(docs))

    client = httpx.Client()
    verdicts: dict[str, list] = {}
    latencies: list[float] = []
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0, "errors": 0}

    def work(d):
        attacks, u = label_doc(client, api_key, d["text"])
        return d, attacks, u

    done = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        for d, attacks, u in ex.map(work, docs):
            spans = []
            for a in attacks:
                m = match_span(d["text"], a["quote"])
                if m:
                    spans.append({"start": m[0], "end": m[1], "family": a.get("family", "override")})
            verdicts[d["id"]] = spans
            latencies.append(u["latency_s"] * 1000)
            usage["prompt_tokens"] += u["prompt_tokens"]
            usage["completion_tokens"] += u["completion_tokens"]
            usage["calls"] += 1
            usage["errors"] += 0 if u["ok"] else 1
            done += 1
            if done % 50 == 0:
                print(done, "/", len(docs), flush=True)

    cost = (usage["prompt_tokens"] * 1.25 + usage["completion_tokens"] * 4.25) / 1e6
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "model": "meta-models/muse-spark-open-1026",
        "price_usd_per_1m": {"input": 1.25, "output": 4.25},
        "usage": usage, "cost_usd": round(cost, 4),
        "latency_ms_p50": round(statistics.median(latencies), 1) if latencies else None,
        "latency_ms_p95": round(sorted(latencies)[int(0.95 * len(latencies))], 1) if latencies else None,
        "docs": len(docs),
        "verdicts": verdicts,
    }, indent=1), encoding="utf-8")
    print("wrote", out, "| cost $", round(cost, 4), "| p50", out and statistics.median(latencies))


if __name__ == "__main__":
    main()
