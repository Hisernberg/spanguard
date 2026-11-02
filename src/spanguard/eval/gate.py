"""Eval regression gate: run the fast systems now, compare with the newest
committed run record of the same system on the same fixture sets.

Used by CI (``make gate``). Escape/over-strip must not rise, F1 must not fall,
beyond absolute tolerances. Never raise a tolerance to make a PR pass without
saying why in the PR.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RESULTS = REPO / "eval" / "results"
GATES = json.loads((REPO / "eval" / "gates.json").read_text())

TOLERANCE = {"escape_rate": 0.02, "overstrip_rate": 0.03, "doc_f1": 0.02, "span_f1": 0.02}


def newest_committed(system: str, exclude: Path | None = None) -> dict | None:
    """Newest committed run record containing this system (dirs sort by date-stamp)."""
    for run_dir in sorted(RESULTS.iterdir(), reverse=True):
        if exclude is not None and run_dir.resolve() == exclude.resolve():
            continue
        f = run_dir / "run.json"
        if not f.is_file():
            continue
        data = json.loads(f.read_text())
        if system in data.get("systems", {}):
            return data["systems"][system]
    return None


def compare(system: str, current: dict, previous: dict) -> list[str]:
    failures: list[str] = []
    for set_name, cur in current.get("sets", {}).items():
        old = previous.get("sets", {}).get(set_name)
        if not old:
            continue
        for metric, tol in TOLERANCE.items():
            c, o = cur.get(metric), old.get(metric)
            if c is None or o is None:
                continue
            lower_is_better = metric not in {"doc_f1", "span_f1"}
            delta = (c - o) if lower_is_better else (o - c)
            if delta > tol:
                failures.append(f"{system}/{set_name}: {metric} regressed {o:.4f} -> {c:.4f} (tolerance {tol})")
    return failures


def main() -> int:
    from .cli import run_eval

    systems = GATES["systems"]
    sets = GATES["sets"]
    run_dir = run_eval(systems, sets, tag="gate")
    failures: list[str] = []
    data = json.loads((run_dir / "run.json").read_text())
    for system in systems:
        previous = newest_committed(system, exclude=run_dir)
        if previous is None:
            print(f"gate: {system}: no committed baseline yet (first run sets it)")
            continue
        failures += compare(system, data["systems"][system], previous)
    if failures:
        print("EVAL GATE FAILED")
        for f in failures:
            print(" -", f)
        return 1
    print("eval gate: OK (no regressions against committed run records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
