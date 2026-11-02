# RESUME — final eval chain state (2026-11-02 ~16:10 UTC)

## SAVED & PUSHED (commit c3ec3fa on GitHub main)
- 3 models on HF (Nabidnur/spanguard-{span,docguard,toolguard}-mdistil), pull with snapshot_download.
- eval/results/llm-self-detect/verdicts.json — **COMPLETE, 482 verdicts** (~60 min CPU; now
  has incremental checkpointing: per-batch writes + resume-safe; smoke-tested).
- All prior records: rules, spanguard-fast hero (2026-11-01-full-1921), family tool-call, gate.
- README intro/results/toolcall blocks carry real numbers. CI gate passing. 25 SVG charts
  verified. Demo Space live (Nabidnur/spanguard-demo). Release script scripts/gh_release.sh ready.
- Tokens: GH_TOKEN in /home/z/my-project/.secrets/env restored to the working one (ends 8shq);
  HF_TOKEN works. Baseten key: gone.

## NOT DONE (chain4 died at baselines phase on sandbox recycle)
1. `training/eval_baselines_local.py` re-run (~15 min). Was mid-run: horizon-base handwritten
   esc 0.062 over 1.438 F1 0.891 — over-strip >1.0 looks like a metric bug in the baseline
   scorer (multi-line char counting?); inspect before publishing.
2. llm HARNESS record failed: ImportError "attempted relative import beyond top-level package"
   from `from ...types import Finding, Result` — the llm-self-detect detector wrapper in the
   eval harness uses a 4-dot relative import; fix to 2 dots or absolute `spanguard.types`,
   then: `python3 -m spanguard eval --detectors llm-self-detect --sets
   handwritten,agent-traffic,public-deepset --tag 2026-11-02-llm` (~2 min).
3. `training/eval_family_toolcall.py` clean-latency re-run (~2 min).
4. `python3 -m spanguard report` final render — fills llm + baseline columns into README.
5. Finalize: fix intro_alternative in docs/benchmarks/config.json to match ACTUAL records;
   fill pending columns in docs/submission-answers.md; `bash scripts/gh_release.sh`;
   commit+push; sync download/ (cp README.md docs + cp -r eval/results/* into
   /home/z/my-project/download/spanguard/; refresh
   /home/z/my-project/download/spanguard-full-history.bundle with `git bundle create ... --all`).
6. Final self-check: pytest 14/14, make gate, README number consistency.

## Sandbox-recycle restart procedure (5th time proven)
```
# restore the working GH token first: it is in the session history; the current
# .secrets/env may hold a stale one (symptom: "Bad credentials" on api.github.com).
# Then:
source /home/z/my-project/.secrets/env
git clone -q "https://x-access-token:${GH_TOKEN}@github.com/Hisernberg/spanguard.git" /home/z/my-project/spanguard
cd /home/z/my-project/spanguard
pip install -q torch --index-url https://download.pytorch.org/whl/cpu && pip install -q -e ".[model,dev]"
python3 -c "
import os
from huggingface_hub import snapshot_download
for n in ['span','docguard','toolguard']:
    snapshot_download(f'Nabidnur/spanguard-{n}-mdistil', local_dir=f'data/models/spanguard-{n}-mdistil', token=os.environ['HF_TOKEN'])"
```
Total remaining: ~25 min compute + ~15 min finalize.
