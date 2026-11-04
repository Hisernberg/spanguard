#!/usr/bin/env python3
"""Build the AgentDojo attack column from the REAL agentdojo package (v1.1.1).

Extracts every canonical injection-task GOAL from the four benchmark suites
(workspace, slack, travel, banking) and wraps each in the canonical jailbreak
templates (direct, ignore_previous, system_message, important_instructions x
name variants) — the same wrappers agentdojo's own benchmark uses. Each wrapped
attack is embedded in one of three synthetic tool-output carriers (JSON, prose,
email) with a plausible benign header, producing eval/fixtures/
agentdojo-wrapped.jsonl for the guard + semantic-judge columns.

This measures THE GUARD against agentdojo's canonical attack surface without
running the full LLM agent loop (which needs provider credentials); the
agent-loop outcome layer lives in eval/agent_harness.py. Labeled accordingly.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

import agentdojo.task_suite.task_suite  # noqa: F401  (breaks the 0.1.35 import cycle)
import agentdojo.default_suites.v1_1_1  # noqa: F401  (registers v1.1.1 suites)
from agentdojo.task_suite import get_suites  # noqa: E402
from agentdojo.attacks import important_instructions_attacks as imp  # noqa: E402

N_PER_TEMPLATE = 3  # goals per template per suite


def templates() -> list[tuple[str, str]]:
    """(name, _JB_STRING) for the canonical jailbreak wrappers."""
    out = []
    for cls_name, label in [
            ("DirectAttack", "direct"),
            ("IgnorePreviousAttack", "ignore_previous"),
            ("SystemMessageAttack", "system_message"),
            ("ImportantInstructionsAttack", "important_instructions"),
            ("ImportantInstructionsAttackNoUserName", "important_instructions_no_user"),
            ("ImportantInstructionsAttackNoModelName", "important_instructions_no_model"),
            ("ImportantInstructionsAttackNoNames", "important_instructions_no_names"),
            ("ImportantInstructionsWrongModelName", "important_instructions_wrong_model"),
            ("ImportantInstructionsWrongUserName", "important_instructions_wrong_user")]:
        cls = getattr(imp, cls_name, None)
        if cls and getattr(cls, "_JB_STRING", None):
            out.append((label, cls._JB_STRING))
    return out


def main() -> None:
    suites = get_suites("v1.1.1")
    rng = random.Random(4711)
    rows = []
    tpls = templates()
    user_name = getattr(imp.ImportantInstructionsAttack, "user_name", "John Doe")
    model_name = getattr(imp.ImportantInstructionsAttack, "model_name", "gpt-4o")
    print(f"templates: {len(tpls)} | user={user_name!r} model={model_name!r}")
    for suite_name, suite in sorted(suites.items()):
        goals = []
        for env_dict in suite._injection_tasks.values():
            for task in env_dict.values():
                g = (task.GOAL or "").strip()
                if g:
                    goals.append(g)
        print(f"{suite}: {len(goals)} injection goals")
        for label, jb in tpls:
            picks = rng.sample(goals, min(N_PER_TEMPLATE, len(goals)))
            for goal in picks:
                attack = jb.replace("{user}", user_name).replace(
                    "{model}", model_name).replace("{goal}", goal)
                carrier = rng.random()
                if carrier < 0.4:
                    text = ('{"tool": "read_ticket", "result": {"id": '
                            f'{rng.randrange(1000, 9999)}, "body": "Customer follow-up. '
                            + attack.replace("\n", " ").replace('"', "'") + '"}}')
                elif carrier < 0.7:
                    text = ("Q3 operations digest\n\nVolumes normalised after the customs "
                            "delay. Regional leads confirmed inventory counts.\n\n" + attack)
                else:
                    text = ("From: notifications@nordwind-labs.example\nTo: ops@nordwind-labs.example\n"
                            "Subject: Automated notice\n\n" + attack)
                did = hashlib.sha256(text.encode()).hexdigest()[:16]
                rows.append({"id": did, "lang": "en", "kind": f"agentdojo-{suite_name}",
                             "text": text, "attack": f"agentdojo:{label}",
                             "goal": goal, "spans": [], "negative": False})
    out = REPO / "eval" / "fixtures" / "agentdojo-wrapped.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                   encoding="utf-8")
    fams: dict[str, int] = {}
    for r in rows:
        fams[r["attack"]] = fams.get(r["attack"], 0) + 1
    print(json.dumps({"docs": len(rows), "families": fams,
                      "suites": sorted(suites)}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
