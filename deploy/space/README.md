---
title: Spanguard
emoji: 🛡️
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: true
license: apache-2.0
short_description: Span-level prompt-injection guard for agent traffic
---

# Spanguard — live demo (v5)

Paste agent tool output (JSON, logs, tickets, MCP payloads, RAG chunks) and watch the
injection spans get stripped while the data survives. This Space runs the **real committed
v5 stack** on a free CPU bucket: validated rules + the 135M multilingual span model + the
3-level char router (`fast-v4`), with **SPG-FM-1** — the 1.7M single-model foundational
variant — pre-cached and one env switch away (`SPANGUARD_MODE=fm`).

Measured, committed, CI-gated (see the
[release notes](https://github.com/Hisernberg/spanguard/releases/tag/v5.0.0)):

- **0.0% escape** on agent traffic (900 docs) and both extended fixtures, in all 7
  languages (en/de/hu/fr/bn/ar/ja)
- hand-written OOD: **4.2%** (fast-v4) / 10.4% (SPG-FM-1 alone)
- latency p50: 14.6 ms (fast-v4) / 36.7 ms (SPG-FM-1) on CPU

- Gateway API: `POST /guard` (demo), `POST /v1/chat/completions` (OpenAI-compatible proxy)
- Health: `/healthz` — shows the detectors that actually loaded
- Source: https://github.com/Hisernberg/spanguard · Models: [`spanguard-fm-1`](https://huggingface.co/Nabidnur/spanguard-fm-1) and the family

**Fictional data only** — anything you paste is processed in this public Space, so do not
paste real secrets or personal data.
