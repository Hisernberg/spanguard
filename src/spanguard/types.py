"""Core types: documents, spans, verdicts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict


@dataclass
class Span:
    """A character span ``[start, end)`` in the source text that is attack text."""

    start: int
    end: int
    kind: str          # override | impersonation | exfil | forgery | encoding | smuggle | spoof
    source: str        # rule:<name> | model | teacher | planted
    rule: str = ""     # rule name when source starts with "rule"
    confidence: float = 1.0

    def clipped(self, n: int) -> "Span":
        return Span(max(0, self.start), min(n, self.end), self.kind, self.source, self.rule, self.confidence)

    def overlaps(self, other: "Span") -> bool:
        return self.start < other.end and other.start < self.end

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Finding:
    """A stripped span as reported to the caller (no original text)."""

    start: int
    end: int
    length: int
    kind: str
    source: str
    confidence: float
    sha256: str        # hash of the removed text, for logs without leaking the payload

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Result:
    """Outcome of guarding one text: cleaned text plus where the attack was."""

    original: str
    cleaned: str
    stripped: list[Finding] = field(default_factory=list)

    @property
    def attacked(self) -> bool:
        return bool(self.stripped)

    def stripped_chars(self) -> int:
        return sum(f.length for f in self.stripped)

    def as_dict(self) -> dict:
        return {
            "attacked": self.attacked,
            "n_stripped": len(self.stripped),
            "stripped_chars": self.stripped_chars(),
            "findings": [f.as_dict() for f in self.stripped],
            "cleaned": self.cleaned,
        }


MARKER = "[stripped]"
#: Marker with length accounted when reconstructing cleaned text.


def doc_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def spans_to_json(spans: list[Span]) -> str:
    return json.dumps([s.as_dict() for s in spans], ensure_ascii=False)
