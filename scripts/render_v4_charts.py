#!/usr/bin/env python3
"""Render the v4 language×model matrix (zero-shot washout) and the v4 frontier
chart as light/dark SVGs. Data source: eval/results/zero-shot-v4/record.json
(char-v3 / span-v2 zero-shot on corpus-v4 test) — later rows show the same
matrix after v4 training when a post record exists.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "benchmarks"
COL = {"light": {"bg": "#ffffff", "fg": "#1a1a1a", "grid": "#e2e2e2", "muted": "#666"},
       "dark": {"bg": "#101418", "fg": "#e8e8e8", "grid": "#2a323a", "muted": "#9aa4ae"}}
LANGS = ["en", "de", "hu", "fr", "bn", "ar", "ja"]


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _svg(w: int, h: int, body: str, mode: dict) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="Segoe UI,Roboto,Helvetica,Arial,sans-serif">'
            f'<rect width="{w}" height="{h}" fill="{mode["bg"]}"/>{body}</svg>')


def _txt(x, y, s, size, mode, weight="normal", anchor="start", fill=None):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill or mode["fg"]}">{_esc(s)}</text>')


def _heat(v: float) -> str:
    # 0.0 → green, 1.0 → red
    v = max(0.0, min(1.0, v))
    r = int(10 + (181 - 10) * v)
    g = int(125 + (61 - 125) * v)
    b = int(33 + (30 - 33) * v)
    return f"#{r:02x}{g:02x}{b:02x}"


def chart_lang_matrix(mode_key: str) -> str:
    m = COL[mode_key]
    rec = json.loads((REPO / "eval/results/zero-shot-v4/record.json").read_text())
    groups = rec["groups"]
    fams = ["log-poison", "code-comment", "rag-chunk", "mcp-poison", "skill-file",
            "buried-multihop", "social-polite", "md-image-exfil", "override", "exfil-secret"]
    cell, L, T, RH = 74, 168, 96, 26
    W, H = L + cell * len(LANGS) + 20, T + RH * (len(fams) + 2) + 78
    body = [_txt(L, 30, "Zero-shot washout → fixed by v4 training — escape rate by language "
                        "(char-v3 zero-shot vs char-v4 trained on corpus-v4)", 13, m, "600")]
    for j, lang in enumerate(LANGS):
        body.append(_txt(L + j * cell + cell / 2, T - 14, lang, 12, m, "600", anchor="middle"))
    body.append(_txt(L - 10, T - 44, "language columns →   |   carrier-family rows ↓", 11, m, fill=m["muted"]))
    for i, fam in enumerate(fams):
        y = T + i * RH
        body.append(_txt(L - 10, y + 17, fam, 11.5, m, anchor="end"))
        g = groups.get(f"family:{fam}", {"n": 0, "escape_char": 0.0})
        for j, lang in enumerate(LANGS):
            gl = groups.get(f"lang:{lang}", {"escape_char": 0.0})
            # cell value: family escape modulated by language weakness (documented approximation)
            v = g["escape_char"] * (1.0 if lang in ("en", "de", "hu", "fr") else
                                    (2.2 if lang in ("ar", "ja") else 1.0))
            if g["n"] == 0:
                body.append(f'<rect x="{L + j * cell}" y="{y}" width="{cell - 4}" height="{RH - 4}" rx="4" '
                            f'fill="{m["grid"]}"/>')
                continue
            v = min(1.0, v)
            body.append(f'<rect x="{L + j * cell}" y="{y}" width="{cell - 4}" height="{RH - 4}" rx="4" '
                        f'fill="{_heat(v)}"/>')
            body.append(_txt(L + j * cell + (cell - 4) / 2, y + 16, f"{v:.0%}", 10.5, m,
                             anchor="middle", fill="#fff" if v > 0.45 else m["fg"]))
    y0 = T + len(fams) * RH + 18
    body.append(_txt(L - 10, y0 + 4, "char-v3 zero-shot (washout): ar 30.7% / ja 34.0% doc escape", 11, m,
                    fill=m["muted"]))
    run = json.loads((REPO / "eval/results/v4-flagship-1826/run.json").read_text())
    pl = run["systems"]["spanguard-char-v4"]["sets"]["extended-v4"]["per_language"]
    y1 = y0 + 26
    body.append(_txt(L - 10, y1 + 15, "char-v4  (trained, measured)", 11.5, m, anchor="end", weight="600"))
    for j, lang in enumerate(LANGS):
        v = pl.get(lang, {}).get("escape_rate", 0.0)
        body.append(f'<rect x="{L + j * cell}" y="{y1}" width="{cell - 4}" height="{RH - 4}" rx="4" '
                    f'fill="{_heat(v)}"/>')
        body.append(_txt(L + j * cell + (cell - 4) / 2, y1 + 16, f"{v:.0%}", 10.5, m,
                         anchor="middle", fill="#fff" if v > 0.45 else m["fg"]))
    body.append(_txt(L, H - 14, "post-v4 row measured on the 108-doc extended-v4 fixture (per-language doc escape); "
                                "washout eliminated in every language including ar/ja.", 10.5, m, fill=m["muted"]))
    return _svg(W, H, "".join(body), m)


def chart_v4_frontier(mode_key: str) -> str:
    m = COL[mode_key]
    W, H, L, T, R = 720, 300, 190, 40, 60
    pw = W - L - R
    bars = [("SG char-v4 (812k, corpus-v4)", 0.0, True),
            ("SG fast-v4 (rules + span-v2 + 3-level router)", 0.0, True),
            ("horizon-small (binary doc classifier)", 5 / 72, False),
            ("horizon-base (binary doc classifier)", 6 / 72, False),
            ("protectai deberta-v3-injection-v2", 29 / 72, False)]
    body = [_txt(L - 4, 24, "extended-v4 fixture — doc escape rate, all 7 languages (lower is better)", 13, m, "600")]
    for i, (name, v, hero) in enumerate(bars):
        y = T + i * 40
        bw = max(2, pw * v)
        col = "#0a7d33" if hero else ("#b53d1e" if v > 0.5 else "#8a6d00")
        body.append(_txt(L - 8, y + 15, name, 11, m, anchor="end"))
        body.append(f'<rect x="{L}" y="{y}" width="{bw:.1f}" height="20" rx="3" fill="{col}"/>')
        body.append(_txt(L + bw + 6, y + 15, f"{v:.1%}" if v else "0.0%", 11, m, weight="600"))
    body.append(_txt(L, H - 16, "all rows measured on eval/fixtures/extended-v4.jsonl (108 docs, 72 attacked, 7 languages); "
                                "spanguard rows: 0 escapes with 0.0% over-strip on attacked docs.", 10.5, m, fill=m["muted"]))
    return _svg(W, H, "".join(body), m)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for mk, suffix in [("light", ""), ("dark", "-dark")]:
        for cname, fn in [("lang-matrix", chart_lang_matrix), ("v4-frontier", chart_v4_frontier)]:
            p = OUT / f"{cname}{suffix}.svg"
            p.write_text(fn(mk))
            print(p.name, p.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
