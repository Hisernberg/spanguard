"""Domain router (v3): pick the right char model per document type.

The corpus-v3 retrain bought new-domain coverage (MCP/skill/buried/md-image/
polite: 0.4% escape) at the cost of old-domain sharpness (hand-written OOD
4.2% -> 12.5%). Shipping both models and routing by document type gets the
best of both: extended-domain carriers go to char-v3, everything else keeps
the original char model. The router itself is rules on the *carrier shape*
(JSON tool defs, markdown skill files, note-with-quote pages, markdown
images) — cheap, deterministic, auditable.
"""

from __future__ import annotations

import json
import re

_EXT_HINTS = re.compile(
    r"(?:\"tool\"\s*:|inputSchema|mcp://|\"instructions\"\s*:|# Skill:|## Steps|"
    r"Whiteboard section kept verbatim|!\[[^\]]*\]\(https?://|Cleanup reminder filed)",
)
_BENGALI = re.compile(r"[\u0980-\u09FF]")


def is_extended_domain(text: str) -> bool:
    """True when the document's CARRIER is one of the v3 domain types, or the
    text is in Bangla (only char-v3 ever saw bn training data — v2 models are
    bn-blind, and the red-team demo caught exactly that escape)."""
    if _EXT_HINTS.search(text):
        return True
    if _BENGALI.search(text):
        return True
    # MCP tool-def JSON: any compact object naming a tool + description
    if text.lstrip().startswith("{") and '"name"' in text and ('"description"' in text or '"instructions"' in text):
        return True
    return False


def routed_char_model(text: str, char_v2_dir: str | None, char_v3_dir: str | None) -> str | None:
    if is_extended_domain(text):
        return char_v3_dir or char_v2_dir
    return char_v2_dir


def routed_char_spans(text: str, threshold: float | None = None):
    """char_spans with the domain router applied. Model dirs come from env:
    SPANGUARD_CHAR_MODEL (v2) and SPANGUARD_CHAR_MODEL_V3."""
    import os

    from .char_guard import char_spans

    v2 = os.environ.get("SPANGUARD_CHAR_MODEL")
    v3 = os.environ.get("SPANGUARD_CHAR_MODEL_V3")
    model = routed_char_model(text, v2, v3)
    spans, doc_p = char_spans(text, dir_path=model, threshold=threshold)
    source = "spanguard-char-router:" + ("v3" if model == v3 and v3 else "v2")
    return spans, doc_p, source


def router_stats() -> dict:
    """For /healthz and run records: which models the router can reach."""
    import os

    return {
        "char_v2": os.environ.get("SPANGUARD_CHAR_MODEL") or "default",
        "char_v3": os.environ.get("SPANGUARD_CHAR_MODEL_V3") or "unset",
        "strategy": "carrier-shape rules (mcp-json | skill-md | notes-quote | md-image) + bangla script",
    }


_ = json  # keep import for downstream record helpers
