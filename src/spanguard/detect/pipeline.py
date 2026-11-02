"""Detector pipeline: rules / fast (rules+model) / audit (rules+model+LLM)."""

from __future__ import annotations

import time

from ..types import Result
from . import rules as rules_mod
from .strip import strip_spans


class Guard:
    """One guard instance; mode selects detectors, one shared SpanModel."""

    def __init__(self, mode: str = "fast", model_id: str | None = None, threshold: float = 0.5):
        if mode not in {"rules", "fast", "audit"}:
            raise ValueError(f"unknown mode {mode!r}")
        self.mode = mode
        self.threshold = threshold
        self._model = None
        self.model_id = model_id
        self.last_latency_ms: float | None = None

    @property
    def model(self):
        if self._model is None:
            from .model import SpanModel  # noqa: PLC0415 - optional dependency

            self._model = SpanModel(self.model_id)
        return self._model

    def guard(self, text: str) -> Result:
        t0 = time.monotonic()
        spans = rules_mod.detect_rules(text)
        if self.mode in {"fast", "audit"}:
            try:
                spans += self.model.spans(text, threshold=self.threshold)
            except ImportError:
                pass  # model extra not installed: rules still ran
        result = strip_spans(text, spans)
        if self.mode == "audit":
            from .audit import AuditDetector, audit_spans  # noqa: PLC0415 - lazy

            audit = AuditDetector()
            verdict = audit.audit(result.cleaned)
            extra = audit_spans(result.cleaned, verdict)
            if extra:
                result = strip_spans(text, spans + _shift(result, extra))
        self.last_latency_ms = round((time.monotonic() - t0) * 1000, 1)
        return result

    def detectors(self) -> list[str]:
        d = ["rules"]
        if self.mode in {"fast", "audit"}:
            d.append("model")
        if self.mode == "audit":
            d.append("audit")
        return d


def _shift(first_result: Result, spans: list):
    """Audit spans are offsets into cleaned text; map back to original offsets."""
    # Positions before the first marker are identical; markers only add length, so
    # audit span starts map 1:1 until the first marker. Conservative mapping:
    first_marker = first_result.cleaned.find("[stripped]")
    out = []
    for s in spans:
        if first_marker == -1 or s.start < first_marker:
            out.append(s)
    return out
