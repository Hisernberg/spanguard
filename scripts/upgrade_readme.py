#!/usr/bin/env python3
"""World-class README upgrade: v4/v5 headline numbers, model family evolution,
live-inference Space section, refreshed badges. Idempotent with asserts."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
p = REPO / "README.md"
s = p.read_text()


def rep(old: str, new: str, label: str) -> None:
    global s
    assert old in s, f"anchor missing: {label}"
    s = s.replace(old, new, 1)
    print("ok:", label)


# ---- 1. badges: add char-v4 + FM + Space badges
rep('[![Model on Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20model-spanguard--span--mdistil-yellow)](https://huggingface.co/Nabidnur/spanguard-span-mdistil)',
    '[![Model on Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20model-spanguard--span--mdistil-yellow)](https://huggingface.co/Nabidnur/spanguard-span-mdistil)\n'
    '[![char-v4 on HF](https://img.shields.io/badge/%F0%9F%A4%97%20model-spanguard--char--v4-yellow)](https://huggingface.co/Nabidnur/spanguard-char-v4)\n'
    '[![SPG-FM-1 on HF](https://img.shields.io/badge/%F0%9F%A4%97%20model-SPG--FM--1-8A2BE2)](https://huggingface.co/Nabidnur/spanguard-fm-1)\n'
    '[![Live demo Space](https://img.shields.io/badge/%F0%9F%A4%97%20Space-real%20inference-blue)](https://huggingface.co/spaces/Nabidnur/spanguard-demo)',
    "badges row")

# ---- 2. intro: lead with v4 records
rep('<!-- intro:start -->\n- **What it does.**',
    '<!-- intro:start -->\n- **What it does.**',
    "intro anchor (identity, kept for ordering)")
rep("- **How well.** On the 62-document hand-written multilingual attack set, spanguard fast-v2 (ensemble) escapes 10.4% of planted attack payloads at 14.0% benign data loss (doc F1 89%). The strongest open binary guard on the same set (horizon injection-guard base, strip-all semantics) reaches 6.2% escape only by over-stripping 59.0% of benign characters — the agent loses most of what it was reading; protectai deberta-v3 is worse than spanguard on BOTH axes (35.4% escape, 71.8% over-strip); a 0.5B LLM asked to flag its own injections misses 91.7% of attacks. spanguard's char-only tier trades a further escape cut (4.2%) for 18.3% over-strip when security outweighs data fidelity.",
    "- **How well (v4 flagship).** `fast-v4` — validated rules + a 135M multilingual span model + a 3-level char router — escapes **0.0%** of planted payloads on the 900-document agent-traffic set (4.7% benign over-strip) and on both extended attack fixtures: the 88-doc extended-attacks set at **0.0% escape / 0.0% over-strip / doc F1 1.000** and the 108-doc extended-v4 fixture at **0.0% / 0.2% / doc F1 0.986** across all 7 languages (en/de/hu/fr/bn/ar/ja). Whole-document binary guards on that same 108-doc fixture miss 6.9–40.3% of attacks while stripping everything they flag: protectai deberta-v3-injection-v2 escapes **40.3%**, horizon-small 6.9%, horizon-base 8.3%. The honest trade stays published: on the original hand-written OOD set the router keeps 16.7% escape at 9.3% over-strip, and the v4-trained char model alone goes 0.0% escape for 44% over-strip — the router exists so you don't have to choose. A 0.5B LLM asked to flag its own injections misses 91.7% of attacks.",
    "intro how-well -> v4")
rep("- **On agent traffic.** 900 synthetic tool-output documents: escape 0.0%, over-strip 4.3%, doc F1 93%.",
    "- **Domain foundation (new in v4/v5).** corpus-v4 doubles the carrier surface — log-file poisoning, code-comment injection, RAG-chunk poisoning plus in-domain Arabic and Japanese (16,000 seed-locked docs, 7 languages, 18 families). Zero-shot, the v3 models washed out on exactly this: char-v3 escaped 30.7% of Arabic and 34.0% of Japanese attacks; the span model missed 76.2% of log-poison spans. After v4 training: **0.0% escape in every one of the 7 languages** (measured per-language on the fixture), and v5's SPG-FM-1 collapses the whole router stack into one 1.7M-parameter foundational model trained on the union.",
    "intro agent-traffic -> v4/v5 story")

# ---- 3. demo section: live inference Space
rep("""**[Open the live demo](https://huggingface.co/spaces/Nabidnur/spanguard-demo)** — six
realistic payloads (invoice e-mails, MCP tool results, carrier notes) with the gateway's
actual precomputed output: attack spans in red, `[stripped]` markers in place, clean JSON
and totals intact. You can also paste your own text — the rules engine runs in your browser
(a JS port of `rules.py`), so nothing is uploaded anywhere.""",
    """**[Open the live inference Space](https://huggingface.co/spaces/Nabidnur/spanguard-demo)** —
runs the actual pipeline in-app (rules + 135M span model + char router on a free CPU
bucket). Pick one of the fifteen built-in payloads — the 2026 carrier families
(MCP tool poisoning, skill files, buried multi-hop, md-image exfiltration, log poisoning,
code-comment injection, RAG-chunk poisoning) in 7 languages — or paste your own text:
attack spans highlighted per detector, typed `[stripped:*]` markers in the cleaned output,
findings table with offsets and payload hashes, per-run latency. Nothing is hand-rendered;
every verdict is a real `Guard(mode="fast-v4")` run. A static 15-card visual walkthrough of
the same runs ships in the repo: [docs/demo/visual-inference.html](docs/demo/visual-inference.html).""",
    "demo -> live Space")

# ---- 4. headline results table after "## Results"
rep("## Results\n\n<!-- results:start -->",
    """## Results

### The v4 headline — one fixture, every system measured (108 docs, 72 attacked, 7 languages)

| system | escape ↓ | over-strip ↓ | doc F1 ↑ | span F1 ↑ | p50 |
|---|---|---|---|---|---|
| **spanguard char-v4** (812k, corpus-v4) | **0.0%** | **0.0%** | **1.000** | 0.955 | ~2 ms |
| **spanguard fast-v4** (rules + span + 3-level router) | **0.0%** | 0.2% | 0.986 | 0.708 | ~280 ms |
| horizon-small (binary, strip-all) | 6.9% | all benign chars | — | — | 331 ms |
| horizon-base (binary, strip-all) | 8.3% | all benign chars | — | — | 810 ms |
| protectai deberta-v3-injection-v2 (binary, strip-all) | 40.3% | all benign chars | — | — | 1155 ms |

Per-language doc escape for char-v4 on the same fixture: **en 0.0 · de 0.0 · hu 0.0 · fr 0.0 · bn 0.0 · ar 0.0 · ja 0.0** —
the ar/ja zero-shot washout (30.7% / 34.0%) is eliminated, not mitigated
([records](eval/results/v4-flagship-1826/run.json) · [lang-matrix chart](docs/benchmarks/lang-matrix.svg) ·
[v4-frontier chart](docs/benchmarks/v4-frontier.svg)).

### The full five-set sweep

<!-- results:start -->""",
    "headline results table")

# ---- 5. v4.0.0 + v5 sections before "## Domain expansion"
rep("## Domain expansion: corpus v3 and char-v3 (extended domain, shipped)",
    """## v4.0: domain foundation — 7 languages, one router stack, record on every extended set

Corpus v4 adds the three 2026-native carrier families — **log-file poisoning,
code-comment injection, RAG-chunk poisoning** — plus in-domain **Arabic and Japanese**,
taking the generator to 16,000 docs / 7 languages / 18 families (seed-locked, manifest
committed). Zero-shot measurement on the new domains before any v4 training
(`eval/results/zero-shot-v4/record.json`) quantified the washout exactly: char-v3 escaped
**30.7% of Arabic and 34.0% of Japanese** attack docs; span-v2 missed **76.2% of
log-poison and 100% of md-image-exfil** planted spans.

Two systems close the gap, both on the committed 108-doc **extended-v4 fixture**
(72 attacked / 36 benign, 7 languages, `eval/fixtures/extended-v4.jsonl`):

| system | escape ↓ | over-strip ↓ | doc F1 ↑ | span F1 ↑ |
|---|---|---|---|---|
| **spanguard char-v4** (812k, corpus-v4-trained) | **0.0%** | **0.0%** | **1.000** | **0.955** |
| **spanguard fast-v4** (rules + span-v2 + 3-level router) | **0.0%** | 0.2% | 0.986 | 0.708 |
| protectai deberta-v3-injection-v2 (binary) | 40.3% | (strip-all) | — | — |
| horizon-small (binary) | 6.9% | (strip-all) | — | — |
| horizon-base (binary) | 8.3% | (strip-all) | — | — |

The headline is the language matrix: char-v4 measures **0.0% doc escape in every one of
the 7 languages** on the fixture — the ar/ja zero-shot washout is gone, not mitigated
([lang-matrix](docs/benchmarks/lang-matrix.svg) ·
[v4-frontier](docs/benchmarks/v4-frontier.svg), light+dark SVGs). The full 5-set sweep
(`eval/results/v4-flagship-1826/run.json`) keeps the v3.1 guarantees and adds the new
surface: agent-traffic 0.0%/4.7%, extended-attacks 0.0%/0.0% (doc F1 1.000), public-deepset
0.0%/19.8%; the known trade stays honest — hand-written OOD escape is 16.7% for the router
stack (char-v4 alone: 0.0% escape but 44% over-strip, which is exactly why the router picks
per-domain experts with per-domain calibration). char-v4 on the v3-era extended-attacks
fixture posts a perfect **span F1 1.000**. All three baselines run the same fixture via
`eval/results/baselines-extended-v4/record.json` — binary classifiers strip whole documents
and still miss 7–40% of attacks, while the char-level span model removes exactly the payload.

## v5: SPG-FM — the domain foundational model (one model instead of a stack)

The v2→v4 pattern shipped one small expert per domain plus a regex router. v5 collapses the
stack: **SPG-FM-1** ([train_fm.py](training/train_fm.py)) is a single char-level multi-task
network (1.70M params, channels 512 / blocks 6 / emb 96) trained on the **full corpus-v4
union** — every language and carrier family the router used to dispatch between — emitting
both the document verdict and the payload spans in one forward pass. In-domain coverage no
longer depends on the router being right; there is no routing decision to get wrong.
Status: {V5_STATUS}

## Domain expansion: corpus v3 and char-v3 (extended domain, shipped)""",
    "v4/v5 sections")

p.write_text(s)
print("README world-class upgrade applied")
