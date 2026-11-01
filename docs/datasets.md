# Datasets

All data is **fictional** and generated deterministically; no personal data, no scraped text.
Every split's counts and SHA-256 are committed in `data/corpus-manifest.json`.

## Corpus (`training/gen_corpus.py`)

| split | docs | attacked | benign traps | clean |
|---|---:|---:|---:|---:|
| train (seed 101) | 4,200 | 2,574 | 448 | 1,178 |
| dev (seed 202) | 450 | 274 | 50 | 126 |
| test (seed 303) | 900 | 479 | 109 | 312 |

- **9 tool-output formats:** JSON API, NDJSON logs, email, CSV, markdown table, code+REPL,
  web page, DB row, support ticket.
- **10 attack families:** override, system/role impersonation, forged tool results,
  secret hunting, exfiltration (URL/email), base64, hex, invisible-unicode smuggling,
  homoglyph/mixed-script, note-to-the-assistant narrative.
- **Benign traps:** attack-shaped text that is *not* an attack (changelogs quoting payload
  phrases, security-training pages, policy text, image blobs) — trained and scored as clean.
- **Languages:** English 60% / German 20% / Hungarian 20% per split.

## Teacher labeling (`training/label_teacher.py`)

Muse Spark Open (`meta-models/muse-spark-open-1026`, Baseten) independently re-labels a
stratified sample (1,000 train + 150 dev): it must quote each attack span exactly. Merged
labels = planted gold ∪ teacher-found spans. Agreement, misses and the exact token cost are
committed in `data/corpus/labelled/manifest.json` — the distillation is *recorded*, not claimed.

## Eval fixtures (committed, in `eval/fixtures/`)

| set | docs | what it is | why it exists |
|---|---:|---|---|
| `handwritten-{en,de,hu}.jsonl` | 62 | hand-written attacks, zero template overlap, plus benign look-alikes | the number to trust: no generator shared with training |
| `agent-traffic.jsonl` | 900 | the corpus test split (seed 303, disjoint from train/dev) | in-distribution volume |
| `public-deepset.jsonl` | 452 | stratified sample of `deepset/prompt-injections` (user prompts) | external generalization check, different channel |

Document-hash decontamination: fixtures and test split are excluded from training data
(different seeds; verified by content hash at label-merge time).
