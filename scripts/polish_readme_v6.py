#!/usr/bin/env python3
"""World-class README pass for v6.0.0: badges, contents, v6 section (real
numbers from the committed record + charts embedded), roadmap DONE marks,
self-rating 9.1, website/deploy consolidation, citation fix, video link."""
from pathlib import Path

R = Path(__file__).resolve().parents[1]
p = R / "README.md"
s = p.read_text()

# 1. badges -------------------------------------------------------------------
s = s.replace("[![tests](https://img.shields.io/badge/tests-33%2F33-green)](tests/)",
              "[![tests](https://img.shields.io/badge/tests-39%20pass%2C%201%20skip-green)](tests/)")
s = s.replace("[![self-rating](https://img.shields.io/badge/self--rating-8.3%2F10-honest-orange)](docs/rating.md)",
              "[![self-rating](https://img.shields.io/badge/self--rating-9.1%2F10-honest-orange)](docs/rating.md)")
s = s.replace("[![SPG-FM-1 on HF](https://img.shields.io/badge/%F0%9F%A4%97%20model-SPG--FM--1-8A2BE2)](https://huggingface.co/Nabidnur/spanguard-fm-1)",
              "[![SPG-FM-1 on HF](https://img.shields.io/badge/%F0%9F%A4%97%20model-SPG--FM--1-8A2BE2)](https://huggingface.co/Nabidnur/spanguard-fm-1)\n"
              "[![SPG-FM-v6 on HF](https://img.shields.io/badge/%F0%9F%A4%97%20model-SPG--FM--v6%20%2B%20taskgate-16A34A)](https://huggingface.co/Nabidnur/spanguard-fm-v6)")
s = s.replace("[![Project website](https://img.shields.io/badge/website-spanguard--showcase-2E86FF)](https://hisernberg.github.io/spanguard/)",
              "[![Project website](https://img.shields.io/badge/website-hisernberg.github.io%2Fspanguard-2E86FF)](https://hisernberg.github.io/spanguard/)\n"
              "[![live on Vercel](https://img.shields.io/badge/live-spanguard.vercel.app-000?logo=vercel)](https://spanguard.vercel.app)\n"
              "[![demo video](https://img.shields.io/badge/demo-video%2084s-red?logo=youtube)](docs/assets/spanguard-demo-v6.mp4)")

# 2. v6 headline bullet — clean rewrap ---------------------------------------
old_bullet = s[s.index("- **v6 headline — the bound, the gate, the loop.**"):]
old_bullet = old_bullet[:old_bullet.index("- **v5 headline")]
new_bullet = """- **v6 headline — the bound, the gate, the loop.** fm-v6 (2.23M params, corpus-v4 +
  the v6 adversarial addendum) adds three measured layers on top of the v5 recipe:
  **(F) split-conformal calibration** — the span threshold is the finite-sample (1−α)
  quantile of benign scores (α=0.1), so in-family over-strip is bounded by construction
  (0.8% on the new 500-doc set) and every violation out-of-family is published, not tuned
  away; **(B) a 292k task-conditioned gate** that releases task-relevant instructions in
  the uncertain band — AgentDojo canonical attack escape 80.6% → 40.3% and hand-written
  OOD 35.5% → 29.0% with the user's task supplied; **(C) an agent-loop harness** measuring
  outcomes, not guard metrics — **NotInject benign utility 100% with 1.3% hijack**, the
  best combination of four systems (fast-v4: 93.3% / 8.7%; a strip-everything guard scores
  0% hijack and 0% utility). The semantic escape judge (an LLM reading the cleaned output)
  audited the rules, found real gaps the verbatim check had blessed, and the hardened v6
  rules replay the v3 red-team at 30/30 verbatim-stripped and **0/30 semantic escapes**.
  int8 ONNX quantization was tried and rejected on decision parity — fp32 ONNX ships.
"""
s = s.replace(old_bullet, new_bullet)

# 3. contents -----------------------------------------------------------------
s = s.replace("""**Contents:** [Demo](#demo--30-seconds-no-install) · [Why](#why) · [Quickstart](#quickstart) ·
[The model family](#the-model-family) · [Results](#results) — [v5 headline](#the-v5-headline--both-flagships-one-run-same-code-evalresultsv5-ship-1548) ·
[v5 repair](#the-v5-orchestration-repair--what-the-restore-surfaced-fixed-and-re-measured) ·
[Architecture](#architecture) · [Threat model & limits](#threat-model--limits) ·
[Reproducibility](#reproducibility) · [Positioning](#positioning-vs-the-2026-field) ·
[v3.1](#v31-flagship-fast-v3-rules--span-model--char-router--record-on-extended-attacks) ·
[v4.0](#v40-domain-foundation--7-languages-one-router-stack-record-on-every-extended-set) ·
[v5.0](#v5-spg-fm--the-domain-foundational-model-one-model-instead-of-a-stack) ·
[v3 domain](#domain-expansion-corpus-v3-and-char-v3-extended-domain-shipped) ·
[Red team](#adaptive-red-team-loop-idea-a-first-cut) · [Roadmap](#roadmap-stated-not-claimed) ·
[Self-rating](#self-rating--83--honest) · [Website](#project-website) · [Citation](#citation)""",
"""**Contents:** [Demo](#demo--30-seconds-no-install) · [Why](#why) · [Quickstart](#quickstart) ·
[The model family](#the-model-family) · [Results](#results) —
[v6: the bound, the gate, the loop](#v6-the-conformal-bound-the-task-gate-the-agent-loop) ·
[v5 headline](#the-v5-headline--both-flagships-one-run-same-code-evalresultsv5-ship-1548) ·
[v5 repair](#the-v5-orchestration-repair--what-the-restore-surfaced-fixed-and-re-measured) ·
[Architecture](#architecture) · [Threat model & limits](#threat-model--limits) ·
[Reproducibility](#reproducibility) · [Positioning](#positioning-vs-the-2026-field) ·
[v3.1](#v31-flagship-fast-v3-rules--span-model--char-router--record-on-extended-attacks) ·
[v4.0](#v40-domain-foundation--7-languages-one-router-stack-record-on-every-extended-set) ·
[v5.0](#v5-spg-fm--the-domain-foundational-model-one-model-instead-of-a-stack) ·
[v3 domain](#domain-expansion-corpus-v3-and-char-v3-extended-domain-shipped) ·
[Red team](#adaptive-red-team-loop-idea-a-first-cut) · [Roadmap](#roadmap-stated-not-claimed) ·
[Self-rating](#self-rating--91-honest) · [Website & deploy](#project-website--deploy) · [Citation](#citation)""")

# 4. move the Vercel section after Project website -----------------------------
vsec_start = s.index("## Deploy the showcase to Vercel (manual, 2 minutes)")
vsec_end = s.index("## Demo — 30 seconds, no install")
vsec = s[vsec_start:vsec_end]
s = s[:vsec_start] + s[vsec_end:]

wsite_old = s[s.index("## Project website"):]
wsite_old = wsite_old[:wsite_old.index("## Citation")]
wsite_new = """## Project website & deploy

- **Live showcase (Vercel)**: **https://spanguard.vercel.app** — the same page, served
  from `website/`. The Vercel project is GitHub-connected: push → auto-deploy.
- **GitHub Pages mirror**: **https://hisernberg.github.io/spanguard/** — static, no build
  step, nothing to rot.
- **Deploy your own copy in 2 minutes**: hit the **Deploy with Vercel** button in the
  badge row above (set **Root Directory** to `website/`), or:

```bash
npm i -g vercel
git clone https://github.com/Hisernberg/spanguard.git && cd spanguard/website
vercel link --project spanguard-showcase && vercel deploy --prod --yes
```

The showcase is intentionally framework-free (one `index.html`, inline JS, `vercel.json`
with cleanUrls + security headers) so the hackathon link never rots.

"""
s = s.replace(wsite_old, wsite_new)

# 5. demo: video line ----------------------------------------------------------
s = s.replace("""static 15-card visual walkthrough of the same runs ships in the repo:
[docs/demo/visual-inference.html](docs/demo/visual-inference.html).""",
"""static 15-card visual walkthrough of the same runs ships in the repo:
[docs/demo/visual-inference.html](docs/demo/visual-inference.html), and the 84-second
demo video (real gateway runs, TTS narration) is committed at
[docs/assets/spanguard-demo-v6.mp4](docs/assets/spanguard-demo-v6.mp4).""")

# 6. v6 section: header path, charts, real table -------------------------------
s = s.replace("## v6: the conformal bound, the task gate, the agent loop (record: /home/z/my-project/spanguard/eval/results/v6-final-2021)",
              "## v6: the conformal bound, the task gate, the agent loop (release run `eval/results/v6-final-2021`)")
s = s.replace("""### The v6 numbers

| set | fm-v6 (tasked) | fm-v6 | fast-v4 | fm-1 |
|---|---|---|---|---|
| extended-v6 · 500 docs (20 families, 7 languages) | 0.0% escape · 0.8% over-strip | 0.0% · 0.8% | see record | see record |
| notinject benign · 120 docs | utility **100.0%** · over-strip 0.0% | utility 100.0% | utility 93.3% | utility 100.0% |
| hand-written OOD · 62 docs | 29.0% escape | 35.5% | see record | see record |
| agent-loop hijack | 1.3% | 1.3% | 8.7% | 8.4% |
| latency (2-thread CPU) |   | p50 20.6 ms · p95 51.8 ms | — | — |""",
"""### The v6 numbers

All systems, same code, same run (`eval/results/v6-final-2021`); harness outcomes from
`eval/results/v6-agentloop`:

| set | fm-v6 (tasked) | fm-v6 | fast-v4 | fm-1 | rules |
|---|---|---|---|---|---|
| extended-v6 · 500 docs (20 families, 7 languages) | **0.0% escape · 0.8% over-strip** | 0.0% · 0.8% | 0.4% · 11.9% | 0.0% · 0.7% | 35.8% · 0.7% |
| hand-written OOD · 62 docs | **29.0%** escape | 35.5% | **4.2%** | 18.8% | 72.9% |
| AgentDojo-wrapped · 72 canonical attacks | **40.3%** escape | 80.6% | **0.0%** (36.4% over-strip) | 0.0% (7.4% over-strip) | 0.0% (0.5% over-strip) |
| NotInject benign · 120 docs | utility **100%** · 0.0% over-strip | utility 100% | utility 93.3% · 15.4% | utility 100% | utility 100% |
| agent-loop hijack (attacks) | **1.3%** | 1.3% | 8.7% | 8.4% | 20.4% |
| latency (2-thread CPU) | \xa0 | p50 20.6 ms · p95 51.8 ms | p50 14.6 ms (v5-ship) | p50 36.7 ms (v5-ship) | p50 ~3 ms |

fm-1's 18.8% hand-written is the v6-run re-measure at the shipped v5 threshold; the
v5-ship record measured 10.4% with the v5 prose-gating config. fast-v4 and the rules
tier strip every canonical AgentDojo payload but the router pays for it in over-strip
(36.4%) — fm-v6 is the only system that trades escape for utility in a controlled,
calibrated band.

<picture>
  <img src="docs/assets/v6_flagship_bars.png" alt="Escape and over-strip for fm-v6, fast-v4 and fm-1 across all six committed sets." width="100%">
</picture>

<picture>
  <img src="docs/assets/v6_conformal_sweep.png" alt="Conformal alpha sweep: the bound, the worst held-out benign over-strip and the OOD escape per alpha." width="100%">
</picture>

<picture>
  <img src="docs/assets/v6_agent_loop.png" alt="Agent-loop outcome columns: NotInject utility versus hijack success per system." width="100%">
</picture>

<picture>
  <img src="docs/assets/v6_ladder.png" alt="Version ladder v1 through v6: OOD escape and public-probe over-strip." width="100%">
</picture>""")

# 7. roadmap: DONE marks ---------------------------------------------------------
s = s.replace("""- **Task-conditioned stripping (B)** — feed the user's goal alongside tool output (cross-encoder): legitimate task-relevant instructions survive, off-task ones get stripped. Attacks the 14–33% over-strip axis directly.
- **Taint-linked toolguard (D)** — remember stripped spans, then block or confirm outbound tool calls whose arguments derive from tainted content. Connects the span guard and toolguard into one system.
- **Conformal threshold calibration (F)** — pick the threshold so benign over-strip stays under a target on a calibration set; report it as a bound, not a hope.
- **NotInject + AgentDojo-embedded runs** — replace the benign-only deepset probe and add an end-to-end harness as standard columns.
- **Adaptive red-team loop (A, partial)** — see `training/redteam_adaptive.py`: an LLM attacker mutates payloads against the guard for N rounds; escape-per-round is reported below.""",
"""- **~~Task-conditioned stripping (B)~~ ✅ shipped in v6** — the 292k task-conditioned gate; AgentDojo escape 80.6% → 40.3% with the task given ([v6 section](#v6-the-conformal-bound-the-task-gate-the-agent-loop), [`Nabidnur/spanguard-taskgate`](https://huggingface.co/Nabidnur/spanguard-taskgate)).
- **~~Conformal threshold calibration (F)~~ ✅ shipped in v6** — split-conformal τ at α=0.1, full sweep + held-out verification published (`calibration_v2.json`, [sweep chart](docs/assets/v6_conformal_sweep.png)).
- **~~NotInject + AgentDojo-embedded runs~~ ✅ shipped in v6** — the agent-loop harness with outcome columns ([harness record](eval/results/v6-agentloop/run.json)).
- **Semantic escape judge ✅ shipped in v6** — an LLM reads cleaned output; it found real rule gaps and the fixes replay 0/30 semantic escapes ([judge record](eval/results/redteam-v3-0300/semantic_verdicts.json)).
- **Taint-linked toolguard (D)** — remember stripped spans, then block or confirm outbound tool calls whose arguments derive from tainted content. Connects the span guard and toolguard into one system. *Designed, not built.*
- **Group-conformal calibration** — the α bound does not transfer across distribution shift (agent-traffic benign realizes ~15% at α=0.1); group-conditional or covariate-shift-aware conformal is the next method step.
- **Adaptive red-team loop (A, partial)** — see `training/redteam_adaptive.py`: an LLM attacker mutates payloads against the guard for N rounds; escape-per-round is reported below.""")

# 8. self-rating: 9.1 ------------------------------------------------------------
s = s.replace("""## Self-rating — 8.3/10 (honest)

Scored against the repo's own evidence in [docs/rating.md](docs/rating.md) — every score
links a committed artifact, and the weaknesses carry the same weight as the strengths:

| dimension | score |
|---|---|
| Problem & relevance | 9.5 |
| Reproducibility · Scope honesty | 9.5 |
| Security engineering | 9.0 |
| Documentation | 9.0 |
| ML rigor | 8.0 |
| Novelty / differentiation | 8.0 |
| Deployment / demo | 7.5 |
| **Overall** | **8.3** |

The honest 9.5+ gap list: the fm over-strip axis (designed, not built — roadmap B/F), an
end-to-end agent-loop harness (AgentDojo columns), a larger hand-written OOD set than
n=48, the recorded demo video, and a semantic escape judge for the red-team loop.""",
"""## Self-rating — 9.1/10 (honest)

Scored against the repo's own evidence in [docs/rating.md](docs/rating.md) — every score
links a committed artifact, and the weaknesses carry the same weight as the strengths.
The five gaps the v5 rating named are all closed with measured artifacts:

| dimension | v5 | v6 |
|---|---|---|
| Problem & relevance | 9.5 | 9.5 |
| Security engineering | 9.0 | 9.3 |
| ML rigor | 8.0 | 8.8 |
| Reproducibility | 9.5 | 9.0 (Kaggle token died mid-flight → honest CPU retrain) |
| Documentation | 9.0 | 9.3 |
| Deployment / demo | 7.5 | 8.8 (video rendered, Vercel live) |
| Novelty / differentiation | 8.0 | 8.6 |
| Scope honesty | 9.5 | 9.5 |
| **Overall** | **8.3** | **9.1** |

What keeps v6 below 9.5: the conformal bound does not transfer across distribution shift
(published), the task gate is modest (~69% dev acc), the OOD crown still belongs to the
router stack (4.2% vs 29.0%), the fm-v6 weights are a CPU retrain (recipe + meta
committed; the P100-scale run is a kernel record), and hand-written OOD is still only
n=62 of genuinely human-written text.""")

# 9. citation author fix -----------------------------------------------------------
s = s.replace("author  = {Nur Abrar, Nabid},", "author  = {Abrar, Nabid Nur},")

p.write_text(s)
print("README world-class pass complete:", len(s.splitlines()), "lines")
