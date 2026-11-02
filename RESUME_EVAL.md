# SpanGuard — STATUS: SUBMISSION COMPLETE (2026-11-02 ~18:30 UTC)

Everything below is DONE, verified, and pushed to GitHub (main @ 52124f2):

- 3 models on HF: Nabidnur/spanguard-{span,docguard,toolguard}-mdistil (pull via snapshot_download)
- COMPLETE benchmark table (9 systems × 3 sets) in README, every cell from a committed record:
  spanguard fast 29.2%·11.3% handwritten (Pareto-optimal), 0.0%·3.3% agent-traffic;
  rules-only, protectai, horizon x2 (binary strip-all), Qwen2.5-0.5B self-detect (482 verdicts),
  docguard vs toolguard (39.0% vs 0.0% false-block, p50 57.5/45.5 ms)
- pytest 14/14 · make gate OK (generated_at-based newest-record selection)
- README: world-class structure (30-sec Demo section, model family, honest limits, citation,
  per-language notes), all blocks auto-rendered from records via `python3 -m spanguard report`
- Release v1.0.0 live: https://github.com/Hisernberg/spanguard/releases/tag/v1.0.0
- Demo Space live: https://huggingface.co/spaces/Nabidnur/spanguard-demo
- docs/submission-answers.md finalized (real numbers, no pending cells)

Only optional leftovers (none block submission):
- 3-min video must be recorded separately (script: docs/demo-video-script.md)
- If the sandbox recycles again: standard recovery is token restore → clone → deps →
  HF model pull (all committed in this repo's scripts/ and REPRODUCE.md)

Tokens: GH_TOKEN + HF_TOKEN in /home/z/my-project/.secrets/env (GH one ends 8shq, works).
Baseten/Meta key: gone; audit mode + teacher path degrade gracefully without it.
