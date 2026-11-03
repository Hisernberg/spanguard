# SpanGuard — v2 track status (2026-11-03 ~02:20 UTC)

## DONE & PUSHED (main)
- **spanguard-char on HF** (0.79M, dual-head char model, CPU-trained 40 min, corpus-v2).
- **corpus-v2 generator committed** (14.4k docs, +fr, templates x2, hard negatives x3, seeds 404/505/303).
- **fast-v2 ensemble** (structure-gated: union on tool output, symmetric corroboration on prose) —
  gateway mode, eval CLI, tests green.
- **Benchmark records committed**: fastv2-corrob-0035 (char: handwritten 4.2 esc/18.3 over — BEST escape
  of all systems; fast-v2: 10.4/14.0 handwritten, 0.0/4.3 agent, 0.0/32.9 public — first system to
  beat fast on public over-strip).
- **Hero switched to fast-v2**; README intro/table, answers doc (4-model family), model family
  section, 29 charts re-rendered. All pushed.

## KAGGLE 135M v2 (kernel spanguard-train-v2, v5 RUNNING)
Root cause of v1-v4 failures found: **Kaggle CLI 2.2.5 renamed the kernel-metadata key**
`dataset_data_sources` → `dataset_sources`; the old key was silently dropped → empty mount.
v5 has BOTH keys + fresh dataset `spanguard-corpus-v2b` (old slug had a broken half-created
state). Script DATA path → /kaggle/input/spanguard-corpus-v2b.
Kernel runs: 4 epochs, boundary-weighted CE (x3 at span edges), batch 32, fp16, ~28k windows.
On COMPLETE: `kaggle kernels output kragglenote2forwork/spanguard-train-v2 -p /tmp/kv2out`
→ copy /tmp/kv2out/spanguard-span-mdistil-v2 → data/models/ → `bash scripts/hf_push_v2.sh`
→ `SPANGUARD_MODEL=$PWD/data/models/spanguard-span-mdistil-v2 python3 -m spanguard.eval.cli
--detectors spanguard-fast-mdistil-v2 --sets handwritten,agent-traffic,public-deepset --tag v2-model`
→ `python3 -m spanguard.eval.report` → docs numbers → release v1.1.0.
(All publish/eval plumbing committed: scripts/hf_push_v2.sh, cli branch, config entry.)

## Tokens in /home/z/my-project/.secrets/env (GH, KAGGLE KGAT_8971...89718... no trailing dot!, HF)
Kaggle auth quirk: CLI 2.2.5 needs `KAGGLE_API_TOKEN` env (kaggle.json works for reads only).
HF publisher needs HF_TOKEN. GH PAT works for clone/push.
