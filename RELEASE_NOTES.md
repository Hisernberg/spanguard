
## 5.0.0 — SPG-FM: one foundational model, the orchestration repair, both flagships shipped

- **SPG-FM-1** (1.70M params, one char-level multi-task network on the full corpus-v4
  union; https://huggingface.co/Nabidnur/spanguard-fm-1): **0.0% escape on every
  in-domain set, in all 7 languages** — agent-traffic 900 docs, extended-attacks 88 docs
  (all five 2026 families), extended-v4 108 docs — with doc F1 1.000 on both extended
  fixtures and the best payload localization in the family (span F1 0.917 / 0.901 vs
  0.689 / 0.612 for the router stack). Hand-written OOD 10.4% escape — the v2-era
  ensemble number, from a single 1.7M model, no router. Dev calibration: span
  precision 1.000 / recall 0.998, 0.19% escape, 0.0% over-strip (threshold 0.25).
  Trained in a committed Kaggle P100 kernel at ~12,000 docs/min.
- **The honest cost, published:** fm's document head over-fires on out-of-domain benign
  prose — 45.4% over-strip on the public probe, 26.4% on hand-written benign (router
  stack: 24.6% / 17.5%). Roadmap items B (task-conditioned stripping) and F (conformal
  calibration) attack exactly this axis. fm = coverage flagship, fast-v4 = fidelity
  flagship; both ship.
- **The orchestration repair** (surfaced by the sandbox restore, fixed and re-measured):
  `is_structured` rebuilt to the carrier taxonomy (k=v anywhere in line, tight CSV, tabs —
  log/CSV docs no longer fall down the prose channel and lose char hits); fast-v4
  union-everywhere restored (every doc routes to one of three experts — the v4.0.0
  behavior; the narrowed-trust variant leaked the polite social-engineering family);
  fm prose gating via its own doc head (≥0.5 → union). Result: fast-v4 hand-written OOD
  16.7% (v4 record) → 29.2% (broken restore) → **4.2%** (repaired, all-time best for the
  stack); extended-attacks 7.1% → **0.0%**. Broken intermediates committed
  (v5-fm-1504, v5-check-1514, v5-final-1519); release run `v5-ship-1548`.
- **Measured charts** (docs/assets/, script `scripts/make_charts_v5.py`, every number
  traced to a committed record): flagship bars, version ladder (OOD escape / public
  over-strip / span F1 across v1→v5), 7-language matrix, cost & latency.
- **Fresh latency** (2-thread sandbox CPU): fm p50 36.7 ms / p95 65.6 ms; fast-v4 p50
  14.6 ms / p95 41.6 ms.
- 26 tests green.

## 4.0.0 — domain foundation: 7 languages, one router stack, record on every extended set

- **corpus-v4**: 16,000 seed-locked docs, 7 languages (en/de/hu/fr/bn/ar/ja), 18 carrier
  families — new: log-file poisoning, code-comment injection, RAG-chunk poisoning +
  in-domain ar/ja templates. Generator + manifest committed.
- **char-v4** (812k, corpus-v4-trained; https://huggingface.co/Nabidnur/spanguard-char-v4):
  on the 108-doc extended-v4 fixture — 0.0% escape in all 7 languages, 0.0% over-strip,
  doc F1 1.000, span F1 0.955 (v3-era extended-attacks fixture: span F1 1.000).
  Washout it fixes: char-v3 ar 30.7% / ja 34.0% escape; span-v2 log-poison 76.2% /
  md-image 100% span miss.
- **fast-v4** (rules + span-v2 + 3-level char router): 5-set sweep 0.0% escape on
  agent-traffic, extended-attacks, extended-v4; doc F1 1.000 / 0.986 on the extended sets;
  honest trade — handwritten OOD 16.7% escape (char-v4 alone 0.0% but 44% over-strip).
- **baselines on the same fixture** (baselines-extended-v4/record.json): protectai
  deberta-v3-injection-v2 40.3% escape, horizon-small 6.9%, horizon-base 8.3%.
- **charts**: lang-matrix (washout → fix, measured post-v4 row) + v4-frontier
  (all bars on the identical fixture), light+dark SVGs, script reproducible.
- **visual-inference demo**: real fast-v4 runs — 15 cards incl. the new carriers and
  bn/ar/ja (docs/demo/visual-inference.html); interactive Gradio Space app staged in the
  Space repo (account cpu-basic quota currently parks it; static page live).
- **README**: world-class rewrite — headline table, per-language matrix, family evolution
  (v1→v5), live Space link, honest trades kept.
- 26 tests green; ruff clean.
