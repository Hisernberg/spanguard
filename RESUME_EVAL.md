# RESUME — evaluation chain (written 2026-11-01 ~20:45 UTC)

## State
Everything DONE and pushed to GitHub (repo Hisernberg/spanguard, latest ~f0b0c14+):
- 3 models on HF (Nabidnur/spanguard-{span,docguard,toolguard}-mdistil), verified loading.
- Records: rules (3 sets), spanguard-fast hero (3 sets), family tool-call (docguard vs toolguard).
- README: intro/results/toolcall blocks injected with real numbers; CI gate passing.
- Demo Space live: https://huggingface.co/spaces/Nabidnur/spanguard-demo (200).
- docs/submission-answers.md + docs/demo-video-script.md + docs/REPRODUCE.md committed.

## The ONLY missing piece: LLM self-detect + open baselines records
A background chain was running when the session cut (llm detect at 320/482 docs,
~27 min left at ~6 docs/min; baselines phase after it, ~20 min). It DIED with the
sandbox. Re-run (RAM-serial, ~50 min total):

```bash
cd /home/z/my-project/spanguard
python3 training/eval_llm_detect.py --agent-limit 300 --public-limit 120   # writes eval/results/llm-self-detect/verdicts.json (~45 min CPU)
python3 training/eval_baselines_local.py                                   # writes baseline records for prompt-guard-2/protectai (~20 min)
python3 training/eval_family_toolcall.py                                   # 2 min: re-run for CLEAN latency (the last run overlapped the LLM job; p50 inflated ~2x)
python3 -m spanguard report    # re-render: fills llm-self-detect + baseline columns/charts in README
git add -A && git commit -m "benchmarks: llm self-detect + open baselines records; final table" && git push origin main
```

## Then finalize
1. Verify the README table now shows llm-self-detect + protectai columns (config tags:
   prompt-guard-2-22m, prompt-guard-2-90m, protectai-deberta-v2, llm-self-detect —
   records must carry EXACTLY these tags; check eval_baselines_local.py writes them).
2. Update docs/submission-answers.md: replace the two "pending" columns with real numbers;
   verify the "strongest open alternative" claim in docs/benchmarks/config.json
   intro_alternative against the ACTUAL protectai record (edit wording to match reality).
3. GitHub release v1.0.0: `scripts/gh_release.sh` or API POST /repos/Hisernberg/spanguard/releases
   (tag v1.0.0 on main, notes: family + measured-in-the-open + honest limits).
4. Copy final docs to /home/z/my-project/download/spanguard/ (submission answers, video
   script, REPRODUCE) — refresh the git bundle into download/ too.
5. Confirm 14/14 tests + `make gate` still pass; CI green.

## Tokens
`.secrets/env` at /home/z/my-project/.secrets/env — GH (works) + HF (works). Baseten: GONE.
