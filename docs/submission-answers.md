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

| Set (all fictional / public, never our own claims) | spanguard fast | rules-only | Qwen2.5-0.5B self-detect | protectai deberta-v3 | horizon small (binary) | horizon base (binary) |
|---|---|---|---|---|---|---|
| Hand-written attacks · 62 docs (en/de/hu) | **29.2% · 11.3%** | 72.9% · 7.5% | 91.7% · 13.1% | 35.4% · 71.8% | 8.3% · 37.7% | 6.2% · 59.0% |
| Agent traffic · 900 docs (synthetic tool output) | **0.0% · 3.3%** | 13.4% · 3.3% | 97.5% · 5.1% | 43.6% · 48.0% | 12.5% · 6.3% | 15.2% · 13.1% |
| Public prompts · 452 docs (deepset, external) | 0.0% · 34.2% | 0.0% · 0.1% | 0.0% · 5.0% | 0.0% · 1.2% | 0.0% · 0.0% | 0.0% · 0.0% |

Cells are **escape % · over-strip %**. Three readings the table gives away for free:

1. **spanguard fast is Pareto-optimal on the hand-written set** — no competitor achieves
   both lower escape and lower over-strip. horizon-base buys 6.2% escape by destroying
   59.0% of benign characters; protectai is worse than spanguard on *both* axes.
2. **A 0.5B LLM asked to flag injections in its own context misses 91.7%** of hand-written
   attacks — "just ask the model to be careful" is not a defense (and it costs tokens).
3. **The public-prompt set is spanguard's honest weak spot**: the span model (trained on
   tool-output style) over-strips 34.2% of user-prompt text while catching every attack.
   We publish it anyway; the rules-only column shows the fallback is safe there.

- **Escape rate**: share of planted attack payload still fully readable after the guard.
- **Over-stripping**: share of benign characters destroyed on clean documents.
- Binary baselines are scored with strip-all semantics: one bit → the whole document
  is lost. That is what a 1-bit classifier can actually do operationally.

## 4. The model family (3 models, all trained locally on CPU)

| Model | Task | Result | HF |
|---|---|---|---|
| spanguard-span-mdistil (135M) | BIO span tagging, en/de/hu | dev span-F1 0.899; with rules: escape 0.0% on agent-traffic | [link](https://huggingface.co/Nabidnur/spanguard-span-mdistil) |
| spanguard-docguard-mdistil | doc-level attack/ok | dev F1 0.984 (recall 1.0, false-block 5.2%) | [link](https://huggingface.co/Nabidnur/spanguard-docguard-mdistil) |
| spanguard-toolguard-mdistil | tool-call argument guard | held-out F1 1.0, false-block 0.0% | [link](https://huggingface.co/Nabidnur/spanguard-toolguard-mdistil) |

**Why a family and not one model:** on the same 400 held-out tool calls, the doc-level
classifier reaches recall 1.0 but false-blocks **39.0%** of benign calls — unusable as a
gateway policy — while the tool-call guard false-blocks **0.0%** (p50 45.5 ms vs 57.5 ms
on CPU). A span edit inside a JSON argument is not an option (the call executes or it
doesn't), which is exactly why a dedicated classifier earns its place.
Records: `eval/results/2026-11-02-family/run.json`.

## 5. What did you build?

- `spanguard` pip package: rules engine (22 patterns), span model wrapper, audit mode
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

Local CPU-only sandbox (4GB RAM, no GPU): distil-multilingual-CASE backbone for all three
models; the trainer pre-tokenizes to fixed windows and uses Adafactor (no Adam moment
buffers) so 541MB models train inside 4GB; models checkpoint to disk and publish to the
Hugging Face Hub. The original plan (Kaggle GPU + Baseten teacher) died twice on platform
outages — the recovery trainer was written to make the whole pipeline reproducible on a
laptop. Every failure mode we hit is documented in the repo (`worklog`-style commits,
commit-by-commit).

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
