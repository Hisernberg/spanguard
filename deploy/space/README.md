---
title: Spanguard
emoji: 🛡️
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: true
license: apache-2.0
short_description: Span-level prompt-injection guard for AI agent tool traffic
---

# Spanguard — live demo

Paste agent tool output (JSON, logs, tickets) and watch the injection spans get stripped
while the data survives. Rules + a 135M multilingual span model, on CPU.

- Gateway API: `POST /guard` (demo), `POST /v1/chat/completions` (OpenAI-compatible proxy)
- Health: `/healthz`
- Source: https://github.com/Hisernberg/spanguard

**Fictional data only** — anything you paste is processed in this public Space, so do not
paste real secrets or personal data.
