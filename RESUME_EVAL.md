# SpanGuard — v2 track status (2026-11-02 ~19:25 UTC)

## DONE & PUSHED (main @ c2ae201; char model on HF)
- **spanguard-char PUBLISHED**: https://huggingface.co/Nabidnur/spanguard-char
  (0.79M params, char-level multi-task: span head + doc head, boundary-weighted loss x3,
  trained on CPU in ~40 min on corpus-v2, dev-calibrated thr 0.3).
- **corpus-v2 committed generator**: training/gen_corpus_v2.py — 14.4k docs, +French (4 langs),
  extra templates per family, URL/secret payload rotation, hard negatives x3, seeds 404/505/303,
  decontamination 0 leaks. Regen: `python3 training/gen_corpus_v2.py`.
- **fast-v2 ensemble mode** (pipeline.py): structured channel = union (rules+span+char, recall
  dominates); prose channel = symmetric corroboration (span<->char backing ±25 chars,
  standalone span conf >=0.85, char spans >=60 chars stand alone).
- kaggle_train_v2.py (boundary-weighted Trainer for the 135M transformer) committed.

## MEASURED (eval/results/2026-11-02-char-1911/run.json)
| system | handwritten | agent-traffic | public-deepset |
|---|---|---|---|
| spanguard-char (0.79M) | **4.17 esc / 18.3 over** | 0.21 / 2.79 | 0.0 / 33.6 |
| fast-v2 (union variant) | 2.08 esc / 27.1 over | 0.0 / 5.4 | 0.0 / 49.6 |
vs 135M fast: 29.2/11.3 · 0.0/3.3 · 0.0/34.2. The char model BEATS the 135M on OOD escape
(4.17 vs 29.2) — char features generalize where subword models memorize templates.

## IN FLIGHT / NOT DONE
1. **fast-v2 corroboration re-benchmark RUNNING** (nohup, /tmp/fastv2-bench.log, tag
   2026-11-02-fastv2): union -> corroboration on prose to cut the 49.6% public over-strip.
   When it lands: commit record, `python3 -m spanguard report` after adding
   spanguard-char + spanguard-fast-v2 to docs/benchmarks/config.json systems[]
   (copy schema of existing entries; colors: char "#e36209"/dark "#f7b955",
   fast-v2 "#116329"/dark "#57ab5a").
2. **Kaggle 135M-v2 transformer BLOCKED**: KGAT token is read-only for uploads
   (datasets create -> 401; --mine lists empty). kaggle_train_v2.py + scripts/kaggle_rest_upload.py
   are committed; with an upload-capable token: `bash scripts/kaggle_dataset_v2.sh` then
   `push_kernel train-v2 training/train/kaggle_train_v2.py true` (adapt push_kernel call).
3. After records land: render (report), update README table/hero if fast-v2 improves both
   axes, answers "How well" numbers, release v1.1.0 notes, download/ sync + bundle.
4. Final checks: pytest 14/14 (passing), gate (spanguard-char/fast-v2 entries need config
   entries first or gate ignores them), chart spot-check.

## Restart procedure (proven 5x)
token restore (.secrets/env GH ends 8shq) -> clone -> pip torch + ".[model,dev]" ->
snapshot_download 3 mdistil models + spanguard-char -> records already committed.
