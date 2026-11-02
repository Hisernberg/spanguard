"""Scorer + fixtures tests: metrics computed on known ground truth."""

import json
from pathlib import Path

from spanguard.eval.scorer import score_documents
from spanguard.types import Finding, Result

FIXTURES = Path(__file__).resolve().parents[1] / "eval" / "fixtures"


def perfect_guard(doc):
    """A guard that strips exactly the gold spans."""
    cleaned = doc["text"]
    for s in sorted(doc.get("spans", []), key=lambda x: -x["start"]):
        cleaned = cleaned[: s["start"]] + "[stripped]" + cleaned[s["end"]:]
    findings = [Finding(start=s["start"], end=s["end"], length=s["end"] - s["start"],
                        kind=s.get("family", "x"), source="oracle", confidence=1.0, sha256="")
                for s in doc.get("spans", [])]
    return Result(original=doc["text"], cleaned=cleaned, stripped=findings)


def blind_guard(doc):
    return Result(original=doc["text"], cleaned=doc["text"], stripped=[])


def strip_all_guard(doc):
    f = Finding(start=0, end=len(doc["text"]), length=len(doc["text"]), kind="all",
                source="strip-all", confidence=1.0, sha256="")
    if doc.get("spans") or doc.get("binary_attack"):
        return Result(original=doc["text"], cleaned="", stripped=[f])
    return Result(original=doc["text"], cleaned=doc["text"], stripped=[])


def test_perfect_guard_zero_escape():
    docs = [json.loads(l) for l in open(FIXTURES / "handwritten-en.jsonl", encoding="utf-8")]
    m = score_documents(docs, perfect_guard)
    assert m["escape_rate"] == 0.0
    assert m["overstrip_rate"] == 0.0
    assert m["doc_f1"] == 1.0
    assert m["span_f1"] == 1.0


def test_blind_guard_leaks_everything():
    docs = [json.loads(l) for l in open(FIXTURES / "handwritten-en.jsonl", encoding="utf-8")]
    m = score_documents(docs, blind_guard)
    assert m["escape_rate"] == 1.0
    assert m["doc_recall"] == 0.0
    assert m["overstrip_rate"] == 0.0


def test_paranoid_guard_zero_escape_but_destroys_data():
    """A guard that nukes every doc: no escapes, but all benign data is lost."""
    docs = [json.loads(l) for l in open(FIXTURES / "handwritten-en.jsonl", encoding="utf-8")]

    def paranoid_guard(doc):
        f = Finding(start=0, end=len(doc["text"]), length=len(doc["text"]), kind="all",
                    source="paranoid", confidence=1.0, sha256="")
        return Result(original=doc["text"], cleaned="", stripped=[f])

    m = score_documents(docs, paranoid_guard)
    assert m["escape_rate"] == 0.0
    assert m["overstrip_rate"] == 1.0  # 100% of benign data destroyed


def test_binary_attack_docs_count_in_doc_detection():
    docs = [{"id": "x", "lang": "en", "text": "attack prompt", "spans": [], "binary_attack": True},
            {"id": "y", "lang": "en", "text": "benign prompt", "spans": [], "binary_attack": False}]
    m = score_documents(docs, blind_guard)
    assert m["doc_recall"] == 0.0 and m["docs"] == 2
    m2 = score_documents(docs, strip_all_guard)
    assert m2["doc_f1"] == 1.0


def test_agent_traffic_fixture_loads():
    docs = [json.loads(l) for l in open(FIXTURES / "agent-traffic.jsonl", encoding="utf-8")]
    assert len(docs) >= 800
    assert any(d["attack"] for d in docs)
    assert any(not d["attack"] for d in docs)
