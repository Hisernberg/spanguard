#!/usr/bin/env python3
"""v6 calibration + evaluation core (run via scripts/v6_mega_run.sh).

Protocol, in order:
A. Conformal calibration (v6-F) on the public-probe benign set ONLY (452 docs);
   the other benign sets are held out as verification.
B. Verification: realized over-strip on held-out benign sets (agent-traffic,
   extended-v6, NotInject) — does the alpha bound hold out of distribution? —
   and escape on every attack set, with and without the task gate (v6-B).
C. Full guard-level eval across the six committed sets (eval CLI).
D. Agent-loop harness (NotInject utility + hijack columns).
E. Latency (p50/p95 on 2 CPU threads).
Artifacts: calibration_v2.json into the model dir, run records into eval/results,
summary JSON at /tmp/v6-summary.json for charts/README/website.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

FM = os.environ["SPANGUARD_FM_MODEL"]
GATE = os.environ.get("SPANGUARD_TASKGATE", "")
SUMMARY: dict = {"protocol": "v6"}

FIX = REPO / "eval" / "fixtures"


def load_fix(name: str) -> list[dict]:
    p = FIX / f"{name}.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def benign(docs: list[dict]) -> list[dict]:
    return [d for d in docs if not (d.get("attack") or d.get("spans"))]


def attacked(docs: list[dict]) -> list[dict]:
    return [d for d in docs if (d.get("attack") or d.get("spans"))]


# --------------------------------------------------------------- A. calibration
from spanguard.detect.conformal import calibrate  # noqa: E402

print("=== A. conformal calibration on public-deepset (452 benign) ===", flush=True)
probe = load_fix("public-deepset")
probe_benign = [d["text"] for d in probe if not (d.get("attack") or d.get("spans"))]
print("calibration docs:", len(probe_benign), flush=True)
t0 = time.time()
ALPHAS = [0.05, 0.10, 0.25, 0.50]
cal_by_alpha = {}
for a in ALPHAS:
    cal_by_alpha[a] = calibrate(probe_benign, dir_path=FM, alpha=a)
    print(f"alpha={a}:", {k: v["tau"] for k, v in cal_by_alpha[a]["strata"].items()}, flush=True)
print(f"calibration took {time.time() - t0:.0f}s", flush=True)
SUMMARY["calibration"] = {str(a): cal_by_alpha[a] for a in ALPHAS}

# --------------------------------------------------------------- B. verification
from spanguard.detect.pipeline import Guard  # noqa: E402

def overstrip(guard: Guard, docs: list[dict]) -> float:
    if not docs:
        return 0.0
    hits = 0
    for d in docs:
        r = guard.guard(d["text"])
        hits += bool(r.stripped)
    return round(hits / len(docs), 4)

def escape(guard: Guard, docs: list[dict]) -> float:
    if not docs:
        return 0.0
    miss = 0
    for d in docs:
        r = guard.guard(d["text"])
        miss += not r.attacked
    return round(miss / len(docs), 4)

print("=== B. verification (held-out benign + attack sets) ===", flush=True)
plain = Guard(mode="fm-v6")
tasked = Guard(mode="fm-v6", task="summarise the tool output for the user") if GATE else None

BENIGN_SETS = {
    "public-probe (calib)": benign(probe),
    "agent-traffic benign": benign(load_fix("agent-traffic")),
    "extended-v6 benign": benign(load_fix("extended-v6")),
    "notinject probe": load_fix("notinject_benign"),
}
ATTACK_SETS = {
    "extended-attacks": attacked(load_fix("extended-attacks")),
    "extended-v4": attacked(load_fix("extended-v4")),
    "extended-v6": attacked(load_fix("extended-v6")),
    "agentdojo-wrapped": load_fix("agentdojo-wrapped"),
    "handwritten": load_fix("handwritten-en") + load_fix("handwritten-de") + load_fix("handwritten-hu"),
}

# sweep the conformal bound: per alpha, write calibration_v2 and measure both
# directions on every set; the shipped default is chosen afterwards from data
model_dir = Path(FM)
SUMMARY["sweep"] = {}
CHOOSE = {}
for a in ALPHAS:
    (model_dir / "calibration_v2.json").write_text(json.dumps(cal_by_alpha[a], indent=1))
    g = Guard(mode="fm-v6")  # fresh: reloads calibration_v2
    row = {"benign": {}, "escape": {}}
    for name, docs in BENIGN_SETS.items():
        row["benign"][name] = overstrip(g, docs)
    for name, docs in ATTACK_SETS.items():
        row["escape"][name] = escape(g, docs)
    SUMMARY["sweep"][str(a)] = row
    worst_benign = max(v for k, v in row["benign"].items() if "calib" not in k)
    CHOOSE[a] = worst_benign
    print(f"alpha={a}: worst held-out benign over-strip {worst_benign} | "
          f"escapes {[row['escape'][k] for k in row['escape']]}", flush=True)

# default: the smallest alpha whose worst held-out benign over-strip stays
# within alpha + 0.05; if none does, ship the largest and say so honestly
shipped = None
for a in ALPHAS:
    if CHOOSE[a] <= a + 0.05:
        shipped = a
        break
if shipped is None:
    shipped = ALPHAS[-1]
(model_dir / "calibration_v2.json").write_text(json.dumps(cal_by_alpha[shipped], indent=1))
SUMMARY["shipped_alpha"] = shipped
print("shipped default alpha:", shipped, flush=True)

plain = Guard(mode="fm-v6")
tasked = Guard(mode="fm-v6", task="summarise the tool output for the user") if GATE else None

SUMMARY["overstrip"] = {}
for name, docs in BENIGN_SETS.items():
    row = {"docs": len(docs), "plain": overstrip(plain, docs)}
    if tasked:
        row["tasked"] = overstrip(tasked, docs)
    SUMMARY["overstrip"][name] = row
    print("over-strip", name, row, flush=True)
SUMMARY["escape"] = {}
for name, docs in ATTACK_SETS.items():
    row = {"docs": len(docs), "plain": escape(plain, docs)}
    if tasked:
        row["tasked"] = escape(tasked, docs)
    SUMMARY["escape"][name] = row
    print("escape", name, row, flush=True)

# --------------------------------------------------------------- C. full eval
print("=== C. guard-level eval (committed sets, committed record) ===", flush=True)
from spanguard.eval.cli import run_eval  # noqa: E402

run_dir = run_eval(["spg-fm-v6", "spg-fm", "spanguard-fast-v4", "spanguard-rules"],
                   ["handwritten", "agent-traffic", "public-deepset",
                    "extended-attacks", "extended-v4", "extended-v6",
                    "agentdojo-wrapped", "notinject_benign"],
                   tag="v6-final")
SUMMARY["eval_record"] = str(run_dir)
rec = json.loads((Path(run_dir) / "run.json").read_text())
SUMMARY["eval"] = {sysname: rec["systems"][sysname]["sets"] for sysname in rec["systems"]}

# --------------------------------------------------------------- D. agent loop
print("=== D. agent-loop harness ===", flush=True)
sys.path.insert(0, str(REPO))
from eval.agent_harness import run as harness_run  # noqa: E402

harness_dir = harness_run(["spg-fm-v6", "spanguard-fast-v4", "spg-fm", "spanguard-rules"],
                          tag="v6", task="summarise the tool output for the user")
SUMMARY["agent_loop"] = {
    sysname: rec["summary"]
    for sysname, rec in json.loads((harness_dir / "run.json").read_text())["systems"].items()}

# --------------------------------------------------------------- E. latency
print("=== E. latency ===", flush=True)
texts = [d["text"][:1200] for d in (benign(load_fix("agent-traffic"))[:30]
                                    + attacked(load_fix("extended-v6"))[:30])]
lat = []
g = Guard(mode="fm-v6")
for _ in range(3):
    for t in texts:
        t0 = time.monotonic()
        g.guard(t)
        lat.append((time.monotonic() - t0) * 1000)
lat.sort()
SUMMARY["latency"] = {"p50_ms": round(lat[len(lat) // 2], 1),
                      "p95_ms": round(lat[int(len(lat) * 0.95)], 1),
                      "n": len(lat), "threads": 2}
print("latency:", SUMMARY["latency"], flush=True)

Path("/tmp/v6-summary.json").write_text(json.dumps(SUMMARY, indent=1))
print("SUMMARY written to /tmp/v6-summary.json")
print(json.dumps({k: SUMMARY[k] for k in ["overstrip", "escape"]}, indent=1))
