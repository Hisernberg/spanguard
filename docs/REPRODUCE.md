# Reproducing the benchmarks

Every number in the README comes from a committed run record under `eval/results/`.
Nothing is hand-written; `spanguard report` regenerates the tables and SVGs from
those records, and CI (`make gate`) fails if quality regresses.

## 1. Environment

```bash
pip install -e ".[model,dev]"   # + torch (CPU wheel is fine)
python -c "import spanguard; print('ok')"
```

## 2. Data (deterministic, fictional)

```bash
python training/gen_corpus.py --out data/corpus --train 4200 --dev 450 --test 900
# fixtures are committed: eval/fixtures/*.jsonl (hand-written en/de/hu, agent-traffic, public-deepset)
```

The generator is seed-locked; re-running it reproduces byte-identical files
(hashes in `data/corpus-manifest.json`). No real or scraped data anywhere.

## 3. Run the systems

```bash
# rules-only guard (no model needed)
python -m spanguard eval --detectors spanguard-rules --sets handwritten,agent-traffic,public-deepset

# rules + span model (downloads Nabidnur/spanguard-span-mdistil, or set SPANGUARD_MODEL=/path)
python -m spanguard eval --detectors spanguard-fast --sets handwritten,agent-traffic,public-deepset

# open baselines (strip-all semantics), local CPU
python training/eval_baselines_local.py

# LLM self-detection baseline (local small LLM)
python training/eval_llm_detect.py --agent-limit 300 --public-limit 120

# model family: doc-level + tool-call classifiers on the held-out call set
python training/eval_family_toolcall.py
```

## 4. Render + gate

```bash
spanguard report   # rebuilds README blocks + docs/benchmarks/*.svg from eval/results/
make gate          # CI regression gate against gates.json
```

## Reading the metrics

- **escape rate** — share of planted attack payload spans still fully readable after the
  guard ran (lower is better). This is the leak.
- **over-stripping** — share of benign characters destroyed on clean documents (lower is
  better). A guard that deletes everything escapes 0% and is useless; the frontier chart
  shows both axes at once.
- **doc F1** — document-level attack/ok classification quality.
- **span F1** — IoU≥0.5 match between predicted and gold spans.
- Binary baselines are scored with **strip-all semantics**: a flagged document loses 100%
  of its characters. That is what a one-bit classifier can actually do operationally.
