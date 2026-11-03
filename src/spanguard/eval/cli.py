"""Eval harness: run systems over fixture sets, write committed run records.

Usage: python -m spanguard eval --detectors rules --sets handwritten,agent-traffic
Run records land in eval/results/<date>-<tag>/run.json; `spanguard eval gate`
compares the newest record per system against gates.json (CI regression check).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "eval" / "fixtures"
RESULTS = REPO / "eval" / "results"
DATA = REPO / "data" / "corpus"

SET_FILES = {
    "handwritten": ["handwritten-en.jsonl", "handwritten-de.jsonl", "handwritten-hu.jsonl"],
    "agent-traffic": ["agent-traffic.jsonl"],
    "public-deepset": ["public-deepset.jsonl"],
}


def load_set(name: str, limit: int | None = None) -> list[dict]:
    docs: list[dict] = []
    for f in SET_FILES[name]:
        p = FIXTURES / f
        if not p.exists() and name == "agent-traffic":
            p = DATA / "test.jsonl"
        if p.exists():
            docs += [json.loads(l) for l in open(p, encoding="utf-8")]
    if limit:
        docs = docs[:limit]
    return docs


def load_docs_for_sets(names: list[str], limit: int | None = None) -> dict[str, list[dict]]:
    return {n: load_set(n, limit) for n in names}


def guard_system(mode: str):
    from ..detect.pipeline import Guard

    g = Guard(mode=mode)

    def fn(doc: dict):
        return g.guard(doc["text"])

    return fn


def external_system(record: dict, tag: str):
    """Build a guard_fn from a kernel-produced baseline record (strip-all semantics)."""
    flags = record.get("_flags", {})  # doc_id -> flagged

    def fn(doc: dict):
        from ..types import Finding, Result

        if flags.get(doc["id"]):
            finding = Finding(start=0, end=len(doc["text"]), length=len(doc["text"]),
                              kind="attack-doc", source=f"baseline:{tag}", confidence=1.0, sha256="")
            return Result(original=doc["text"], cleaned="", stripped=[finding])
        return Result(original=doc["text"], cleaned=doc["text"], stripped=[])

    return fn


def llm_selfdetect_system(limit: int | None = None, concurrency: int = 4):
    """LLM self-detection baseline. Reads the precomputed verdicts sidecar when
    present (training/eval_llm_detect.py); falls back to live calls otherwise."""
    from ..types import Finding, Result  # noqa: PLC0415

    sidecar = RESULTS / "llm-self-detect" / "verdicts.json"
    verdicts: dict = {}
    if sidecar.exists():
        verdicts = json.loads(sidecar.read_text()).get("verdicts", {})

    if verdicts:
        def fn(doc: dict):
            findings = [Finding(start=s["start"], end=s["end"], length=s["end"] - s["start"],
                                kind=s.get("family", "override"), source="llm-self", confidence=1.0, sha256="")
                        for s in verdicts.get(doc["id"], [])]
            cleaned = doc["text"]
            for f in sorted(findings, key=lambda x: x.start, reverse=True):
                cleaned = cleaned[: f.start] + "[stripped]" + cleaned[f.end:]
            return Result(original=doc["text"], cleaned=cleaned, stripped=findings)

        return fn

    sys.path.insert(0, str(REPO / "training"))
    from label_teacher import label_doc, load_key, match_span  # noqa: PLC0415

    api_key = load_key()
    client = __import__("httpx").Client()

    def fn(doc: dict):
        attacks, _ = label_doc(client, api_key, doc["text"])
        findings = []
        for a in attacks:
            m = match_span(doc["text"], a["quote"])
            if m:
                findings.append(Finding(start=m[0], end=m[1], length=m[1] - m[0], kind=a.get("family", "override"),
                                        source="llm-self", confidence=1.0, sha256=""))
        cleaned = doc["text"]
        for f in sorted(findings, key=lambda x: x.start, reverse=True):
            cleaned = cleaned[: f.start] + "[stripped]" + cleaned[f.end:]
        r = Result(original=doc["text"], cleaned=cleaned, stripped=findings)
        r.latency_ms = 0.0  # latency tracked separately in the run manifest
        return r

    return fn


def run_eval(systems: list[str], sets: list[str], tag: str | None = None, limit: int | None = None) -> Path:
    from .scorer import score_documents

    docs_by_set = load_docs_for_sets(sets, limit)
    out: dict = {"generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                 "environment": {"python": platform.python_version(), "platform": platform.platform()},
                 "systems": {}}
    for sysname in systems:
        if sysname == "spanguard-rules":
            fn = guard_system("rules")
        elif sysname == "spanguard-fast":
            try:
                fn = guard_system("fast")
            except Exception as exc:  # noqa: BLE001
                print(f"skip spanguard-fast: {exc}")
                continue
        elif sysname == "spanguard-fast-v2":
            try:
                fn = guard_system("fast-v2")
            except Exception as exc:  # noqa: BLE001
                print(f"skip spanguard-fast-v2: {exc}")
                continue
        elif sysname == "spanguard-fast-mdistil-v2":
            # same fast pipeline; SPANGUARD_MODEL must point at the v2 model dir
            try:
                fn = guard_system("fast")
            except Exception as exc:  # noqa: BLE001
                print(f"skip spanguard-fast-mdistil-v2: {exc}")
                continue
        elif sysname == "spanguard-char":
            try:
                from ..detect.char_guard import char_guard_system  # noqa: PLC0415

                fn = char_guard_system()
            except Exception as exc:  # noqa: BLE001
                print(f"skip spanguard-char: {exc}")
                continue
        elif sysname.startswith("baseline:"):
            rec_path = RESULTS / sysname.split(":", 1)[1]
            record = json.loads(Path(rec_path).read_text())
            fn = external_system(record, sysname)
        elif sysname == "llm-self-detect":
            fn = llm_selfdetect_system(limit)
            # restrict to the docs the sidecar actually covers (no silent FNs)
            covered = RESULTS / "llm-self-detect" / "verdicts.json"
            if covered.exists():
                ids = set(json.loads(covered.read_text()).get("verdicts", {}))
                docs_by_set = {n: [d for d in docs if d["id"] in ids] for n, docs in docs_by_set.items()}
        else:
            raise ValueError(f"unknown system {sysname}")
        t0 = dt.datetime.now(dt.UTC)
        set_metrics = {}
        for name, docs in docs_by_set.items():
            if not docs:
                continue
            print(f"[{sysname}] scoring {name}: {len(docs)} docs", flush=True)
            set_metrics[name] = score_documents(docs, fn)
        out["systems"][sysname] = {"sets": set_metrics, "wallclock_s": (dt.datetime.now(dt.UTC) - t0).seconds}
    stamp = tag or dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    run_dir = RESULTS / f"{stamp}-{out['generated_at'][11:13]}{out['generated_at'][14:16]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("run record:", run_dir / "run.json")
    return run_dir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--detectors", default="spanguard-rules,spanguard-fast")
    ap.add_argument("--sets", default="handwritten,agent-traffic,public-deepset")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    run_eval(args.detectors.split(","), args.sets.split(","), tag=args.tag, limit=args.limit)


if __name__ == "__main__":
    main()
