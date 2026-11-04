# Changelog

All notable versions of SpanGuard, v0 → v6. Every number below is a committed,
re-verifiable run record (`eval/results/`); models are published on
[Hugging Face](https://huggingface.co/Nabidnur/spanguard-suite). Dates are the
build dates of this repository's history (the whole ladder was built in a single
compressed sprint for the Meta Global AI Hackathon 2026).

The one-line story: **v0** rules-only prototype → **v1** measurable eval harness →
**v2** trained span model → **v3** domain expansion → **v3.1** record flagship →
**v4** 7-language domain foundation → **v5** one-model collapse (SPG-FM) →
**v6** the conformal bound, the task gate, the agent loop.

---

## v6.0.0 — the bound, the gate, the loop (2026-11-04) `v6.0.0`

*The five gaps the v5 rating named, all closed with measured artifacts.*

- **fm-v6** (2.23M params, corpus-v4 + v6 adversarial addendum) — release run
  [`v6-final-2021`](eval/results/v6-final-2021): **0.0% escape / 0.8% over-strip** on the
  500-doc extended-v6 fixture (20 families, 7 languages); p50 20.6 ms on CPU. Retrained
  locally on CPU after the Kaggle credentials expired mid-flight (recipe + meta committed).
- **(F) Split-conformal span threshold** — τ is the finite-sample (1−α) quantile of benign
  scores (α=0.1); in-family over-strip bounded by construction, full α sweep + held-out
  verification published, worst out-of-family violation reported honestly (~15%).
- **(B) Task-conditioned gate** (292k char-CNN, [`spanguard-taskgate`](https://huggingface.co/Nabidnur/spanguard-taskgate))
  — with the user's task supplied: AgentDojo canonical escape **80.6% → 40.3%**, hand-written
  OOD **35.5% → 29.0%**.
- **Agent-loop harness** ([`v6-agentloop`](eval/results/v6-agentloop)) — outcome columns, not
  guard metrics: fm-v6 **NotInject utility 100% / hijack 1.3%**, best of four systems
  (fast-v4 93.3%/8.7%; strip-everything 0%/0%; pass-everything 100%/20.4%).
- **Semantic escape judge** — an LLM reads cleaned output; found real rule gaps the verbatim
  check had blessed + mid-URL sentence-boundary residue. Hardened rules replay the v3
  red-team at **30/30 verbatim-stripped and 0/30 semantic escapes** (both flagships).
- int8 ONNX quantization tried and **rejected on decision parity**; fp32 ONNX ships.
- Models: [`spanguard-fm-v6`](https://huggingface.co/Nabidnur/spanguard-fm-v6),
  [`spanguard-taskgate`](https://huggingface.co/Nabidnur/spanguard-taskgate). Self-rating 9.1/10.

## v5.0.0 — SPG-FM: one model instead of a stack (2026-11-04) `v5.0.0`

- **SPG-FM-1** (1.70M char-level multi-task, trained on the full corpus-v4 union) replaces
  the regex router + three experts; one forward pass emits doc verdict + payload spans
  ([`spanguard-fm-1`](https://huggingface.co/Nabidnur/spanguard-fm-1), run
  [`v5-ship-1548`](eval/results/v5-ship-1548)).
- **0.0% escape on every in-domain set, all 7 languages**; doc F1 1.000 on both extended
  fixtures; best payload localization in the family (span F1 0.917/0.901 vs 0.689/0.612).
- **The honest cost, published**: out-of-domain benign prose over-strips (45.4% public probe
  / 26.4% hand-written) — the router stack keeps the fidelity crown (24.6%/17.5%).
- **Orchestration repair** surfaced by the sandbox restore: `is_structured` rebuilt,
  fast-v4 union-everywhere restored, fm prose gating added. fast-v4's hand-written OOD
  escape 16.7% → 4.2% (all-time best); broken intermediate runs committed for audit.

## v4.0.0 — domain foundation: 7 languages, one router stack (2026-11-03) `v4.0.0`

- **corpus-v4**: 16,000 seed-locked docs, 7 languages (en/de/hu/fr/bn/**ar/ja**), 18 families —
  adds log-file poisoning, code-comment injection, RAG-chunk poisoning + in-domain Arabic
  and Japanese.
- **Zero-shot washout measured, then fixed**: char-v3 escaped 30.7% (ar) / 34.0% (ja);
  the span model missed 76.2% of log-poison spans. After v4 training: **char-v4 0.0% escape
  in every one of the 7 languages** ([`spanguard-char-v4`](https://huggingface.co/Nabidnur/spanguard-char-v4)).
- **fast-v4**: 3-level char router (route every doc to its expert; union channel everywhere) —
  extended-v4 fixture: 0.0% escape / 0.0% over-strip / doc F1 1.000 / span F1 0.955.

## v3.1.0 — fast-v3 flagship, record on extended attacks (2026-11-03)

- Domain router (MCP/skill/buried/md-image carriers + Bangla script → char-v3) + union path.
- **fast-v3 4-set sweep: extended-attacks 0.0% escape / 0.0% over-strip / doc F1 1.000** —
  all five 2026 carrier families at 0.0%, vs the whole-document baseline (protectai-deberta)
  at 84.3% escape on the same fixture.
- extended-attacks fixture committed (88 docs / 70 planted, seed-locked); red-team curve +
  extended frontier charts; visual-inference demo (real runs, typed markers, honest FPs).

## v3.0.0 — corpus v3: the 2026 attack surface (2026-11-03) `v3.0.0`

- **corpus-v3** adds MCP tool-description poisoning, agent skill/config files, buried
  multi-hop payloads, markdown-image exfiltration, polite social-engineering + Bangla
  (14,000 docs, 16 families, 5 languages).
- **char-v3** retrained: new families **0.4% escape / span F1 0.996** (char-v2 washed out at
  11.6% / 0.467; buried multi-hop alone 33.3%). Honest regression published: old hand-written
  OOD 4.2% → 12.5% ([`spanguard-char-v3`](https://huggingface.co/Nabidnur/spanguard-char-v3)).
- **Adaptive red-team loop (first cut)**: an LLM attacker mutates payloads against the live
  guard for 6 rounds — 25 real mutations, **0 escapes in 30 attempts** (verbatim check).

## v2.0.0 — the trained span model, hard truths (2026-11-03) `v2.0.0`

- **corpus-v2**: 4th language (fr), doubled per-family templates, ×3 hard negatives
  (quoted attacks in runbooks, benign base64/hex, homoglyph brand names) — 14,400 docs.
- **spanguard-span-mdistil-v2** retrained on it (boundary-weighted token loss, ×3 at span
  edges): dev F1 1.0; shipped as
  [`spanguard-span-mdistil-v2`](https://huggingface.co/Nabidnur/spanguard-span-mdistil-v2).
- **Truth pass**: teacher pass ran once (Muse Spark Open, 1,150 calls, $3.91 — recovered
  62.5% of planted spans, hallucinated zero teacher-only spans → the deterministic generator
  beats LLM-as-annotator); Wilson CIs; public-deepset reframed as a benign-only over-strip
  probe; 2026 positioning table (Meta stack, Sanitizer, Presidio, NotInject); roadmap B/D/F.
- **v3 engineering hardening**: tool-def scanning + rug-pull pins, typed `[stripped:*]`
  markers, async client, Bearer-by-default, /guard auth, honest /healthz degradation, ruff
  clean, 21 → 26 tests.

## v1.0.0 — measurable from day one (2026-11-03) `v1.0.0`

- Deterministic **agent-traffic corpus generator** with planted spans (fictional data,
  seed-locked, manifest committed).
- **62 hand-written multilingual fixtures** — novel attacks + benign traps, the OOD set
  nothing is allowed to train on.
- **Eval scorer + run records + CI regression gate** (escape and over-strip reported
  together), docker + compose + GitHub Actions, SVG chart engine
  (frontier/heatmap/language/latency/banner/pipeline).

## v0 — prototype, pre-tag (2026-11-03)

- Scaffold of the `spanguard` package (types, config, spec).
- **Rule engine** — override / impersonation / exfiltration / encoding / smuggling patterns
  with span merge + strip.
- **SLM span-tagger wrapper** + opt-in Muse Spark Open audit mode.
- **OpenAI-compatible gateway** with tool-output inspection + demo UI.

---

### Tag index

| tag | commit | note |
|---|---|---|
| `v1.0.0` | `0dc0e20` | first measurable release |
| `v2.0.0` | `5ed489d` | span-v2 + truth pass |
| `v3.0.0` | `71d7d03` | extended domain shipped |
| `v5.0.0` | `865ba00` | SPG-FM-1 + repair |
| `v6.0.0` | `90892cc` | bound, gate, loop |

(v3.1 and v4 shipped between tags; the commits above are their release records — see the
date-ordered `git log` and each version's section.)
