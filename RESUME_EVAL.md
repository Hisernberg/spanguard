# SpanGuard — v3.0.0 shipped (2026-11-03 ~04:00 UTC)

## DONE & PUSHED (main) — release v3.0.0 published
- External-review hardening: teacher truth ($3.91 ran once, union==planted), real latency
  numbers, Wilson CIs, SPEC fixes (135M/21 tests/18 rules/PG2-gated-403), public-deepset
  reframed as benign-only over-strip probe, 2026 positioning table + roadmap.
- Engineering: tool-def scanning + rug-pull pins (C), typed markers (G), honest /healthz
  degradation, async httpx, Bearer default, /guard auth, build_public verify shim,
  ruff 0 errors, 21 tests green.
- Corpus v3 (MCP poisoning/skill files/buried multi-hop/md-image exfil/polite SE/+bn,
  14k docs, 16 families) → char-v3 trained + published (extended-domain 0.4% escape /
  spanF1 0.996 vs char-v2 11.6%/0.467; old-OOD regression 4.2→12.5% published).
- v2-model (135M boundary-weighted) published; public over-strip 34.2→18.1.
- Adaptive red-team: 25 mutations / 0 escapes / 30 attempts, record committed.
- Release: https://github.com/Hisernberg/spanguard/releases/tag/v3.0.0

## Remaining (if a next round happens)
1. fast-v2 ensemble with char-v3 (per-domain routing claim is roadmap, not built).
2. PromptGuard 2 head-to-head needs license acceptance on HF web UI (403 today).
3. NotInject + AgentDojo-embedded standard columns (roadmap in README).
4. Demo Space precomputed outputs still use plain [stripped] markers — rebuild
   scripts/build_demo.py run would refresh them.
5. Review claimed "span P/R 0.46 for fast" — visible in records; a span-metrics chart
   could make that first-class.

## Tokens: /home/z/my-project/.secrets/env (GH / KAGGLE / HF). Kaggle CLI 2.2.5 quirks:
kernel metadata key is `dataset_sources`; uploads need KAGGLE_API_TOKEN env.
