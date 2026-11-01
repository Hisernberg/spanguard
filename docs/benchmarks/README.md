# Benchmarks — how they are produced

Every number in the README comes from **committed run records** in `eval/results/`. Nothing is
hand-typed; `spanguard report` reads the records and regenerates the README blocks and every
SVG chart in this directory (light + dark variants).

## Systems

| tag | what | where measured |
|---|---|---|
| `spanguard-fast` | rules + SLM span model, `[stripped]` markers | Kaggle CPU (model), 4 threads |
| `spanguard-rules` | rules only | sandbox / CI (pure stdlib) |
| `prompt-guard-2-22m` / `prompt-guard-2-90m` | Meta's binary classifiers, strip-all semantics | Kaggle GPU node |
| `protectai-deberta-v2` | open binary classifier, strip-all semantics | Kaggle GPU node |
| `llm-self-detect` | Muse Spark Open asked to find + quote attack spans | hosted inference (network incl.) |
| `spanguard-audit` | rules + SLM + LLM audit (opt-in mode) | sandbox + hosted |

Binary classifiers are scored with honest **strip-all** semantics: flagged = 0% of the
document survives; unflagged = 100%. That is exactly how they would run behind a gateway.

## Metrics

- **escape rate** — planted attack payloads still fully readable after the guard ran.
- **over-stripping** — benign characters destroyed on documents with no planted spans.
- **doc P/R/F1** — attacked-document detection; `binary_attack` docs (public set) count here.
- **span F1** — IoU ≥ 0.5 between predicted and gold spans (span systems only).
- **latency p50/p95** — per document, measured where each system ran; disclosed per record.

## Costs

`llm-self-detect` records token usage per call; cost per 1M documents is computed at Baseten
list prices ($1.25/Mtok in, $4.25/Mtok out). Local systems are $0. The teacher-labeling run
for training is a separate ledger in `data/corpus/labelled/manifest.json`.

## Reproduce

```bash
make eval && make report      # rules system + all charts, no GPU needed
# baselines: kaggle kernels push (see scripts/kaggle_push.sh)
# llm baseline: python training/eval_llm_detect.py
```

The CI `eval-gate` job re-runs the rules system on every push and fails if any set regresses
beyond tolerance against the newest committed record (`eval/gates.json`).
