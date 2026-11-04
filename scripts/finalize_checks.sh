#!/usr/bin/env bash
# Post-chain4 finalize: verify records, finalize answers, release, push, sync download/.
set -uo pipefail
cd /home/z/my-project/spanguard
echo "== records present?"
ls eval/results/ | tail -8
python3 - <<'EOF'
import json
from pathlib import Path
tags = {}
for f in sorted(Path("eval/results").glob("*/run.json")):
    d = json.loads(f.read_text())
    for tag in d.get("systems", {}):
        tags.setdefault(tag, f.parent.name)
print("system tags:", sorted(tags))
need = {"spanguard-rules", "spanguard-fast", "spanguard-audit", "llm-self-detect",
        "protectai-deberta-v2", "horizon-small", "horizon-base",
        "spanguard-docguard", "spanguard-toolguard"}
print("MISSING:", sorted(need - set(tags)) or "none")
EOF
echo "== gate"
python3 -m spanguard.eval.gate | tail -1
echo "== submission answers pending columns"
grep -n "pending" docs/submission-answers.md | head -4
echo "== FINALIZE-CHECKS-DONE (remaining steps need real numbers: intro_alternative wording, answers fill, release)"
