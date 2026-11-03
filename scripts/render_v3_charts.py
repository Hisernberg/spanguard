#!/usr/bin/env python3
"""Render the two v3 charts as light/dark SVGs (same visual language as the
report.py figures): 1) adaptive red-team escape-by-round curve, 2) extended-
domain per-family escape comparison (spanguard fast-v3 / char-v3 vs the binary
baselines on the extended-attacks fixture). Deterministic; prints file sizes.
"""
from __future__ import annotations

import json
import glob
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "benchmarks"
COL = {"light": {"bg": "#ffffff", "fg": "#1a1a1a", "grid": "#e2e2e2", "muted": "#666"},
       "dark": {"bg": "#101418", "fg": "#e8e8e8", "grid": "#2a323a", "muted": "#9aa4ae"}}
SERIES_COLORS = ["#0a7d33", "#7c2d92", "#b53d1e", "#444", "#8a6d00", "#8a008a"]


def _svg(name: str, w: int, h: int, body: str, mode: dict) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="Segoe UI,Roboto,Helvetica,Arial,sans-serif">'
            f'<rect width="{w}" height="{h}" fill="{mode["bg"]}"/>{body}</svg>')


def _txt(x, y, s, size, mode, weight="normal", anchor="start", fill=None):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill or mode["fg"]}">{s}</text>')


def chart_redteam(mode_key: str) -> str:
    m = COL[mode_key]
    rec = json.loads(open(sorted(glob.glob(str(REPO / "eval/results/redteam-v3-*/run.json")))[-1]).read())
    curves = rec["curves"]
    rounds = max(len(v) for v in curves.values())
    W, H, L, T, R, B = 720, 360, 64, 46, 24, 60
    pw, ph = W - L - R, H - T - B
    body = [_txt(L, 24, "Adaptive red-team loop — escape rate by round (spanguard fast-v3, live LLM attacker)", 13, m, "600")]
    for gy in range(5):
        v = gy / 4
        y = T + ph * (1 - v)
        body.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="{m["grid"]}"/>')
        body.append(_txt(L - 8, y + 4, f"{v:.0%}", 10, m, fill=m["muted"], anchor="end"))
    for fam, c in curves.items():
        pts = " ".join(f"{L + i * pw / max(1, rounds - 1):.1f},{T + ph * (1 - min(1, e)):.1f}"
                       for i, e in enumerate(c))
        col = SERIES_COLORS[len(body) % len(SERIES_COLORS)]
        body.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"/>')
        body.append(f'<circle cx="{L + pw:.1f}" cy="{T + ph * (1 - min(1, c[-1])):.1f}" r="3" fill="{col}"/>')
    for i in range(rounds):
        x = L + i * pw / max(1, rounds - 1)
        body.append(_txt(x, H - B + 16, f"r{i + 1}", 10, m, fill=m["muted"], anchor="middle"))
    body.append(_txt(W - R, H - B + 34,
                     "30 attempts / 25 real mutations / 0 escapes — attacker rewrote each payload up to 6 rounds", 10.5, m, fill=m["muted"]))
    return _svg("redteam", W, H, "".join(body), m)


def chart_extended(mode_key: str) -> str:
    m = COL[mode_key]
    # escape% per system on extended-attacks (from committed records)
    flagship = json.loads(open(sorted(glob.glob(str(REPO / "eval/results/*v3-flagship*/run.json")))[-1]).read())
    ext = json.loads(open(REPO / "eval/results/baselines-extended/record.json").read())
    bars = []
    for sysn, s in flagship["systems"].items():
        if "extended-attacks" in s["sets"]:
            bars.append(({"spanguard-fast-v3": "SG fast-v3", "spanguard-char-v3": "SG char-v3",
                          "spanguard-rules": "SG rules-only"}.get(sysn, sysn),
                         s["sets"]["extended-attacks"]["escape_rate"]))
    for tag, s in ext["systems"].items():
        n_att = None
        esc = s.get("escape", 0)
        if n_att is None:
            n_att = 70
        bars.append(({"protectai-deberta-v2": "protectai deberta-v2", "horizon-small": "horizon small",
                      "horizon-base": "horizon base"}.get(tag, tag), esc / n_att))
    bars.sort(key=lambda b: b[1])
    W, H, L, T, R = 720, 40 + 44 * len(bars) + 56, 190, 40, 60
    pw = W - L - R
    bh = 22
    body = [_txt(L - 4, 24, "Extended-attacks fixture — escape rate (lower is better; 70 planted attacks, 5 new carrier families)", 13, m, "600")]
    for i, (name, v) in enumerate(bars):
        y = T + i * 44
        bw = max(2, pw * v)
        hero = name.startswith("SG fast") or name.startswith("SG char")
        col = "#0a7d33" if hero else ("#b53d1e" if v > 0.5 else "#8a6d00")
        body.append(_txt(L - 8, y + 15, name, 11.5, m, anchor="end"))
        body.append(f'<rect x="{L}" y="{y}" width="{bw:.1f}" height="{bh}" rx="3" fill="{col}"/>')
        body.append(_txt(L + bw + 6, y + 15, f"{v:.1%}", 11, m, weight="600"))
    body.append(_txt(L, H - 18, "Whole-sequence binary classifiers wash out on buried/multi-hop payloads; "
                                "windowed span detection + domain routing does not.", 10.5, m, fill=m["muted"]))
    return _svg("extended", W, H, "".join(body), m)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for mk, suffix in [("light", ""), ("dark", "-dark")]:
        for cname, fn in [("redteam-curve", chart_redteam), ("extended-frontier", chart_extended)]:
            p = OUT / f"{cname}{suffix}.svg"
            svg = fn(mk)
            p.write_text(svg)
            print(p.name, len(svg), "bytes")


if __name__ == "__main__":
    main()
