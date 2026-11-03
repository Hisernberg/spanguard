"""Detector pipeline: rules / fast (rules+model) / fast-v2 (structure-aware
ensemble of rules + span model + char model) / audit (rules+model+LLM)."""

from __future__ import annotations

import re
import time

from ..types import Result
from . import rules as rules_mod
from .strip import strip_spans

_PROSE_HIGH_CONF = 0.85   # span-model confidence that stands alone on unstructured text
_PROSE_CHAR_BUMP = 0.1    # char-model threshold bump on unstructured text
_PROSE_SLACK = 25         # char/span corroboration tolerance (chars)
_STRUCTURED = re.compile(r"\{|\}|^\s*\w+=\S+|\s\|\s", re.MULTILINE)


def is_structured(text: str) -> bool:
    """Tool-output-ish (JSON braces, k=v, pipe tables) vs prose (web pages,
    user prompts). The two channels need different precision/recall tradeoffs."""
    return bool(_STRUCTURED.search(text))


class Guard:
    """One guard instance; mode selects detectors, one shared SpanModel."""

    def __init__(self, mode: str = "fast", model_id: str | None = None, threshold: float = 0.5,
                 typed_markers: bool = True):
        if mode not in {"rules", "fast", "fast-v2", "fast-v3", "fast-v4", "audit"}:
            raise ValueError(f"unknown mode {mode!r}")
        self.mode = mode
        self.threshold = threshold
        self.typed_markers = typed_markers
        self._model = None
        self._char = None
        self.model_id = model_id
        self.last_latency_ms: float | None = None
        # honest degradation tracking: what the caller asked for vs what actually loaded
        self.degraded: list[str] = []
        self._model_ok = False
        self._char_ok = False

    @property
    def model(self):
        if self._model is None:
            from .model import SpanModel

            self._model = SpanModel(self.model_id)
        return self._model

    @property
    def char_model(self):
        if self._char is None:
            from .char_guard import char_spans

            self._char = char_spans
        return self._char

    def guard(self, text: str) -> Result:
        t0 = time.monotonic()
        spans = rules_mod.detect_rules(text)
        model_spans_kept: list = []
        if self.mode in {"fast", "fast-v2", "fast-v3", "fast-v4", "audit"}:
            try:
                model_spans = self.model.spans(text, threshold=self.threshold)
                if self.mode in {"fast-v2", "fast-v3", "fast-v4"} and not is_structured(text):
                    model_spans = [s for s in model_spans if s.confidence >= _PROSE_HIGH_CONF]
                if self.mode in {"fast-v2", "fast-v3", "fast-v4"}:
                    model_spans_kept = model_spans  # ensemble decides below
                else:
                    spans += model_spans
            except ImportError:
                if "model:torch-not-installed" not in self.degraded:
                    self.degraded.append("model:torch-not-installed")  # visible in /healthz
        if self.mode in {"fast-v2", "fast-v3", "fast-v4"}:
            try:
                thr = self.char_threshold(text)
                if self.mode == "fast-v3":
                    from .router import routed_char_spans
                    char_spans, _, _route = routed_char_spans(text, threshold=thr)
                elif self.mode == "fast-v4":
                    from .router import routed_char_spans_v4
                    char_spans, _, _route = routed_char_spans_v4(text, threshold=thr)
                else:
                    char_spans, _ = self.char_model(text, threshold=thr)
                self._char_ok = True
                prose = not is_structured(text)
                if self.mode in {"fast-v3", "fast-v4"}:
                    from .router import is_extended_domain, route_v4
                    routed = (is_extended_domain(text) if self.mode == "fast-v3"
                              else route_v4(text) in {"v3", "v4"})
                    if routed:
                        prose = False  # routed docs trust the in-domain char model (union)
                if prose:
                    # Corroboration channel: on prose (web pages, user prompts) both
                    # neural detectors false-positive more, so a finding survives
                    # only when the other detector backs it, a rule backs it, or it
                    # is long (>=60 chars — never benign filler).
                    for s in model_spans_kept:
                        if any(sa < s.end + _PROSE_SLACK and s.start - _PROSE_SLACK < sb
                               for sa, sb in char_spans):
                            spans.append(s)
                    for a, b in char_spans:
                        backed = any(x.start < b + _PROSE_SLACK and a - _PROSE_SLACK < x.end
                                     for x in spans)
                        if (backed or b - a >= 60) and not any(
                                x.start < b and a < x.end for x in spans):
                            spans.append(_mk_span(text, a, b))
                else:
                    # Structured channel (home domain): union — recall dominates.
                    spans += model_spans_kept
                    for a, b in char_spans:
                        if not any(x.start < b and a < x.end for x in spans):
                            spans.append(_mk_span(text, a, b))
            except (ImportError, FileNotFoundError, OSError) as exc:
                tag = f"char:{type(exc).__name__}"
                if tag not in self.degraded:
                    self.degraded.append(tag)
                spans += model_spans_kept  # char unavailable: keep the span model
        result = strip_spans(text, spans, typed=self.typed_markers)
        if self.mode == "audit":
            from .audit import AuditDetector, audit_spans

            audit = AuditDetector()
            verdict = audit.audit(result.cleaned)
            extra = audit_spans(result.cleaned, verdict)
            if extra:
                result = strip_spans(text, spans + _shift(result, extra), typed=self.typed_markers)
        self.last_latency_ms = round((time.monotonic() - t0) * 1000, 1)
        return result

    def char_threshold(self, text: str) -> float | None:
        """Calibrated char threshold, bumped up on prose to protect over-strip.
        fast-v3 reads the ROUTED model's calibration (v3 models calibrate lower)."""
        try:
            import os

            from .char_guard import _load

            if self.mode == "fast-v3":
                from .router import is_extended_domain

                dir_path = (os.environ.get("SPANGUARD_CHAR_MODEL_V3")
                            if is_extended_domain(text) else os.environ.get("SPANGUARD_CHAR_MODEL"))
            elif self.mode == "fast-v4":
                from .router import route_v4

                dir_path = os.environ.get(f"SPANGUARD_CHAR_MODEL_{route_v4(text).upper()}")                     or os.environ.get("SPANGUARD_CHAR_MODEL")
            else:
                dir_path = None
            _, _, calib = _load(dir_path)
            base = calib.get("threshold", 0.5)
            if self.mode in {"fast-v3", "fast-v4"}:
                from .router import is_extended_domain, route_v4
                # prose bump protects against neural FPs on out-of-domain prose;
                # routed (in-domain) docs use the routed model's own calibration
                routed = (is_extended_domain(text) if self.mode == "fast-v3"
                          else route_v4(text) in {"v3", "v4"})
                bump = 0.0 if routed else (_PROSE_CHAR_BUMP if not is_structured(text) else 0.0)
                return base + bump
            return base + (_PROSE_CHAR_BUMP if not is_structured(text) else 0.0)
        except (ImportError, FileNotFoundError, OSError):
            return None

    def detectors(self) -> list[str]:
        """Detectors that ACTUALLY loaded — not what the mode asks for.

        If torch is missing or a model file is absent, the detector is absent
        here and ``degraded`` says why. This is the number /healthz serves, so
        a silent rules-only downgrade is always visible to the operator.
        """
        d = ["rules"]
        if self.mode in {"fast", "fast-v2", "audit"} and self._model_ok:
            d.append("model")
        if self.mode in {"fast-v2", "fast-v3", "fast-v4"} and self._char_ok:
            d.append("char" if self.mode == "fast-v2"
                     else "char-router(v2+v3)" if self.mode == "fast-v3" else "char-router(v2+v3+v4)")
        if self.mode == "audit" and self._model_ok:
            d.append("audit")
        return d


def _mk_span(text: str, a: int, b: int):
    from ..types import Span

    return Span(start=a, end=b, kind="char-span", source="model:char", confidence=0.6)


def _shift(first_result: Result, spans: list):
    """Audit spans are offsets into cleaned text; map back to original offsets."""
    # Positions before the first marker are identical; markers only add length, so
    # audit span starts map 1:1 until the first marker. Conservative mapping:
    first_marker = first_result.cleaned.find("[stripped")
    out = []
    for s in spans:
        if first_marker == -1 or s.start < first_marker:
            out.append(s)
    return out
