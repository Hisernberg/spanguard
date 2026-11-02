#!/usr/bin/env bash
# Create the v1.0.0 GitHub release with measured-numbers notes.
set -euo pipefail
source /home/z/my-project/.secrets/env
: "${GH_TOKEN:?}"
REPO=Hisernberg/spanguard
TAG=v1.0.0

BODY=$(cat <<'MD'
## SpanGuard v1.0.0 — submission release

A span-level prompt-injection guard for AI agent tool traffic: strip the attack, keep the data.

### What ships

- `spanguard` pip package: rules engine (21 patterns) · 135M span model (BIO tagger) · audit mode · OpenAI-compatible gateway (`/v1/chat/completions` proxy + `/guard`)
- Three published models, all trained locally on CPU from one deterministic fictional corpus (en/de/hu):
  - [spanguard-span-mdistil](https://huggingface.co/Nabidnur/spanguard-span-mdistil) — surgical span stripping
  - [spanguard-docguard-mdistil](https://huggingface.co/Nabidnur/spanguard-docguard-mdistil) — the one-bit baseline, trained on the same data for a fair fight
  - [spanguard-toolguard-mdistil](https://huggingface.co/Nabidnur/spanguard-toolguard-mdistil) — tool-call argument guard
- Committed run records + SVG charts + CI regression gate (`make gate`)
- Static demo Space: https://huggingface.co/spaces/Nabidnur/spanguard-demo

### Headline numbers (escape % · over-strip %)

| Set | spanguard fast | rules-only |
|---|---|---|
| Hand-written attacks (62, en/de/hu) | **29.2 · 12.3** | 75.0 · 7.5 |
| Agent traffic (900, synthetic) | **0.0 · 3.3** | 13.4 · 3.3 |
| Public prompts (452, deepset) | 0.0 · 34.2 | 0.0 · 0.1 |

Tool-call surface (400 held-out calls): toolguard blocks 100% of attacks with **0.0% false-blocks**; the doc-level model on the same calls false-blocks **39.0%**.

### Honesty

- Fictional data only; every number is a committed, re-runnable record (`eval/results/`, `docs/REPRODUCE.md`).
- Escape **and** over-stripping are reported together everywhere — a guard that deletes everything escapes 0%.
- The teacher-LLM path ships as optional tooling; committed labels are deterministic planted spans. No unrun inference is claimed.
- Per-family heatmaps show which families leak for which system — including ours.

Apache-2.0. Solo project for the Meta Global AI Hackathon 2026 — Indie track.
MD
)

curl -sS -X POST \
  -H "Authorization: token ${GH_TOKEN}" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO}/releases" \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"tag_name": sys.argv[1], "target_commitish": "main", "name": "SpanGuard v1.0.0", "body": sys.argv[2], "draft": False, "prerelease": False}))' "$TAG" "$BODY")" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('release:', d.get('html_url') or d)"
