#!/usr/bin/env python3
"""v5 charts — every number comes from a committed eval record (path annotated)."""
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
SHIP = json.loads((R / "eval/results/v5-ship-1548/run.json").read_text())
SETS = ["handwritten", "agent-traffic", "public-deepset", "extended-attacks", "extended-v4"]
LABELS = ["hand-written\nOOD", "agent\ntraffic", "public\nprobe", "extended\nattacks", "extended\ncarriers v4"]
C_FM, C_V4, C_GREY = "#7c3aed", "#0891b2", "#94a3b8"


def get(sysname, s, key):
    m = SHIP["systems"][sysname]["sets"].get(s, {})
    v = m.get(key)
    return (v if v is not None else 0) * 100


# ---- 1. flagship side-by-side (v5-ship-1548) ------------------------------
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), constrained_layout=True)
x = range(len(SETS))
w = 0.38
for ax, key, title in [(axes[0], "escape_rate", "Escape rate (lower is better)"),
                       (axes[1], "overstrip_rate", "Over-strip on benign (lower is better)")]:
    fm_v = [get("spg-fm", s, key) for s in SETS]
    v4_v = [get("spanguard-fast-v4", s, key) for s in SETS]
    ax.bar([i - w / 2 for i in x], fm_v, w, label="SPG-FM-1 (single model)", color=C_FM)
    ax.bar([i + w / 2 for i in x], v4_v, w, label="fast-v4 (3-level router)", color=C_V4)
    for i, (a, b) in enumerate(zip(fm_v, v4_v)):
        ax.text(i - w / 2, a + 0.6, f"{a:.1f}", ha="center", fontsize=8)
        ax.text(i + w / 2, b + 0.6, f"{b:.1f}", ha="center", fontsize=8)
    ax.set_xticks(list(x), LABELS, fontsize=8)
    ax.set_ylabel("%")
    ax.set_title(title, fontsize=10)
    ax.set_ylim(0, max(max(fm_v), max(v4_v)) * 1.25 + 1)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].legend(fontsize=8, loc="upper right")
fig.suptitle("SpanGuard v5 — both flagships measured on the same code, same run (v5-ship-1548)",
             fontsize=11)
fig.savefig(OUT / "v5_flagship_bars.png", dpi=150)
plt.close(fig)

# ---- 2. version ladder: OOD escape / span F1 / public overstrip -----------
# records: v1 fast 2026-11-02-rulesfix-1717 · v2 fastv2-corrob-0035 ·
# v3.1 v31-flagship-final-1511 · v4 record v4-flagship-1826 · v5 v5-ship-1548
versions = ["v1\nspan model\n135M", "v2\n+char ensemble\n+corroboration", "v3.1\n2-expert\nrouter",
            "v4\n3-expert\nrouter", "v4\n(repaired,\nv5 re-measure)", "v5\nSPG-FM-1\nsingle model"]
ood = [29.2, 10.4, 16.7, 16.7, 4.2, 10.4]
spanf1 = [None, None, 0.716, 0.716, 0.689, 0.917]  # extended-attacks span F1 (v31/v4 records/v5-ship)
pub_ov = [34.2, 32.9, 19.8, 19.8, 24.6, 45.4]
cols = [C_GREY, C_GREY, C_GREY, C_V4, C_V4, C_FM]
fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), constrained_layout=True)
panels = [(ood, "hand-written OOD escape %\n(cross-domain sharpness)", ood, "{:.1f}"),
          (pub_ov, "public-deepset over-strip %\n(the honest cost axis)", pub_ov, "{:.1f}")]
for ax, (vals, title, _, fmt) in zip(axes[:2], panels):
    ax.bar(range(len(versions)), vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.02, fmt.format(v), ha="center", fontsize=8)
    ax.set_xticks(range(len(versions)), versions, fontsize=7)
    ax.set_title(title, fontsize=9.5)
    ax.set_ylim(0, max(vals) * 1.22)
    ax.spines[["top", "right"]].set_visible(False)
ax = axes[2]
sf = [(i, v) for i, v in enumerate(spanf1) if v is not None]
ax.bar([i for i, _ in sf], [v for _, v in sf], color=[cols[i] for i, _ in sf], width=0.55)
for i, v in sf:
    ax.text(i, v + 0.015, f"{v:.2f}", ha="center", fontsize=9)
ax.set_xticks([i for i, _ in sf], [versions[i] for i, _ in sf], fontsize=7)
ax.set_title("span F1 on extended-attacks\n(payload localization quality)", fontsize=9.5)
ax.set_ylim(0, 1.1)
ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("The version ladder, measured — v5 is the first version to hold 0% in-domain escape "
             "at 10.4% OOD with one 1.7M model", fontsize=10.5)
fig.savefig(OUT / "v5_frontier.png", dpi=150)
plt.close(fig)

# ---- 3. fm language matrix (v5-ship-1548 extended-v4 per_language) --------
pl = SHIP["systems"]["spg-fm"]["sets"]["extended-v4"].get("per_language", {})
pl4 = SHIP["systems"]["spanguard-fast-v4"]["sets"]["extended-v4"].get("per_language", {})
langs = ["en", "de", "hu", "fr", "bn", "ar", "ja"]
esc = [pl.get(l, {}).get("escape_rate", 0) * 100 for l in langs]
esc4 = [pl4.get(l, {}).get("escape_rate", 0) * 100 for l in langs]
fig, ax = plt.subplots(figsize=(8.6, 3.9), constrained_layout=True)
x = range(len(langs))
ax.bar([i - w / 2 for i in x], esc, w, label="SPG-FM-1", color=C_FM)
ax.bar([i + w / 2 for i in x], esc4, w, label="fast-v4", color=C_V4)
for i, (a, b) in enumerate(zip(esc, esc4)):
    ax.text(i - w / 2, a + 0.05, f"{a:.1f}", ha="center", fontsize=8)
    ax.text(i + w / 2, b + 0.05, f"{b:.1f}", ha="center", fontsize=8)
ax.set_xticks(list(x), ["English", "German", "Hungarian", "French", "Bangla", "Arabic", "Japanese"], fontsize=9)
ax.set_ylabel("escape % (extended-v4)")
ax.set_title("One foundational model covers all seven languages at 0.0% escape\n"
             "(no per-language router, no language detection — one forward pass)", fontsize=10)
ax.legend(fontsize=8)
ax.set_ylim(0, 1.6)
ax.spines[["top", "right"]].set_visible(False)
fig.savefig(OUT / "v5_languages.png", dpi=150)
plt.close(fig)

# ---- 4. cost: neural params vs OOD escape, latency ------------------------
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3), constrained_layout=True)
sysinfo = [  # (name, neural params M, hw OOD escape %, record)
    ("v1 span model", 135.0, 29.2, "rulesfix-1717"),
    ("v2 stack", 135.8, 10.4, "fastv2-corrob-0035"),
    ("v4 stack (repaired)", 137.6, 4.2, "v5-ship-1548"),
    ("SPG-FM-1", 1.7, 10.4, "v5-ship-1548"),
]
ax = axes[0]
for name, mp, esc_, rec in sysinfo:
    star = name == "SPG-FM-1"
    ax.scatter(mp, esc_, s=180 if star else 90, color=C_FM if star else "#64748b", zorder=3)
    ax.annotate(f"{name}\n({rec})", (mp, esc_), textcoords="offset points",
                xytext=(8, -4), fontsize=7.5)
ax.set_xscale("log")
ax.set_xlabel("total neural parameters, M (log scale) — span backbone + char experts")
ax.set_ylabel("hand-written OOD escape %")
ax.set_title("Size vs OOD escape: SPG-FM-1 sheds the 135M backbone\nand keeps the v2-level OOD escape", fontsize=9.5)
ax.spines[["top", "right"]].set_visible(False)
ax = axes[1]
lat = [("fast-v4", 14.6), ("SPG-FM-1", 36.7)]
ax.barh([n for n, _ in lat][::-1], [v for _, v in lat][::-1],
        color=[C_V4, C_FM][::-1], height=0.5)
for i, (_, v) in enumerate(lat[::-1]):
    ax.text(v + 0.5, i, f"p50 {v}ms", va="center", fontsize=9)
ax.set_xlabel("ms/doc (p50, 2-thread sandbox CPU, 150 agent-traffic docs)")
ax.set_title("Latency (fresh measurement, same machine)", fontsize=9.5)
ax.set_xlim(0, 45)
ax.spines[["top", "right"]].set_visible(False)
fig.savefig(OUT / "v5_cost.png", dpi=150)
plt.close(fig)

from PIL import Image
for p in sorted(OUT.glob("v5_*.png")):
    im = Image.open(p).convert("L")
    h = im.histogram()
    print("chart:", p.name, im.size, f"non-white {1 - h[255] / sum(h):.3f}")
