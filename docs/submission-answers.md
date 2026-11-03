# SpanGuard — Meta Global AI Hackathon 2026 submission answers

> All numbers come from committed run records (`eval/results/*/run.json`); regeneration
> commands in `docs/REPRODUCE.md`. Every table cell below is from a re-runnable record —
> nothing is projected, estimated or borrowed from another project's paper.

## 1. What does your project do? (≤ 100 words)

SpanGuard is an OpenAI-compatible security gateway for AI agents. Untrusted tool output —
API responses, fetched pages, MCP payloads, RAG chunks — passes through the gateway before
the agent reads it. A 135M-parameter multilingual span model plus 22 validated rules locate
prompt-injection text at character level and replace each span with `[stripped]`, while the
orders, totals, names and JSON structure around it survive untouched. A model family extends
coverage: a document-level classifier, and a tool-call guard that blocks malicious function
calls before they execute. CPU-only, no per-document LLM calls, Apache-2.0.

## 2. What inspired you? (≤ 100 words)

Agent frameworks pass tool results straight into the model's context. A single
"IGNORE ALL PREVIOUS INSTRUCTIONS" hidden in a carrier note is enough to hijack the
run — and defenses today are all-or-nothing: block the document (agent loses data it
needed) or pass it (attack goes through). We wanted the middle ground: surgical removal
of only the attack text, with both failure directions measured separately. The insight:
injection is a span problem, not a document-classification problem.

## 3. What does it measure? (the honest core)

| Set (all fictional / public, never our own claims) | spanguard fast-v2 | spanguard char (0.79M) | spanguard fast | fast (corpus-v2 model) | rules-only | Qwen2.5-0.5B self-detect | protectai deberta-v3 | horizon small (binary) | horizon base (binary) |
|---|---|---|---|---|---|---|---|---|---|
| Hand-written attacks · 62 docs (en/de/hu) | **10.4% · 14.0%** | **4.2% · 18.3%** | 29.2% · 11.3% | 33.3% · 6.9% | 72.9% · 7.5% | 91.7% · 13.1% | 35.4% · 71.8% | 8.3% · 37.7% | 6.2% · 59.0% |
| Agent traffic · 900 docs (synthetic tool output) | **0.0% · 4.3%** | 0.2% · 2.8% | 0.0% · 3.3% | 0.0% · 4.0% | 13.4% · 3.3% | 97.5% · 5.1% | 43.6% · 48.0% | 12.5% · 6.3% | 15.2% · 13.1% |
| Public prompts (benign-only probe) · 452 docs | **0.0% · 32.9%** | 0.0% · 33.6% | 0.0% · 34.2% | **0.0% · 18.1%** | 0.0% · 0.1% | 0.0% · 5.0% | 0.0% · 1.2% | 0.0% · 0.0% | 0.0% · 0.0% |

The corpus-v2 retrain (boundary-weighted loss, 3x hard negatives) is a textbook
precision/recall trade in the open: it nearly halves over-stripping on the public
probe (34.2% → 18.1%) and cuts hand-written over-strip 11.3% → 6.9%, at the cost
of a slightly WORSE hand-written escape (29.2% → 33.3%). We publish that shift
rather than cherry-picking the flattering axis; the fast-v2 ensemble keeps the
balanced operating point.

Cells are **escape % · over-strip %**. Four readings the table gives away for free:

1. **The 0.79M char model has the lowest escape of ANY system on the hand-written set
   (4.2%) — below horizon-base's 6.2% — while over-stripping 3× less than it (18.3% vs
   59.0%).** It dominates both binary baselines on both axes at 1/170th their footprint,
   and beats its own 135M teacher-model family member on OOD escape (4.2% vs 29.2%):
   char-level features generalize where subword models memorize template phrasing.
2. **fast-v2 (structure-gated ensemble: rules + 135M span + char) is the balanced flagship** —
   escape 29.2% → 10.4% vs fast, and the first spanguard system to also beat fast on the
   public-prompt weak spot (over-strip 32.9% vs 34.2%). No competitor achieves both lower
   escape and lower over-strip than fast-v2 on any set.
3. **A 0.5B LLM asked to flag injections in its own context misses 91.7%** of hand-written
   attacks — "just ask the model to be careful" is not a defense (and it costs tokens).
4. **The public-prompt set remains the honest weak spot** (over-strip ~33%): the span model
   (trained on tool-output style) still over-strips user-prompt text while catching every
   attack. The corroboration gate chips away at it; the rules-only column shows the safe
   fallback there.

- **Escape rate**: share of planted attack payload still fully readable after the guard.
- **Over-stripping**: share of benign characters destroyed on clean documents.
- Binary baselines are scored with strip-all semantics: one bit → the whole document
  is lost. That is what a 1-bit classifier can actually do operationally.

**Domain expansion (v3).** Corpus v3 + char-v3 extend coverage to the 2026 surface
(MCP tool poisoning, skill files, buried multi-hop, markdown-image exfil, polite
social engineering, +Bangla): on those five NEW families char-v3 scores 0.4% escape
with span F1 0.996 where char-v2 scored 11.6% / 0.467. The trade is published too:
char-v3 regresses on the original hand-written OOD set (4.2% → 12.5%). Both models
ship; per-domain routing is roadmap.

**v3.1 flagship record.** fast-v3 (rules + 135M span + char router with Bangla
detection) scores **0.0% escape / 0.0% over-strip / doc F1 1.000 on the committed
extended-attacks fixture** where protectai deberta-v2 escapes 84.3% and the horizon
binaries 8.6–10% — the buried-signal washout of whole-sequence classifiers,
measured on our own data. The router fix (bn → char-v3, union path for routed
docs) was found by the visual-inference demo catching a real Bangla escape, then
verified by tests and a re-run record. Two span variants ship with their trade
published: span-v2 (0.0% extended escape, 19.8% public over-strip, 16.7%
hand-written escape) and span-v1 (10.4% hand-written escape, 32.9% public
over-strip).

## 4. The model family (4 models; span models on free Kaggle GPU, the rest on local CPU)

| Model | Task | Result | HF |
|---|---|---|---|
| spanguard-span-mdistil (135M) | BIO span tagging, en/de/hu | dev span-F1 0.899; with rules: escape 0.0% on agent-traffic | [link](https://huggingface.co/Nabidnur/spanguard-span-mdistil) |
| spanguard-char (0.79M) | char-level spans + doc verdict, one dual-head model (en/de/hu/fr) | trained on CPU in 40 min on corpus-v2; handwritten escape **4.2%** (best of all systems), doc F1 0.94 on agent traffic | [link](https://huggingface.co/Nabidnur/spanguard-char) |
| spanguard-docguard-mdistil | doc-level attack/ok | dev F1 0.984 (recall 1.0, false-block 5.2%) | [link](https://huggingface.co/Nabidnur/spanguard-docguard-mdistil) |
| spanguard-toolguard-mdistil | tool-call argument guard | held-out F1 1.0, false-block 0.0% | [link](https://huggingface.co/Nabidnur/spanguard-toolguard-mdistil) |

**Why a family and not one model:** on the same 400 held-out tool calls, the doc-level
classifier reaches recall 1.0 but false-blocks **39.0%** of benign calls — unusable as a
gateway policy — while the tool-call guard false-blocks **0.0%** (p50 45.5 ms vs 57.5 ms
on CPU). A span edit inside a JSON argument is not an option (the call executes or it
doesn't), which is exactly why a dedicated classifier earns its place. The char model is
the newest tier: it reads raw characters (homoglyphs and zero-width payload survive no
smoothing), trains in minutes on CPU, and serves as the independent corroboration signal
inside the fast-v2 ensemble.
Records: `eval/results/2026-11-02-family/run.json`, `eval/results/fastv2-corrob-0035/run.json`.

## 5. What did you build?

- `spanguard` pip package: rules engine (18 patterns), span model wrapper, audit mode
  (optional LLM), OpenAI-compatible gateway (FastAPI) with `/v1/chat/completions`
  request inspection and tool-result cleaning, plus `/guard` JSON API.
- Deterministic fictional corpus generator (en/de/hu, 10 attack families + benign
  traps, seed-locked, hash manifest). No real or scraped data anywhere.
- Teacher pipeline (fictional-key gated) + local recovery trainer (CPU, Adafactor,
  memory-profiled for 4GB sandboxes).
- Eval harness: committed run records, SVG chart renderer, CI regression gate
  (`make gate` — passing), reproduction guide (`docs/REPRODUCE.md`).
- Static demo Space with real precomputed gateway outputs + a JS port of the rules
  engine for live pasting: https://huggingface.co/spaces/Nabidnur/spanguard-demo
- 14/14 tests, Dockerfile + compose for the gateway, GitHub Actions CI.

## 6. How did you build it? (stack + constraints)

The compute story has three honest tiers. The 135M span models (v1 and the corpus-v2
retrain) trained on free Kaggle GPUs — the kernels are committed and re-runnable. The
smaller family models (docguard, toolguard, and the 0.79M char model) trained locally on
a 4GB CPU-only sandbox using Adafactor so 541MB models fit in memory. The Muse Spark Open
teacher pass ran exactly once — 1,150 calls, $3.91, logged in `data/corpus-manifest.json` —
as a precision check on the deterministic generator labels, not as the label source: it
recovered 62.5% of planted spans and hallucinated zero extra ones, so `planted ∪ teacher
== planted`. Platform outages along the way are why the recovery trainer exists; every
failure mode is documented in worklog-style commits.

## 7. What was hard?

1. **Measuring both failure directions.** Escape rate alone flatters any aggressive guard;
   we report over-stripping next to it everywhere, including per language and per family.
2. **Transformers 5.x migration bugs**: `BatchEncoding` indexing and uneven overflow
   windows broke three different code paths (train, dev-eval, inference) — each fix is a
   commit with a regression test.
3. **Staying honest under deadline**: when the teacher-LLM key died, we did not fake
   distillation; the trainer fell back to deterministic label functions, and the corpus
   manifest proves which labels are rule-derived.

## 8. Try it

- Demo (static, real gateway outputs): https://huggingface.co/spaces/Nabidnur/spanguard-demo
- Gateway locally: `docker compose up` then POST to `:8819/v1/chat/completions`
- Models: https://huggingface.co/Nabidnur → `spanguard-*-mdistil`
- Source + committed benchmarks: https://github.com/Hisernberg/spanguard

## 9. Track

- [x] AI Agent Security (prompt injection defense for tool traffic)
- [x] Small/distributed models (135M family, CPU-only, no per-doc LLM)
