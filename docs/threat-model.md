# Threat model

## What spanguard defends

An **AI agent** that consumes **tool output** it did not author: HTTP API responses, MCP tool
results, fetched web pages, retrieved documents, logs, tickets, exports. An attacker who can
plant text in any of those channels (a support ticket, a product note, a web page, a calendar
field) can speak to the agent directly. This is *indirect prompt injection* — the top failure
mode of tool-using agents.

## The mechanism

1. Every `tool`-role message (and, by configuration, system/user messages) is scanned by
   validated rules and a 135M BIO span tagger.
2. Merged attack spans are replaced by `[stripped]` markers; the findings (offsets, kind,
   confidence, payload **hash** — never the payload) go to the local audit log.
3. The cleaned text is what the agent reads. `audit` mode additionally sends the *stripped*
   text to Muse Spark Open and asks "is any attack instruction still standing?" — the original
   text never leaves the box in any mode.

## Honest limits

- Span stripping is lossy for the attacker but not guaranteed: paraphrases outside the
  training distribution and the teacher's imagination can pass. The per-family heatmap in the
  benchmark section is the honest scoreboard, including our leaks.
- `[stripped]` markers are data loss by design; a too-aggressive guard degrades the agent's
  task. That trade is the over-stripping axis, and we publish it next to escape rate.
- No defense against a compromised upstream provider, a compromised host, or attacks embedded
  in images (future work: SAM 3.1 for text-in-screenshot localization).
- Not legal advice, not a compliance certification, not a sandbox.
