#!/usr/bin/env python3
"""Replay the v4.0.0 + v5-prep code patches (lost with the root-locked repo dir)
onto the fresh clone. Idempotent: each patch asserts its anchor exists."""
from pathlib import Path
import json
import ast

REPO = Path(__file__).resolve().parents[1]


def patch(path: str, old: str, new: str, label: str) -> None:
    p = REPO / path
    s = p.read_text()
    if new in s:
        print(f"skip (already applied): {label}")
        return
    assert old in s, f"anchor missing for {label} in {path}"
    s = s.replace(old, new, 1)
    p.write_text(s)
    ast.parse(s) if path.endswith(".py") else None
    print(f"patched: {label}")


# ---------------- pipeline.py: fm mode ----------------
patch("src/spanguard/detect/pipeline.py",
      'if mode not in {"rules", "fast", "fast-v2", "fast-v3", "fast-v4", "audit"}:',
      'if mode not in {"rules", "fast", "fast-v2", "fast-v3", "fast-v4", "fm", "audit"}:',
      "pipeline: fm mode accepted")
patch("src/spanguard/detect/pipeline.py",
      'if self.mode in {"fast", "fast-v2", "fast-v3", "fast-v4", "audit"}:',
      'if self.mode in {"fast", "fast-v2", "fast-v3", "fast-v4", "fm", "audit"}:',
      "pipeline: fm loads char stack")
patch("src/spanguard/detect/pipeline.py",
      'if self.mode in {"fast-v2", "fast-v3", "fast-v4"} and not is_structured(text):',
      'if self.mode in {"fast-v2", "fast-v3", "fast-v4", "fm"} and not is_structured(text):',
      "pipeline: fm prose path")
patch("src/spanguard/detect/pipeline.py",
      '''        if self.mode in {"fast-v2", "fast-v3", "fast-v4"}:
            try:
                thr = self.char_threshold(text)
                if self.mode == "fast-v3":''',
      '''        if self.mode in {"fast-v2", "fast-v3", "fast-v4", "fm"}:
            try:
                thr = self.char_threshold(text)
                if self.mode == "fm":
                    from .router import fm_char_spans
                    char_spans, _, _route = fm_char_spans(text, threshold=thr)
                elif self.mode == "fast-v3":''',
      "pipeline: fm char dispatch")
patch("src/spanguard/detect/pipeline.py",
      '''        if self.mode in {"fast-v2", "fast-v3", "fast-v4"} and self._char_ok:
            d.append("char" if self.mode == "fast-v2"
                     else "char-router(v2+v3)" if self.mode == "fast-v3" else "char-router(v2+v3+v4)")''',
      '''        if self.mode in {"fast-v2", "fast-v3", "fast-v4", "fm"} and self._char_ok:
            d.append("char" if self.mode == "fast-v2"
                     else "char-router(v2+v3)" if self.mode == "fast-v3"
                     else "char-router(v2+v3+v4)" if self.mode == "fast-v4" else "spg-fm-1")''',
      "pipeline: fm detector label")
patch("src/spanguard/detect/pipeline.py",
      '''            if self.mode == "fast-v3":
                from .router import is_extended_domain

                dir_path = (os.environ.get("SPANGUARD_CHAR_MODEL_V3")
                            if is_extended_domain(text) else os.environ.get("SPANGUARD_CHAR_MODEL"))''',
      '''            if self.mode == "fm":
                dir_path = os.environ.get("SPANGUARD_FM_MODEL")
            elif self.mode == "fast-v3":
                from .router import is_extended_domain

                dir_path = (os.environ.get("SPANGUARD_CHAR_MODEL_V3")
                            if is_extended_domain(text) else os.environ.get("SPANGUARD_CHAR_MODEL"))''',
      "pipeline: fm threshold model dir")
patch("src/spanguard/detect/pipeline.py",
      '''            if self.mode in {"fast-v3", "fast-v4"}:
                from .router import is_extended_domain, route_v4
                # prose bump protects against neural FPs on out-of-domain prose;
                # routed (in-domain) docs use the routed model's own calibration
                routed = (is_extended_domain(text) if self.mode == "fast-v3"
                          else route_v4(text) in {"v3", "v4"})
                bump = 0.0 if routed else (_PROSE_CHAR_BUMP if not is_structured(text) else 0.0)
                return base + bump''',
      '''            if self.mode in {"fast-v3", "fast-v4", "fm"}:
                from .router import is_extended_domain, route_v4
                # prose bump protects against neural FPs on out-of-domain prose;
                # routed (in-domain) docs use the routed model's own calibration
                routed = (is_extended_domain(text) if self.mode == "fast-v3"
                          else route_v4(text) in {"v3", "v4"} if self.mode == "fast-v4" else True)
                bump = 0.0 if routed else (_PROSE_CHAR_BUMP if not is_structured(text) else 0.0)
                return base + bump''',
      "pipeline: fm threshold no prose bump")
patch("src/spanguard/detect/pipeline.py",
      '''                if self.mode in {"fast-v3", "fast-v4"}:
                    from .router import is_extended_domain, route_v4
                    routed = (is_extended_domain(text) if self.mode == "fast-v3"
                              else route_v4(text) in {"v3", "v4"})
                    if routed:
                        prose = False  # routed docs trust the in-domain char model (union)''',
      '''                if self.mode in {"fast-v3", "fast-v4", "fm"}:
                    from .router import is_extended_domain, route_v4
                    routed = (is_extended_domain(text) if self.mode == "fast-v3"
                              else route_v4(text) in {"v3", "v4"} if self.mode == "fast-v4" else True)
                    if routed:
                        prose = False  # routed docs trust the in-domain char model (union)''',
      "pipeline: fm union trust")

# ---------------- router.py: fm entry ----------------
p = REPO / "src/spanguard/detect/router.py"
s = p.read_text()
if "def fm_char_spans" not in s:
    s += '''

def fm_char_spans(text: str, threshold: float | None = None):
    """SPG-FM path: one foundational model for every domain — no routing.
    Model dir from env SPANGUARD_FM_MODEL (falls back to the v2 char model)."""
    import os

    from .char_guard import char_spans

    model = os.environ.get("SPANGUARD_FM_MODEL") or os.environ.get("SPANGUARD_CHAR_MODEL")
    spans, doc_p = char_spans(text, dir_path=model, threshold=threshold)
    return spans, doc_p, "spg-fm-1"
'''
    p.write_text(s)
    ast.parse(s)
    print("patched: router fm_char_spans")
else:
    print("skip: router fm_char_spans")

# ---------------- eval/cli.py: char-v4 + spg-fm branches ----------------
patch("src/spanguard/eval/cli.py",
      '''        elif sysname == "spanguard-fast-v4":''',
      '''        elif sysname == "spanguard-char-v4":
            try:
                from ..detect.char_guard import char_guard_system

                fn = char_guard_system(model_dir=str(REPO / "data" / "models" / "spanguard-char-v4"))
            except Exception as exc:  # noqa: BLE001
                print(f"skip spanguard-char-v4: {exc}")
                continue
        elif sysname == "spg-fm":
            try:
                fn = guard_system("fm")
            except Exception as exc:  # noqa: BLE001
                print(f"skip spg-fm: {exc}")
                continue
        elif sysname == "spanguard-fast-v4":''',
      "cli: char-v4 + spg-fm branches")

# ---------------- config.json: spg-fm system ----------------
p2 = REPO / "docs/benchmarks/config.json"
d = json.loads(p2.read_text())
tags = [x["tag"] for x in d["systems"]]
if "spg-fm" not in tags:
    d["systems"].insert(0, {"tag": "spg-fm",
        "label": "SPG-FM-1 (domain foundational model — one model, no router)",
        "short": "SPG-FM-1", "color": "#6d28d9", "color_dark": "#a78bfa",
        "cost_usd_per_1m_docs": 0, "required": True})
    p2.write_text(json.dumps(d, indent=2))
    print("patched: config spg-fm")
else:
    print("skip: config spg-fm")

# ---------------- version 4.0.0 ----------------
for path, old, new in [("src/spanguard/__init__.py", '__version__ = "0.1.0"', '__version__ = "4.0.0"'),
                       ("pyproject.toml", 'version = "0.1.0"', 'version = "4.0.0"')]:
    patch(path, old, new, f"version: {path}")

print("ALL CODE PATCHES APPLIED")
