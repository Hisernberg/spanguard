"""Merge overlapping spans and strip them from text."""

from __future__ import annotations

import hashlib

from ..types import MARKER, Finding, Result, Span

# kinds that come from the rule engine (typed markers use these verbatim)
_RULE_KINDS = {"override", "impersonation", "exfil", "forgery", "encoding", "smuggle", "spoof"}


def merge_spans(spans: list[Span], gap: int = 2) -> list[Span]:
    """Union of spans; overlapping or near-adjacent (within ``gap`` chars) spans merge.

    Priority on merge: higher confidence, then longer, then rules over model.
    """
    if not spans:
        return []
    ordered = sorted(spans, key=lambda s: (s.start, -(s.confidence), -(s.end - s.start)))
    merged: list[Span] = []
    for s in ordered:
        if merged and (s.start <= merged[-1].end + gap):
            prev = merged[-1]
            end = max(prev.end, s.end)
            winner = prev if (prev.confidence, prev.end - prev.start) >= (s.confidence, s.end - s.start) else s
            merged[-1] = Span(prev.start, end, winner.kind, winner.source, winner.rule, max(prev.confidence, s.confidence))
        else:
            merged.append(s)
    return [s for s in merged if s.end > s.start]


def _marker_for(span: Span, typed: bool) -> str:
    if not typed:
        return MARKER
    kind = span.kind if span.kind in _RULE_KINDS else "injection"
    return f"[stripped:{kind}]"


def strip_spans(text: str, spans: list[Span], marker: str = MARKER, typed: bool = False) -> Result:
    """Replace every merged span with the marker; report findings without the payload.

    ``typed=True`` emits ``[stripped:<kind>]`` (override/exfil/... from rules;
    ``injection`` for neural spans, which carry no family) so the agent can tell
    the user *what* was removed, not just that something was.
    """
    merged = merge_spans(spans)
    merged = [s.clipped(len(text)) for s in merged if s.start < len(text) and s.end > s.start]
    out: list[str] = []
    findings: list[Finding] = []
    cursor = 0
    for s in sorted(merged, key=lambda x: x.start):
        out.append(text[cursor:s.start])
        payload = text[s.start:s.end]
        findings.append(Finding(
            start=s.start, end=s.end, length=s.end - s.start, kind=s.kind,
            source=s.source, confidence=round(s.confidence, 3),
            sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16],
        ))
        out.append(_marker_for(s, typed) if typed else marker)
        cursor = s.end
    out.append(text[cursor:])
    return Result(original=text, cleaned="".join(out), stripped=findings)
