
## 4.0.0 — domain foundation: 7 languages, one router stack, record on every extended set

- **corpus-v4**: 16,000 seed-locked docs, 7 languages (en/de/hu/fr/bn/ar/ja), 18 carrier
  families — new: log-file poisoning, code-comment injection, RAG-chunk poisoning +
  in-domain ar/ja templates. Generator + manifest committed.
- **char-v4** (812k, corpus-v4-trained; https://huggingface.co/Nabidnur/spanguard-char-v4):
  on the 108-doc extended-v4 fixture — 0.0% escape in all 7 languages, 0.0% over-strip,
  doc F1 1.000, span F1 0.955 (v3-era extended-attacks fixture: span F1 1.000).
  Washout it fixes: char-v3 ar 30.7% / ja 34.0% escape; span-v2 log-poison 76.2% /
  md-image 100% span miss.
- **fast-v4** (rules + span-v2 + 3-level char router): 5-set sweep 0.0% escape on
  agent-traffic, extended-attacks, extended-v4; doc F1 1.000 / 0.986 on the extended sets;
  honest trade — handwritten OOD 16.7% escape (char-v4 alone 0.0% but 44% over-strip).
- **baselines on the same fixture** (baselines-extended-v4/record.json): protectai
  deberta-v3-injection-v2 40.3% escape, horizon-small 6.9%, horizon-base 8.3%.
- **charts**: lang-matrix (washout → fix, measured post-v4 row) + v4-frontier
  (all bars on the identical fixture), light+dark SVGs, script reproducible.
- **visual-inference demo**: real fast-v4 runs — 15 cards incl. the new carriers and
  bn/ar/ja (docs/demo/visual-inference.html); interactive Gradio Space app staged in the
  Space repo (account cpu-basic quota currently parks it; static page live).
- **README**: world-class rewrite — headline table, per-language matrix, family evolution
  (v1→v5), live Space link, honest trades kept.
- 26 tests green; ruff clean.
