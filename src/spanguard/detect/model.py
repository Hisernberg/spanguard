"""Fine-tuned span model (XLM-RoBERTa token classification, BIO: O / B-INJ / I-INJ).

Optional extra: ``pip install spanguard[model]``. Everything else in Spanguard runs
without torch; the gateway falls back to rules-only when the model is absent.
"""

from __future__ import annotations

import os

from ..types import Span

DEFAULT_MODEL_ID = "Nabidnur/spanguard-span-xlmr-base"
LABELS = ["O", "B-INJ", "I-INJ"]
MAX_TOKENS = 512
STRIDE = 64


class SpanModel:
    """Sliding-window BIO tagger over character offsets."""

    def __init__(self, model_id: str | None = None, device: str = "auto", max_chars: int = 12000):
        import torch  # noqa: PLC0415 - optional dependency
        from transformers import AutoModelForTokenClassification, AutoTokenizer  # noqa: PLC0415

        self._torch = torch
        model_id = model_id or os.environ.get("SPANGUARD_MODEL", DEFAULT_MODEL_ID)
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForTokenClassification.from_pretrained(model_id)
        self.model.eval()
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.model.to(device)
        self.max_chars = max_chars

    def spans(self, text: str, threshold: float = 0.5) -> list[Span]:
        text = text[: self.max_chars]
        tok = self.tokenizer
        enc = tok(
            text,
            return_offsets_mapping=True,
            truncation=True,
            max_length=MAX_TOKENS,
            stride=STRIDE,
            return_overflowing_tokens=True,
            padding="max_length",  # overflow windows are uneven; the last one would break tensor stacking
            return_tensors="pt",
        )
        offsets = enc.pop("offset_mapping")
        enc.pop("overflow_to_sample_mapping", None)
        spans: list[Span] = []
        with self._torch.no_grad():
            logits = self.model(**{k: v.to(self.device) for k, v in enc.items()}).logits
            probs = logits.softmax(-1)
        for w in range(probs.shape[0]):
            pred = probs[w].argmax(-1)
            conf = probs[w].max(-1).values
            cur: tuple[int, int, float] | None = None
            for i, (s, e) in enumerate(offsets[w].tolist()):
                if e <= s:  # special token
                    if cur:
                        spans.append(self._span(text, *cur))
                        cur = None
                    continue
                label = LABELS[int(pred[i])]
                if label == "B-INJ":
                    if cur:
                        spans.append(self._span(text, *cur))
                    cur = (s, e, float(conf[i]))
                elif label == "I-INJ" and cur:
                    cur = (cur[0], e, max(cur[2], float(conf[i])))
                else:
                    if cur:
                        spans.append(self._span(text, *cur))
                    cur = None
            if cur:
                spans.append(self._span(text, *cur))
        return [s for s in spans if s.confidence >= threshold]

    @staticmethod
    def _span(text: str, start: int, end: int, conf: float) -> Span:
        # Trim whitespace and stretch to whole words so the strip does not leave fragments.
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        while end < len(text) and text[end].isalnum():
            end += 1
        while start > 0 and text[start - 1].isalnum():
            start -= 1
        return Span(start, end, "override", "model", confidence=round(conf, 3))
