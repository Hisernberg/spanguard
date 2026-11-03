"""Tool-definition scanning (idea C): the `tools` array / MCP tool descriptions
are an injection surface too (MCPTox measured 36.5% average tool-poisoning
success across 45 live servers). This module scans tool *definitions* — not
message content — and detects description changes (rug-pulls) against a pin
file. Stateless except for the optional pin file the operator controls.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .rules import detect_rules

_SUSPICIOUS = re.compile(
    r"(?:exfiltrat|send.{0,24}(?:to|the)\s+(?:api|webhook|attacker|attacker\.|http)|"
    r"ignore\s+all\s+previous|base64|before\s+(?:any|each)\s+(?:use|call)|"
    r"do\s+not\s+(?:tell|inform|reveal)|secretly|without\s+the\s+user|"
    r"email\s+the\s+credentials|post\s+the\s+(?:contents|conversation))",
    re.IGNORECASE,
)


def _iter_defs(body: dict):
    """Yield (where, name, description) for OpenAI-style tools and MCP servers."""
    for i, t in enumerate(body.get("tools") or []):
        if not isinstance(t, dict):
            continue
        fn = t.get("function") or (t if t.get("name") else None)
        if isinstance(fn, dict):
            yield f"tools[{i}]", str(fn.get("name", "?")), str(fn.get("description") or "")
    for i, srv in enumerate(body.get("mcp_servers") or []):
        if isinstance(srv, dict):
            yield f"mcp_servers[{i}]", str(srv.get("name", "?")), str(srv.get("description") or "")


def _desc_hash(name: str, description: str) -> str:
    return hashlib.sha256(f"{name}\n{description}".encode()).hexdigest()[:16]


def scan_tool_defs(body: dict, pin_file: str = "") -> list[dict]:
    """Findings across the request's tool definitions. Each finding:
    {where, tool, kind: rule|heuristic|rug-pull, rule, source_hash, pinned_hash}."""
    findings: list[dict] = []
    pins: dict = {}
    if pin_file and Path(pin_file).exists():
        try:
            pins = json.loads(Path(pin_file).read_text())
        except (json.JSONDecodeError, OSError):
            pins = {}
    for where, name, desc in _iter_defs(body):
        for span in detect_rules(desc):
            findings.append({"where": where, "tool": name, "kind": "rule", "rule": span.rule,
                             "source_hash": _desc_hash(name, desc), "pinned_hash": pins.get(name)})
        if _SUSPICIOUS.search(desc) and not any(f["where"] == where and f["kind"] == "rule" for f in findings):
            findings.append({"where": where, "tool": name, "kind": "heuristic", "rule": "tool-desc-pattern",
                             "source_hash": _desc_hash(name, desc), "pinned_hash": pins.get(name)})
        if name in pins and pins[name] != _desc_hash(name, desc):
            findings.append({"where": where, "tool": name, "kind": "rug-pull", "rule": "description-changed",
                             "source_hash": _desc_hash(name, desc), "pinned_hash": pins[name]})
    return findings


def write_pins(body: dict, pin_file: str) -> int:
    """Pin every tool description's hash; returns count written. Operators run
    this once over a trusted tool manifest, then the gateway flags any change."""
    pins: dict = {}
    if Path(pin_file).exists():
        try:
            pins = json.loads(Path(pin_file).read_text())
        except (json.JSONDecodeError, OSError):
            pins = {}
    n = 0
    for _where, name, desc in _iter_defs(body):
        pins[name] = _desc_hash(name, desc)
        n += 1
    Path(pin_file).write_text(json.dumps(pins, indent=1, sort_keys=True))
    return n
