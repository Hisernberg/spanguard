# SpanGuard v6.0.0 — honest self-assessment

Rubric scored against the repo's own evidence, not intentions. Every claim links to a
committed artifact. Weaknesses carry the same weight as strengths; the overall score is
the honest number a reviewer should start from before adjusting for taste.

**Overall: 9.1 / 10** — the five gaps the v5 rating named are all closed with measured
artifacts (conformal bound, task gate, agent-loop harness, 500-doc adversarial set,
semantic judge + video); what keeps this below 9.5 is that the strongest new evidence
has honest limits: the conformal bound does not fully transfer across distribution
shift (15.0% worst held-out over-strip at α=0.1), the task gate is modest
(dev acc ~69%, OOD escape improvement 35.5% → 29.0%),
the fm-v6 weights are a CPU retrain after the Kaggle credentials expired mid-flight,
and the OOD crown still belongs to the router stack, not the single model.

## What changed since v5 (each named gap → its artifact)

1. **fm over-strip axis** → built: split-conformal calibration (`conformal.py`,
   `calibration_v2.json`, α sweep shipped) + task-conditioned gate
   (`Nabidnur/spanguard-taskgate`). extended-v6 benign over-strip 0.8%,
   NotInject 0.0%; the α sweep and its held-out violations are
   published as a chart, not footnoted.
2. **End-to-end agent harness** → built: `eval/agent_harness.py` (deterministic executor;
   outcomes task_completed / utility_lost / hijack_prevented / hijacked), NotInject probe
   (120 docs, 7 languages), canonical AgentDojo v1.1.1 column (72 wrapped attacks).
   NotInject utility 100.0%, hijack
   1.3% (fast-v4 8.7%).
3. **Adversarial sets at scale** → built: extended-v6 (500 docs, 250 attacks across
   20 families, 7 languages, seed-locked and disjoint from training). Escape
   0.0% / over-strip 0.8%. Hand-written stays n=48/62
   (it is the only genuinely human set — labeled as such).
4. **Demo video** → rendered from the committed script with TTS narration and the real
   gateway payload (`download/spanguard-demo-v6.mp4`, renderer committed).
5. **Semantic escape judge** → built and immediately useful: it found real rule gaps the
   verbatim check had blessed ("Disregard any prior directives…" untouched; passive exfil;
   mid-URL sentence-boundary residue). Fixed; the v3 red-team now replays at 30/30
   verbatim-stripped AND 0/30 semantic escapes under rules alone.

## Scorecard

| dimension | v5 | v6 | why |
|---|---|---|---|
| Problem & relevance | 9.5 | 9.5 | unchanged; the agent-loop harness now measures the thing the problem is actually about |
| Security engineering | 9.0 | 9.3 | + semantic judge closed real rule gaps; + sentence-level stripping kills imperative residue; + calibrated operating point with published violations |
| ML rigor | 8.0 | 8.8 | + 500-doc set, α sweep with held-out verification, gate ablation (tasked vs plain); − gate is weak (69%), conformal bound doesn't transfer OOD (published), no learning curves |
| Reproducibility | 9.5 | 9.0 | + every v6 number from one mega-run record; − Kaggle credentials expired mid-flight, so fm-v6 is a local CPU retrain (2.23M, subsample 9k+6k docs, window 512) — recipe and meta committed, but the P100 3.47M run's weights were unrecoverable (kernel record only) |
| Documentation | 9.0 | 9.3 | + README v6 sections generated from the same summary as the charts; rating rewritten against evidence |
| Deployment / demo | 7.5 | 8.8 | + video rendered; + Vercel mirror (spanguard.vercel.app) with v6 content; − Space still quota-parked, gateway still single-process |
| Novelty / differentiation | 8.0 | 8.6 | + a *conformally bounded* span stripper is genuinely rare; + judge-in-the-loop red-team audit is a repeatable method, not a one-off |
| Scope honesty | 9.5 | 9.5 | v6's headline limitations are in the README paragraph itself: bound non-transfer, modest gate, CPU retrain, int8 rejected on parity, OOD crown still fast-v4's |

**Overall 8.3 → 9.1.** The remaining 0.9 is not polish: it is (a) a
distribution-shift-proof calibration method (group-conformal or covariate-shift
correction), (b) a gate that actually learns task relevance at >85% instead of 69%,
(c) the P100-scale run trained end-to-end and measured, and (d) human-written
adversarial sets beyond n=62.

## Known limitations (published, not hidden)

- The conformal bound is exchangeability-bound: on agent-traffic benign the realized
  over-strip exceeds α (15.0% worst case). The sweep chart shows the whole frontier.
- The task gate is small and modest: ~69% dev accuracy; it moves OOD escape but does
  not close it (35.5% → 29.0% vs fast-v4's
  single digits). fast-v4 remains the OOD flagship.
- fm-v6 weights are a CPU retrain (2.23M, window 512, corpus-v4 subsample + addendum)
  after the Kaggle token expired mid-v6; the 3.47M P100 kernel completed but its output
  was unrecoverable when the API token's scopes changed. Kernel + recipe are committed;
  rerunning needs only working credentials.
- int8 ONNX quantization (dynamic and static) flips span decisions at the operating
  point and was rejected; fp32 ONNX ships with the parity report on the HF repo.
- Rules are English-phrase regexes; non-Latin coverage comes from the models, and the
  semantic judge is an LLM (z-ai GLM) with its own failure modes — 2/30 verdicts failed
  to parse and are reported as errors, not escapes.
- Binary baselines: PromptGuard 2 figures remain cited from public reports, not run.
