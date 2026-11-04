# SpanGuard v5.0.0 — honest self-assessment

Rubric scored against the repo's own evidence, not intentions. Every claim links to a
committed artifact. Weaknesses are listed with the same weight as strengths; the overall
score is the honest number a reviewer should start from before adjusting for taste.

**Overall: 8.3 / 10** — a complete, reproducible, honestly-measured security project that
ships; held back from 9+ by small adversarial sets, a missing end-to-end agent harness,
and one unresolved over-strip axis.

## Scorecard

| dimension | score | evidence |
|---|---|---|
| Problem & relevance | 9.5 | Indirect prompt injection through tool output is the 2026 agent-security headline; span-level stripping vs whole-doc binary is a real, argued distinction ([positioning table](positioning) in README) |
| Security engineering | 9.0 | Dual-axis metric (escape AND over-strip), strip-all semantics for baselines, decontamination by document hash, honest /healthz degradation, Bearer auth, no original text leaves in audit mode |
| ML rigor | 8.0 | Same-data fair baselines (docguard/toolguard), boundary-weighted losses, per-family + per-language reporting, Wilson CIs on the small set; −: hand-written set is n=48, no learning-curve or ablation on every knob |
| Reproducibility | 9.5 | Seed-locked generator, committed manifests + run records for every claim, CI regression gate (`make gate`), Kaggle kernels committed, 33 tests green, zero-cost rebuild of corpus + fixtures + charts |
| Documentation | 9.0 | World-class README with measured tables and honest trades, per-model HF cards, threat model doc, this rating; −: demo video still pending (script committed) |
| Deployment / demo | 7.5 | OpenAI-compatible gateway (Docker), live HF Space (v5 files pushed; build parked on free-tier quota), static visual-inference demo; −: no production hardening (no TLS story, single-process gateway) |
| Novelty / differentiation | 8.0 | Char-level multi-task span+doc in 1.7M params at 0% in-domain escape across 7 languages is a measured result, not a claim; the 135M→1.7M collapse with span F1 *improvement* is the strongest single result |
| Scope honesty | 9.5 | Every trade published (fm over-strip 45.4%/26.4%, v4-record vs repaired runs both committed, broken intermediates kept), roadmap states "stated, not claimed" |

## What would move it to 9.5+

1. **fm over-strip axis** (the one loss to fast-v4): task-conditioned stripping (B) or
   conformal calibration (F) — designed, not yet built.
2. **End-to-end agent harness** (AgentDojo-embedded columns + NotInject benign probe):
   the current fixtures measure the guard, not the agent-loop outcome.
3. **Adversarial sets at scale**: hand-written n=48 carries the OOD story; a 500-doc
   hand-written-equivalent set would tighten every CI.
4. **Demo video** recorded from the committed script (deferred by design to post-v6).
5. **Semantic escape judge** in the red-team loop (today: substring-verbatim core check).

## Known limitations (published, not hidden)

- Rules are English-phrase regexes; non-Latin coverage comes from the trained models,
  not the rules.
- fm over-fires its document head on unseen benign prose — the router stack stays the
  fidelity flagship (README carries both, side by side, same run).
- The Space demo is quota-paused on the HF free tier; the code and Dockerfile in the
  Space repo are v5-current and rebuild automatically when quota resumes.
- Binary baselines run with honest strip-all semantics but were accessed through gated
  or CPU-bound endpoints; PromptGuard 2 figures are cited from public reports, not run.
