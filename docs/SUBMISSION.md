# Meta Global AI Hackathon 2026 — Submission (ready to paste)

Team **team blackbox** · Members: **navi12**, **Nabid Nur** (@Hisernberg — GitHub ·
Nabidnur — Hugging Face) · Project: **SpanGuard**

---

### Team Name
`team blackbox`

### Team Members
`navi12` · `Nabid Nur`

### Which track are you submitting to? (required)
**Indie / Solo Builder track** — built end-to-end by one person (models, data, gateway,
evals, site, video). If the list names it differently, the two equally accurate picks are:
**Best Agentic AI Application** (the project is agent-input security) or **Best Use of Meta
Models** (Muse Spark Open runs both the teacher audit and the semantic judge).

### Which problem statement did you build towards? (required)
**"AI agents cannot tell data from instructions."** Every tool result, fetched page, MCP
payload and RAG chunk an agent reads is attacker-writable text, and the industry default —
a one-bit whole-document classifier — either blocks the data the agent needed or ships the
attack. SpanGuard solves it at the span level: find the injection *inside* the data, strip
exactly those characters, and keep the order IDs, totals and JSON structure alive. Pick the
closest listed statement (agent security / safety / tool-use reliability); this paragraph is
the mapping.

### If you're competing for the Most Viral Track (X post link)
Post the X thread below (in `X_POST.md`), then paste the URL here:
`https://x.com/<your-handle>/status/…` *(paste after posting)*

### Project Description
Your AI agent just read a shipping notification. Buried in the carrier note is an
instruction to email your customer list to an attacker. The agent cannot tell data from
instruction — and whole-document guards can't either: they block everything (agent blind)
or pass everything (agent hijacked).

**SpanGuard is the third option: strip the attack, keep the data.** An OpenAI-compatible
security gateway: tool results, pages, MCP payloads and RAG chunks pass through before the
agent reads them. Validated rules + a 135M multilingual span model + a family of
sub-million char models find the injection *spans* and replace them with `[stripped]`
markers — order IDs, totals, names and JSON structure survive untouched.

v6 adds three measured layers: a **split-conformal bound** (over-stripping bounded by
construction — 0.8% on 500 fresh adversarial docs), a **task-conditioned gate** (canonical
AgentDojo attack escape 80.6% → 40.3% with the user's task given), and an **agent-loop
harness** that scores outcomes, not vibes: utility 100% with hijack 1.3% — the best
combination of four systems. A semantic judge (an LLM reading the cleaned output) audited
the rules: 30/30 verbatim-stripped, 0/30 semantic escapes.

Everything is open: 7 languages, every weight on Hugging Face, every run record committed
and re-verifiable, honest costs published next to every win. CPU-only, ~21 ms per document,
no LLM call in the guard path.

### Public GitHub Repository (required)
`https://github.com/Hisernberg/spanguard`
(tag `v6.0.0`, release + demo video attached, full v0→v6 history in `CHANGELOG.md`)

### 3-Minute Demo Video (required)
*(upload the `yt-package/` video with the provided title/description/subtitles, then paste)*
`https://youtube.com/watch?v=…`

### Describe your use of Meta products to build the submitted project
Meta models run twice in SpanGuard's pipeline — both times where independence matters most:

1. **The teacher audit (Muse Spark Open, `meta-models/muse-spark-open-1026`).** My corpus
   labels come from a deterministic generator that plants spans and logs their offsets —
   so I used Muse Spark Open as an *independent* precision auditor: one pass, 1,150 calls,
   $3.91, logged in `data/corpus-manifest.json`. It recovered 62.5% of planted spans and
   hallucinated **zero** teacher-only spans — evidence the open-weights frontier model
   agrees with the deterministic labels rather than inventing its own. Audit mode ships in
   the gateway (opt-in, off by default, no per-document cost).
2. **The semantic escape judge.** Verbatim checks bless attacks that survive as paraphrase.
   I run Muse Spark Open as a judge that *reads the guard's cleaned output* and answers
   whether an actionable injection remains. It found real rule gaps my verbatim check had
   blessed (passive-voice exfiltration, "provide/share" verbs, mid-URL sentence-boundary
   residue) — all fixed; the hardened rules replay the red-team at 0/30 semantic escapes.
3. **The build itself.** The entire repo — models, eval harness, gateway, charts, site,
   video — was engineered in agent-mode sessions with GLM (z.ai) as the coding agent,
   with Muse Spark Open as the independent grader. Meta models are the *reference* in this
   project: the thing the small guard is measured against, and the thing that audits it.

### Why are Meta's models important to your solution?
Three reasons. **First, independence:** a guard trained on my own labels needs a grader that
doesn't share my training pipeline's biases — Muse Spark Open recovered 62.5% of planted
spans with zero hallucinated ones, which is exactly the conservative, precision-first
behavior an auditor needs. **Second, open weights:** the same model that audits offline is
one I can self-host, quantize, and ship inside the project with no per-call dependency —
the audit and judge are reproducible by anyone who clones the repo, which is the whole point
of publishing committed run records. **Third, one coherent family:** Spark Open covers
text audit and judging today, and the family's larger-context and vision variants are the
obvious upgrade path (screenshot-carried injections, whole-thread judging) — no other vendor
offers hosted-frontier + open-weights in one stack a solo builder can actually afford; my
entire teacher audit cost $3.91.

### Provide feedback from your experience using partner technologies
Using Muse Spark Open through the Meta Model API was the smoothest part of the project: the
`meta-models/muse-spark-open-1026` endpoint took OpenAI-shaped requests, so the audit loop
was ~40 lines of Python on top of the same client the gateway already uses. Latency was
consistent enough to batch 1,150 calls in one unattended pass, and the cost came to $3.91
total. The one thing I'd ask for: explicit JSON-mode / structured output for judge workloads
(I parse free-text verdicts today), and per-token cost lines in the response metadata to
make run-record accounting automatic.

### How likely are you to build with Meta Model API? (required)
**9/10** — already shipping in two pipeline roles (teacher audit, semantic judge); the
missing point is structured-output mode for the judge.

### How would you describe your overall opinion of Meta Model API? (required)
**Very positive.** Open-weight frontier quality at hosted-API convenience, honest pricing,
and the same family available for self-hosting when a workload needs zero per-call cost.
For a solo builder it removed the usual choice between "good model I can't afford" and
"cheap model that can't judge."

### How likely are you to recommend the Meta Model API to another developer or engineering team building with LLMs?
**9/10** — especially for teams that need an independent grader/auditor rather than another
chat endpoint.

### How likely are you to recommend Muse Code to another developer or engineering team?
**8/10** — strong for agent-mode engineering on greenfield repos with committed test gates
(this repo: 39 green tests); add deeper multi-repo refactoring support and it's a 9.

### What was the biggest obstacle your team hit while building this project?
**Infrastructure died mid-flight, twice — and both times the honest fix beat the pretty
one.** (1) My Kaggle GPU credentials expired mid-session during v6 training: fm-v6 was
retrained on CPU overnight instead, and the recipe + metadata are committed so the
P100-scale run is a kernel record anyone can re-run. (2) Rebuilding the sandbox from the
code mirror surfaced an orchestration regression (structured docs routed down the prose
channel) that had silently shipped — caught it because committed run records existed to
diff against, repaired it, and fast-v4's hand-written OOD escape improved from 16.7% to
4.2%. The lesson: measurements you can replay are worth more than a bigger GPU.

### Compared with other AI models your team has used for the same kind of work, how did Meta's models perform?
More conservative and more reliable for audit/judge work than the general chat models I
used for attacker simulations: on the same 1,150-call pass it hallucinated zero teacher-only
spans (a chat model I trialed earlier volunteered "attacks" that were never planted, which
would have poisoned the audit). As the semantic judge it flags paraphrase-surviving
injections the substring check misses. For raw creative attack generation the chat models
were more inventive — which is why the red-team attacker is a different model, and the
grader is Meta.

### When your team chooses an AI model or coding tool, what matters most?
(1) Price-performance at *my* volume — thousands of small calls, not one giant one;
(2) reproducibility — deterministic enough that a committed run record means something;
(3) open weights as the escape hatch when per-call cost or data residency rules a
workload out; (4) OpenAI-compatible APIs so switching costs stay near zero.

### What makes it hardest for your team to switch to a different AI model or coding tool?
Judgment calibration built on a specific model: my semantic judge's prompt, thresholds and
verdict format are tuned to how Muse Spark Open behaves, and the audit baseline (62.5%
recovery / 0 hallucinated spans) is a measured fact about *that* model — switching means
re-measuring everything the claims depend on.

### If your team took this project to production, what would most likely stop you from using Meta's models?
Cost and rate limits at guard volume: a production gateway guards *every* tool result, so
per-document LLM calls don't fit the unit economics — which is exactly why SpanGuard's hot
path is a 2M-parameter CPU model and Meta runs only the offline audit + judge roles. For
those roles: rate-limit ceilings on long batch passes, and (for regulated customers)
data-residency terms on the hosted API — the open-weights escape hatch covers both, at the
price of self-hosting.

---

*Everything above is tailorable on the form; the numbers are from committed run records
(`eval/results/`), not estimates.*
