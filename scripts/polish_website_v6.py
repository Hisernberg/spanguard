#!/usr/bin/env python3
"""Website v6 world-class pass: video section, versions ladder, roadmap DONE
marks, fm-v6 links, team + submission links in footer."""
from pathlib import Path

p = Path("/home/z/my-project/spanguard/website/index.html")
s = p.read_text()

# 1. nav: video link + fm-v6 ---------------------------------------------------
s = s.replace('<span class="links"><a href="#demo">live demo</a>',
              '<span class="links"><a href="#video">video</a><a href="#demo">live demo</a>')
s = s.replace('<a href="https://huggingface.co/Nabidnur/spanguard-fm-1">HF model</a>',
              '<a href="https://huggingface.co/Nabidnur/spanguard-fm-v6">fm-v6</a>')

# 2. hero buttons ---------------------------------------------------------------
s = s.replace('<a class="btn s" href="https://huggingface.co/Nabidnur/spanguard-fm-1">🤗 SPG-FM-1 model</a>',
              '<a class="btn s" href="https://huggingface.co/Nabidnur/spanguard-fm-v6">🤗 fm-v6 model</a>\n'
              '<a class="btn s" href="#video">▶ watch 2:54 demo</a>')

# 3. video section ---------------------------------------------------------------
video = '''
<h2 id="video">The 2:54 demo — hijack, guard, bound, agent loop</h2>
<p class="sub">Eight scenes, real gateway runs, TTS narration, subtitles. Chapters:
<code>0:00</code> the one-message hijack · <code>0:15</code> block-vs-pass dilemma ·
<code>0:30</code> live guard · <code>0:44</code> seven languages · <code>1:12</code> the
conformal bound + task gate · <code>1:39</code> agent-loop outcomes · <code>2:08</code> the
open family · <code>2:35</code> links.</p>
<div class="card" style="margin-top:16px">
<video controls preload="metadata" poster="assets/spanguard-demo-v6-thumb.png"
       style="width:100%;border-radius:10px;background:#010409">
  <source src="assets/spanguard-demo-v6.mp4" type="video/mp4">
  Your browser cannot play embedded video — download it
  <a href="https://github.com/Hisernberg/spanguard/releases/download/v6.0.0/spanguard-demo-v6.mp4">here</a>
  (subtitles included in the repo package).
</video>
<p class="cap" style="margin-top:10px">YouTube-ready package (SRT/VTT subtitles, thumbnail,
title/description/tags) ships in the repo under
<a href="https://github.com/Hisernberg/spanguard/tree/main/docs/yt-package">docs/yt-package/</a>
and on the <a href="https://huggingface.co/Nabidnur/spanguard-suite/tree/main/demo-video">HF suite</a>.</p>
</div>
'''
s = s.replace('\n<h2 id="demo">Live demo', video + '\n<h2 id="demo">Live demo')

# 4. honest trades: v6 outcome ----------------------------------------------------
s = s.replace("""document head that buys record OOD recall fires eagerly on prose it has never seen. This
is the one axis where fm loses to fast-v4, and closing it (task-conditioned stripping,
conformal calibration) is the top v6 item.</p>""",
"""document head that buys record OOD recall fires eagerly on prose it has never seen. v6
attacked exactly this axis with a split-conformal bound (in-family over-strip 0.8% on the
500-doc extended-v6 set) and the task gate — the honest residue is that the bound does not
transfer across distribution shift (~15% realized on agent-traffic benign), and the sweep
is published.</p>""")

# 5. roadmap: shipped marks ---------------------------------------------------------
s = s.replace("""<tr><td><b>B — task-conditioned stripping</b> <span class="pill">top v6 item</span></td><td>fm's 14–45% over-strip axis: feed the user's goal alongside tool output; task-relevant instructions survive, off-task ones get stripped</td></tr>
<tr><td><b>D — taint-linked toolguard</b></td><td>remember stripped spans, block or confirm outbound tool calls whose arguments derive from tainted content — connects span guard and toolguard</td></tr>
<tr><td><b>F — conformal threshold calibration</b></td><td>pick thresholds so benign over-strip stays under a target — a bound, not a hope</td></tr>
<tr><td><b>NotInject + AgentDojo columns</b></td><td>replace the benign-only probe; end-to-end agent-loop harness as standard columns</td></tr>
<tr><td><b>A — adaptive red-team loop</b> <span class="pill">first cut shipped</span></td><td>an LLM attacker rewrites payloads against the live guard for 6 rounds — 25 real mutations, 0 escapes in 30 attempts (substring-verbatim check; semantic judge on the roadmap)</td></tr>""",
"""<tr><td><b>B — task-conditioned stripping</b> <span class="pill ok">shipped in v6</span></td><td>the 292k task gate: AgentDojo escape 80.6% → 40.3%, hand-written OOD 35.5% → 29.0% with the task given</td></tr>
<tr><td><b>F — conformal threshold calibration</b> <span class="pill ok">shipped in v6</span></td><td>split-conformal τ at α=0.1: extended-v6 over-strip 0.8%, full sweep + held-out verification published</td></tr>
<tr><td><b>Agent-loop harness + semantic judge</b> <span class="pill ok">shipped in v6</span></td><td>outcome columns (utility 100% / hijack 1.3%) and an LLM judge reading cleaned output — 0/30 semantic escapes</td></tr>
<tr><td><b>A — adaptive red-team loop</b> <span class="pill">first cut shipped</span></td><td>an LLM attacker rewrites payloads against the live guard for 6 rounds — 25 real mutations, 0 escapes in 30 attempts; v6 added the semantic judge and the hardened rules replay 0/30</td></tr>
<tr><td><b>D — taint-linked toolguard</b> <span class="pill">designed, not built</span></td><td>remember stripped spans, block or confirm outbound tool calls whose arguments derive from tainted content — connects span guard and toolguard</td></tr>
<tr><td><b>Group-conformal calibration</b> <span class="pill">next method step</span></td><td>the α bound does not transfer across distribution shift (~15% on agent-traffic benign); group-conditional conformal is the fix</td></tr>""")

# 6. quickstart fm card ---------------------------------------------------------------
s = s.replace("""<div class="card"><h3 style="margin-top:0">SPG-FM-1 in Python</h3>
<pre>import os
os.environ["SPANGUARD_FM_MODEL"] = "&lt;fm-1 dir&gt;"
from spanguard.detect.pipeline import Guard

r = Guard(mode="fm").guard(text)
r.cleaned   # typed [stripped:*] markers
r.attacked  # document verdict</pre></div>""",
"""<div class="card"><h3 style="margin-top:0">fm-v6 in Python</h3>
<pre>from spanguard.detect.pipeline import Guard

g = Guard(mode="fm-v6", task="email the customer about the delay")
r = g.guard(text)
r.cleaned   # typed [stripped:*] markers, conformal band applied
r.attacked  # document verdict</pre></div>""")

# 7. versions ladder ------------------------------------------------------------------
ladder = '''
<h2 id="versions">The ladder — every version, documented</h2>
<p class="sub">Full history with dates, records and honest costs in the
<a href="https://github.com/Hisernberg/spanguard/blob/main/CHANGELOG.md">CHANGELOG</a>;
tags <code>v1.0.0</code> → <code>v6.0.0</code> are on the repo.</p>
<table>
<tr><th>version</th><th>what shipped</th><th>headline</th></tr>
<tr><td><b>v0</b> prototype</td><td>rule engine, SLM wrapper, OpenAI-compatible gateway</td><td>the mechanism works</td></tr>
<tr><td><b>v1</b></td><td>corpus generator, 62 hand-written fixtures, scorer, CI gate</td><td>measurable from day one</td></tr>
<tr><td><b>v2</b></td><td>span-mdistil-v2 (135M), truth pass, positioning</td><td>teacher audit: 0 hallucinated spans</td></tr>
<tr><td><b>v3</b></td><td>corpus v3 (MCP/skill/buried/md-image + bn), char-v3, red-team loop</td><td>0.4% escape on new families</td></tr>
<tr><td><b>v3.1</b></td><td>domain router, fast-v3 flagship, extended-attacks fixture</td><td>0.0% / 0.0% / doc F1 1.000</td></tr>
<tr><td><b>v4</b></td><td>corpus v4 (16k, 7 languages, log/code/rag), fast-v4 router stack</td><td>0.0% escape in all 7 languages</td></tr>
<tr><td><b>v5</b></td><td>SPG-FM-1 single model + orchestration repair</td><td>span F1 0.917 · OOD 4.2% (repaired)</td></tr>
<tr><td><b>v6</b></td><td>fm-v6 + conformal bound + task gate + agent loop + semantic judge</td><td><b class="ok">0.0% / 0.8% bounded · hijack 1.3%</b></td></tr>
</table>
'''
s = s.replace('\n<footer>', ladder + '\n<footer>')

# 8. footer: team + submission ----------------------------------------------------------
s = s.replace("""<p><b>SpanGuard v6.0.0</b> — built for the Meta Global AI Hackathon 2026 (Indie track, solo
project by Nabid Nur Abrar, <a href="https://github.com/Hisernberg">@Hisernberg</a>).</p>""",
"""<p><b>SpanGuard v6.0.0</b> — built for the Meta Global AI Hackathon 2026 by <b>team
blackbox</b> (navi12 + Nabid Nur Abrar,
<a href="https://github.com/Hisernberg">@Hisernberg</a>).</p>""")
s = s.replace("""<a href="https://github.com/Hisernberg/spanguard">GitHub</a> ·
<a href="https://huggingface.co/Nabidnur/spanguard-suite">HF suite</a> ·
<a href="https://huggingface.co/Nabidnur/spanguard-fm-1">SPG-FM-1</a> ·
<a href="https://huggingface.co/spaces/Nabidnur/spanguard-demo">Space</a> ·
<a href="https://github.com/Hisernberg/spanguard/tree/main/eval/results">run records</a> ·
<a href="https://github.com/Hisernberg/spanguard/blob/main/docs/rating.md">self-rating</a> ·
Apache-2.0""",
"""<a href="https://github.com/Hisernberg/spanguard">GitHub</a> ·
<a href="https://huggingface.co/Nabidnur/spanguard-suite">HF suite</a> ·
<a href="https://huggingface.co/Nabidnur/spanguard-fm-v6">fm-v6</a> ·
<a href="https://huggingface.co/spaces/Nabidnur/spanguard-demo">Space</a> ·
<a href="https://github.com/Hisernberg/spanguard/tree/main/eval/results">run records</a> ·
<a href="https://github.com/Hisernberg/spanguard/blob/main/CHANGELOG.md">v0→v6</a> ·
<a href="https://github.com/Hisernberg/spanguard/blob/main/docs/rating.md">self-rating 9.1</a> ·
<a href="https://github.com/Hisernberg/spanguard/blob/main/docs/SUBMISSION.md">submission</a> ·
Apache-2.0""")

p.write_text(s)
print("website v6 pass complete:", len(s), "bytes")
