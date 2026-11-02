"""Rule-based injection detection: fast patterns that need no model.

Rules cover what is structurally visible: override phrases, tag/system forgeries,
exfiltration phrasing, encoded blobs, invisible-unicode smuggling and homoglyph
tricks. The model covers the paraphrases rules cannot name. Fictional test data
only; no network access here.
"""

from __future__ import annotations

import base64
import re
import unicodedata

from ..types import Span

KIND = {
    "override": "override",
    "impersonation": "impersonation",
    "exfil": "exfil",
    "forgery": "forgery",
    "encoding": "encoding",
    "smuggle": "smuggle",
    "spoof": "spoof",
}

# (name, kind, confidence, compiled regex)
_PATTERNS: list[tuple[str, str, float, re.Pattern[str]]] = []


def _p(name: str, kind: str, conf: float, pattern: str, flags: re.RegexFlag = re.IGNORECASE | re.MULTILINE) -> None:
    _PATTERNS.append((name, kind, conf, re.compile(pattern, flags)))


# --- override / instruction replacement -------------------------------------
_p("override-ignore", "override", 0.95,
   r"\b(?:ignore|disregard|forget|discard|override)\s+(?:all\s+|any\s+|the\s+|your\s+|their\s+|all\s+of\s+the\s+|any\s+of\s+the\s+|the\s+above\s+|your\s+prior\s+|"
   r"(?:all\s+)?(?:previous|prior|earlier|above|preceding)[\w\s]{0,20}?)?"
   r"(?:instructions?|prompts?|directions?|rules?|guidelines?|constraints?|context|message|messages|task)\b")
_p("override-replace", "override", 0.9,
   r"\b(?:from\s+now\s+on|henceforth|instead)\b[^.\n]{0,60}\b(?:you\s+(?:are|must|will|should|have\s+to)|your\s+(?:task|goal|job|instructions?))\b")
_p("override-newtask", "override", 0.85,
   r"\b(?:real|actual|new|updated|revised|true)\s+(?:task|instructions?|objective|goal|mission)\s*:")

# --- system / role impersonation ---------------------------------------------
_p("tag-system", "impersonation", 0.95, r"<\|?(?:im_start|im_end|system|endoftext|eot|assistant)\|?>")
_p("tag-metatag", "impersonation", 0.9, r"</?(?:system|assistant|instruction|instructions|tool_call|tool_result|function_call|function_response|request|context|memor(?:y|ies))\s*>")
_p("line-system", "impersonation", 0.8, r"^\s{0,8}(?:SYSTEM|SYSTEM PROMPT|INSTRUCTIONS?)\s*:")
_p("you-are-now", "impersonation", 0.9, r"\byou\s+are\s+now\s+(?:a|an|the)\b|\bact\s+as\s+(?:a|an|the)?\s*(?:different|new|unrestricted)\b")
_p("role-adopt", "impersonation", 0.75, r"^\s*assistant\s*:\s", re.IGNORECASE)
_p("dev-mode", "impersonation", 0.9, r"\b(?:developer\s+mode|dan\s+mode|do\s+anything\s+now|godmode|unrestricted\s+mode)\b")

# --- exfiltration / secret hunting --------------------------------------------
_p("exfil-send", "exfil", 0.9,
   r"\b(?:send|post|submit|upload|forward|exfiltrate|transmit)\b[^.\n]{0,120}?(?:https?://|ftp://|\b(?:curl|wget)\b|requests\.(?:post|get)|fetch\()")
_p("exfil-include", "exfil", 0.85,
   r"\b(?:include|append|add|embed|reveal|print|show|repeat|copy|quote)\b[^.\n]{0,80}?"
   r"\b(?:api[\s_-]?key|api[\s_-]?secret|password|passphrase|access[\s_-]?token|auth[\s_-]?token|private[\s_-]?key|credentials?|env(?:ironment)?[\s_-]?variables?|\.env)\b")
_p("secret-read", "exfil", 0.8,
   r"\b(?:read|dump|list|load|grep|search)\b[^.\n]{0,60}?\b(?:\.env|credentials?|secrets?|api[\s_-]?keys?|passwords?|tokens?)\b[^.\n]{0,80}?\b(?:and\s+)?(?:then\s+)?(?:send|post|share|include|reply|output|return|report)\b")

# --- forged structure ----------------------------------------------------------
_p("fake-tool-result", "forgery", 0.9,
   r"(?:TOOL_RESULT|FUNCTION_RESPONSE|EXECUTION_RESULT|TOOL_OUTPUT|SUCCESS_CONFIRMED)\s*[:({\[]")
_p("trusted-claim", "forgery", 0.9, r"[-_=*\s]*(?:BEGIN|END)[\s_-]+(?:TRUSTED|VERIFIED|SAFE|SYSTEM)[\s_-]+[-_=*\s]*", re.IGNORECASE)
_p("trusted-field", "spoof", 0.8, r"\"(?:status|trust_level|clearance|priority|importance|verified|safe)\"\s*:\s*\"(?:trusted|verified|safe|critical|internal|high|max)\"", re.IGNORECASE)
_p("note-to-assistant", "override", 0.85,
   r"\b(?:note|message|memo|warning|psa|notice)\s+(?:to|for)\s+(?:the\s+|any\s+|future\s+)?(?:assistant|ai|agent|model|llm|chatbot|bot|language\s+model|reader)\b")
_p("todo-ai", "override", 0.7, r"^\s*(?:TODO|FIXME|NOTE)\s*[\(\[]?\s*(?:for\s+)?(?:ai|assistant|agent|llm|bot)\b[\)\]]?\s*:", re.IGNORECASE)

# --- encoded payloads -----------------------------------------------------------
_B64 = re.compile(r"\b[A-Za-z0-9+/]{48,}={0,2}\b")
_HEX = re.compile(r"\b(?:[0-9a-fA-F]{2}){24,}\b")
_B64_KEYWORDS = re.compile(
    r"(?i)ignore|instruction|system|assistant|exfil|http|send|post|password|api|secret|curl|token|email|tool|agent")
_WORD = re.compile(r"[A-Za-z]{4,}")


def _b64_spans(text: str) -> list[Span]:
    out: list[Span] = []
    for m in _B64.finditer(text):
        blob = m.group(0)
        hit = False
        try:
            pad = blob + "=" * (-len(blob) % 4)
            decoded = base64.b64decode(pad, validate=True).decode("utf-8", "ignore")
            hit = len(_WORD.findall(decoded)) >= 3 or bool(_B64_KEYWORDS.search(decoded))
        except Exception:
            hit = False
        if hit:
            out.append(Span(m.start(), m.end(), "encoding", "rule:encoded-b64", confidence=0.95))
    return out


def _hex_spans(text: str) -> list[Span]:
    out: list[Span] = []
    for m in _HEX.finditer(text):
        try:
            decoded = bytes.fromhex(m.group(0)).decode("utf-8", "ignore")
        except Exception:
            continue
        if len(_WORD.findall(decoded)) >= 3:
            out.append(Span(m.start(), m.end(), "encoding", "rule:encoded-hex", confidence=0.95))
    return out


# --- invisible-unicode smuggling ------------------------------------------------
_INVISIBLE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\U000e0000-\U000e007f]+")


def _invisible_spans(text: str) -> list[Span]:
    out: list[Span] = []
    for m in _INVISIBLE.finditer(text):
        run = m.group(0)
        # A run of >=2 invisible controls is smuggling; a single one inside a word too.
        inside_word = 0 < m.start() and m.end() < len(text) and text[m.start() - 1].isalpha() and text[m.end()].isalpha()
        if len(run) >= 2 or inside_word:
            # Extend to the whole word when the invisible run sits inside it.
            s, e = m.start(), m.end()
            while s > 0 and (text[s - 1].isalnum() or text[s - 1] in "-_"):
                s -= 1
            while e < len(text) and (text[e].isalnum() or text[e] in "-_"):
                e += 1
            out.append(Span(s, e, "smuggle", "rule:invisible-unicode", confidence=0.9))
    return out


# --- homoglyph / mixed-script ----------------------------------------------------
def _script(ch: str) -> str:
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return "?"
    if "CYRILLIC" in name:
        return "cy"
    if "GREEK" in name:
        return "gr"
    if "LATIN" in name:
        return "la"
    return "?"


_HOMOGLYPH_LATIN = set("aeoxycAEPOXCBMKHTOP".lower() + "AEPOXCBMKH")


def _homoglyph_spans(text: str) -> list[Span]:
    out: list[Span] = []
    for m in re.finditer(r"[^\W\d_]+", text, re.UNICODE):
        w = m.group(0)
        scripts = {_script(c) for c in w} - {"?"}
        if len(scripts) > 1 and _script(w[0]) in {"la", "?"}:
            # Mixed Latin/Cyrillic/Greek word: classic impersonation trick.
            if any(_script(c) in {"cy", "gr"} for c in w):
                out.append(Span(m.start(), m.end(), "smuggle", "rule:homoglyph", confidence=0.85))
    return out


def detect_rules(text: str) -> list[Span]:
    """All rule hits for one text, no merging."""
    spans: list[Span] = []
    for name, kind, conf, rx in _PATTERNS:
        for m in rx.finditer(text):
            s = m.start()
            while s < m.end() and text[s] in "\n\r\t ":
                s += 1
            if s < m.end():
                spans.append(Span(s, m.end(), KIND[kind], f"rule:{name}", confidence=conf))
    spans += _b64_spans(text)
    spans += _hex_spans(text)
    spans += _invisible_spans(text)
    spans += _homoglyph_spans(text)
    return spans
