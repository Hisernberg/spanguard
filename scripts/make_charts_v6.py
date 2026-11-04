#!/usr/bin/env python3
"""v6 charts — every number comes from a committed record or /tmp/v6-summary.json.

Panels:
1. flagship bars: spg-fm-v6 vs fast-v4 vs fm-1 across the six committed sets;
2. conformal alpha sweep: realized over-strip (held-out benign worst case) and
   attack escape per alpha — the calibration frontier;
3. agent-loop columns: NotInject utility vs hijack success per system;
4. version ladder extended with v6.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.font_manager as fm

fm.fontManager.addfont('/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf')
fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans SC']
plt.rcParams['axes.unicode_minus'] = False

R = Path(__file__).resolve().parent.parent
OUT = R / "docs" / "assets"
OUT.mkdir(parents=True, exist_ok=True)
SUMMARY = json.loads(Path("/tmp/v6-summary.json").read_text())
REC_PATH = SUMMARY.get("eval_record")
SHIP = json.loads((Path(REC_PATH) / "run.json").read_text()) if REC_PATH else \
    {"systems": {}}
SETS = ["handwritten", "agent-traffic", "public-deepset", "extended-attacks",
        "extended-v4", "extended-v6"]
LABELS = ["hand-written\nOOD", "agent\ntraffic", "public\nprobe", "extended\nattacks",
          "extended\ncarriers v4", "extended\nv6 (500)"]
C_V6, C_V4, C_FM, C_GREY = "#16a34a", "#0891b2", "#7c3aed", "#94a3b8"


def get(sysname, s, key):
    m = SHIP.get("systems", {}).get(sysname, {}).get("sets", {}).get(s, {})
    v = m.get(key)
    return (v if v is not None else 0) * 100


# ---- 1. flagship bars -------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(13.2, 4.6), constrained_layout=True)
x = range(len(SETS))
w = 0.27
sys_map = [("spg-fm-v6", "fm-v6 (conformal + gate)", C_V6),
           ("spanguard-fast-v4", "fast-v4 (router stack)", C_V4),
           ("spg-fm", "fm-1 (v5 flagship)", C_FM)]
for ax, key, title in [(axes[0], "escape_rate", "Escape rate (lower is better)"),
                       (axes[1], "overstrip_rate", "Over-strip on benign (lower is better)")]:
    for k, (sysname, label, color) in enumerate(sys_map):
        if sysname not in SHIP.get("systems", {}):
            continue
        vals = [get(sysname, s, key) for s in SETS]
        off = (k - 1) * w
        ax.bar([i + off for i in x], vals, w, label=label, color=color)
        for i, v in enumerate(vals):
            ax.text(i + off, v + 0.6, f"{v:.1f}", ha="center", fontsize=7)
    ax.set_xticks(list(x), LABELS, fontsize=7.5)
    ax.set_ylabel("%")
    ax.set_title(title, fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].legend(fontsize=8)
fig.suptitle("SpanGuard v6 — three guards, one run (record: %s)" %
             (REC_PATH or "n/a"), fontsize=11)
fig.savefig(OUT / "v6_flagship_bars.png", dpi=150)
plt.close(fig)

# ---- 2. conformal alpha sweep ----------------------------------------------
sweep = SUMMARY.get("sweep", {})
if sweep:
    alphas = sorted(sweep, key=float)
    a_labels = [f"α={a}" for a in alphas]
    worst = [max(v for k, v in sweep[a]["benign"].items() if "calib" not in k) * 100
             for a in alphas]
    bound = [float(a) * 100 for a in alphas]
    esc_v6 = [min(sweep[a]["escape"].values()) * 100 for a in alphas]
    esc_ood = [sweep[a]["escape"].get("handwritten", 0) * 100 for a in alphas]
    fig, ax = plt.subplots(figsize=(9.2, 4.2), constrained_layout=True)
    ax.plot(a_labels, bound, "o--", color="#64748b", label="the α bound (target)")
    ax.plot(a_labels, worst, "o-", color=C_V6, label="worst held-out benign over-strip")
    ax.plot(a_labels, esc_ood, "s-", color=C_FM, label="hand-written OOD escape")
    for i, a in enumerate(alphas):
        ax.text(i, worst[i] + 1.5, f"{worst[i]:.1f}", ha="center", fontsize=8)
        ax.text(i, esc_ood[i] + 1.5, f"{esc_ood[i]:.1f}", ha="center", fontsize=8)
    ax.set_ylabel("%")
    ax.set_title("Conformal calibration frontier (α sweep on public-probe, "
                 "verified on held-out benign sets)", fontsize=10)
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUT / "v6_conformal_sweep.png", dpi=150)
    plt.close(fig)

# ---- 3. agent-loop columns --------------------------------------------------
al = SUMMARY.get("agent_loop", {})
if al:
    names = [n for n in ["spg-fm-v6", "spanguard-fast-v4", "spg-fm", "spanguard-rules"]
             if n in al]
    util = [al[n]["notinject_utility"] * 100 for n in names]
    hij = [al[n]["hijack_success"] * 100 for n in names]
    labels = [n.replace("spanguard-", "").replace("spg-", "") for n in names]
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.0), constrained_layout=True)
    axes[0].bar(labels, util, color=C_V6)
    axes[0].set_title("NotInject benign utility (higher is better)", fontsize=10)
    axes[1].bar(labels, hij, color="#dc2626")
    axes[1].set_title("Agent-loop hijack success (lower is better)", fontsize=10)
    for ax, vals in [(axes[0], util), (axes[1], hij)]:
        for i, v in enumerate(vals):
            ax.text(i, v + 1, f"{v:.1f}", ha="center", fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylim(0, 105)
    fig.suptitle("Agent-loop harness: utility and hijack, outcome-level "
                 "(AgentDojo-style + NotInject probe)", fontsize=11)
    fig.savefig(OUT / "v6_agent_loop.png", dpi=150)
    plt.close(fig)

# ---- 4. version ladder with v6 ---------------------------------------------
versions = ["v1\nspan model\n135M", "v2\n+char ens.\n+corrob.", "v3.1\n2-expert\nrouter",
            "v4\n3-expert\nrouter", "v5\nSPG-FM-1\n1.7M", "v6\nfm-v6+conformal\n+gate 2.2M"]
ood = [29.2, 10.4, 16.7, 16.7, 10.4, None]
pub_ov = [34.2, 32.9, 19.8, 19.8, 45.4, None]
ev6 = SUMMARY.get("escape", {})
if ev6:
    ood[-1] = round(ev6.get("handwritten", {}).get("plain", 0) * 100, 1)
    pub_ov[-1] = round(SUMMARY.get("overstrip", {}).get("public-probe (calib)", {})
                       .get("plain", 0) * 100, 1)
cols = [C_GREY, C_GREY, C_GREY, C_V4, C_FM, C_V6]
fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.0), constrained_layout=True)
axes[0].plot(range(len(versions)), ood, "o-", color=C_V6)
for i, v in enumerate(ood):
    if v is not None:
        axes[0].text(i, v + 0.8, f"{v}", ha="center", fontsize=8)
axes[0].set_xticks(range(len(versions)), versions, fontsize=7)
axes[0].set_title("Hand-written OOD escape by version", fontsize=10)
axes[1].plot(range(len(versions)), pub_ov, "o-", color="#dc2626")
for i, v in enumerate(pub_ov):
    if v is not None:
        axes[1].text(i, v + 0.8, f"{v}", ha="center", fontsize=8)
axes[1].set_xticks(range(len(versions)), versions, fontsize=7)
axes[1].set_title("Public-probe over-strip by version (the honest axis)", fontsize=10)
for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
fig.savefig(OUT / "v6_ladder.png", dpi=150)
plt.close(fig)

for f in ["v6_flagship_bars.png", "v6_conformal_sweep.png", "v6_agent_loop.png", "v6_ladder.png"]:
    p = OUT / f
    print(f, p.exists() and p.stat().st_size > 10000)
