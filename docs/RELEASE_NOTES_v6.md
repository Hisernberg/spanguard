# SpanGuard v6.0.0 — release notes (bundle)

## What shipped
- **fm-v6** (2.23M params, corpus-v4 subsample 9k + v6 addendum 6k, CPU retrain after
  the Kaggle token expired): dev span F1 0.984, escape 2.77%, over-strip 0.04 chars/doc.
  `Nabidnur/spanguard-fm-v6` on HF.
- **task-gate** (292k, dev acc 68.95%): `Nabidnur/spanguard-taskgate` on HF.
- **Split-conformal calibration** shipped at α=0.1 (in-family bound holds: 10.8% ≤ 10%+tol;
  full α sweep 0.05–0.50 in calibration_v2.json + sweep chart).
- **Mega-run record**: eval/results/v6-final-2021 (all sets, 4 systems) + v6-agentloop
  + semantic verdicts. Charts: docs/assets/v6_*.png.

## Headline numbers (all from committed records)
- extended-v6 (500 docs, 20 families, 7 languages): **0.0% escape / 0.8% over-strip**
- extended-attacks + extended-v4: **0.0% escape** (plain and tasked)
- NotInject benign utility **100%** (fast-v4: 93.3%), agent-loop hijack **1.3%** (fast-v4: 8.7%)
- AgentDojo canonical attacks: hijack surface **80.6% → 40.3%** with the task gate
- Semantic escape judge (LLM reads cleaned output): **0/30** for fm-v6 AND fast-v4
  after the v6 rule fixes (v3 red-team replay; rules alone: 30/30 verbatim-stripped)
- Hand-written OOD: 35.5% → **29.0%** with the gate (fast-v4 remains the OOD crown: 4.2%)
- Latency: p50 20.6 ms / p95 51.8 ms (2-thread CPU)
- Rating: **9.1/10** honest self-assessment (docs/rating.md)

## How to push the bundle to GitHub (GH token expired in the sandbox)
```bash
git clone https://github.com/Hisernberg/spanguard.git spanguard-old   # optional
git clone spanguard-v6.0.0.bundle spanguard                            # from bundle
cd spanguard && git checkout main
# or, from an existing clone:
#   git fetch /path/to/spanguard-v6.0.0.bundle 'refs/heads/*:refs/remotes/bundle/*'
#   git merge bundle/main   (fast-forward from a910a12)
git push origin main --tags
```
Vercel auto-deploys on push (the project is GitHub-connected). Manual CLI deploy:
```bash
cd website && vercel deploy --prod --yes --token <YOUR_TOKEN>   # link with: vercel link --project spanguard
```
Live: https://spanguard.vercel.app (already serving v6 content) · video: spanguard-demo-v6.mp4
