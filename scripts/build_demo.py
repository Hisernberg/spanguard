"""Build the static demo page (HF Space, free tier) for spanguard.

Inputs:
  - /tmp/demo_presets.json (or data/demo_presets.json): REAL guard outputs precomputed
    locally by scripts/make_demo_presets.py (rules + trained span model).
  - docs/benchmarks/*.svg: embedded inline for the results section.

Output: deploy/space/index.html — fully self-contained (inline CSS/JS, no build step).
The page also ports the core rule patterns to JS for live pasting, clearly labeled
"rules engine (JS port)"; the trained-model presets are the gateway's real output.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CHARTS = REPO / "docs" / "benchmarks"
PRESETS = Path("/tmp/demo_presets.json")
if not PRESETS.exists():
    PRESETS = REPO / "data" / "demo_presets.json"

# Faithful JS subset of the rules engine (same regexes, same kinds)
JS_RULES = r"""
const RULES = [
  ["override", /\b(?:ignore|disregard|forget|discard|override)\s+(?:all\s+|any\s+|the\s+|your\s+|their\s+|all\s+of\s+the\s+|any\s+of\s+the\s+|the\s+above\s+|your\s+prior\s+|(?:(?:all\s+)?(?:previous|prior|earlier|above|preceding)[\w\s]{0,20}?))?(?:instructions?|prompts?|directions?|rules?|guidelines?|constraints?|context|message|messages|task)\b/gi],
  ["override", /\b(?:ignoriere|übergehe|uebergehe|missachte)\s+(?:alle\s+|die\s+|deine\s+|sämtliche\s+|saemtliche\s+)?(?:bisherigen\s+|vorherigen\s+|alten\s+|allen\s+)?(?:anweisungen|instruktionen|prüfungen|pruefungen|sicherheitsregeln|regeln|kontrollen|vorgaben)\b/gi],
  ["override", /\bhagy(?:d|j)\s+figyelmen\s+k[íi]v[üu]l\b[^.\n]{0,40}\butasít/gi],
  ["override", /\b(?:from\s+now\s+on|henceforth)\b[^.\n]{0,60}\byou\s+(?:are|must|will|should)\b/gi],
  ["impersonation", /<\|?(?:im_start|im_end|system|endoftext|eot|assistant)\|?>/gi],
  ["impersonation", /<\/?(?:system|assistant|instruction|tool_call|tool_result|function_call|function_response|context)\s*>/gi],
  ["impersonation", /(?:^|(?<=[.;!]\s))\s{0,8}SYSTEM(?:\s+(?:UPDATE|PROMPT|NOTE|MESSAGE))?\s*:/gim],
  ["impersonation", /\[\s*system(?:\s+(?:note|update|message|announcement|instruction))?\s*\]/gi],
  ["impersonation", /\b(?:developer\s+mode|dan\s+mode|do\s+anything\s+now|godmode|unrestricted\s+mode)\b/gi],
  ["exfil", /\b(?:send|post|submit|upload|forward|exfiltrate|transmit|küldd\s+el|sende)\b[^.\n]{0,120}?(?:https?:\/\/|ftp:\/\/|t\.me\/|telegram\.me\/|discord\.gg\/|wa\.me\/|\b(?:curl|wget)\b)/gi],
  ["exfil", /\b(?:include|append|add|embed|reveal|print|show|repeat|copy|quote)\b[^.\n]{0,80}?\b(?:api[\s_-]?key|api[\s_-]?secret|password|passphrase|access[\s_-]?token|auth[\s_-]?token|private[\s_-]?key|credentials?|\.env)\b/gi],
  ["forgery", /(?:TOOL_RESULT|FUNCTION_RESPONSE|EXECUTION_RESULT|TOOL_OUTPUT|SUCCESS_CONFIRMED)\s*[:({\[]/g],
  ["forgery", /[-_=*\s]*(?:BEGIN|END)[\s_-]+(?:TRUSTED|VERIFIED|SAFE|SYSTEM)[\s_-]+[-_=*\s]*/gi],
  ["spoof", /"(?:status|trust_level|clearance|verified|safe)"\s*:\s*"(?:trusted|verified|safe|critical|internal)"/gi],
  ["smuggle", /[\u200b\u200c\u200d\u200e\u200f\u2060\ufeff]/g],
];
function detect(text) {
  const spans = [];
  for (const [kind, rx] of RULES) {
    rx.lastIndex = 0; let m;
    while ((m = rx.exec(text)) !== null) {
      if (m.index === rx.lastIndex) { rx.lastIndex++; continue; }
      spans.push({start: m.index, end: m.index + m[0].length, kind});
    }
  }
  spans.sort((a, b) => a.start - b.start || b.end - a.end);
  const merged = [];
  for (const s of spans) {
    const last = merged[merged.length - 1];
    if (last && s.start < last.end) { last.end = Math.max(last.end, s.end); }
    else merged.push({...s});
  }
  return merged;
}
function stripWith(text, spans) {
  let out = text;
  for (let i = spans.length - 1; i >= 0; i--) {
    out = out.slice(0, spans[i].start) + "[stripped]" + out.slice(spans[i].end);
  }
  return out;
}
"""

PRESET_JS = json.dumps(json.loads(PRESETS.read_text()), ensure_ascii=False) if PRESETS.exists() else "[]"

CHART_FILES = ["banner.svg", "pipeline.svg", "transcript.svg", "frontier-handwritten.svg",
               "heatmap-agent-traffic.svg", "latency.svg", "cost-ledger.svg", "toolcall.svg"]
charts_html = ""
for name in CHART_FILES:
    p = CHARTS / name
    if p.exists():
        svg = p.read_text()
        svg = svg.replace("{ink}", "#1f2328").replace("{muted}", "#59636e").replace("{grid}", "#d0d7de")
        title = name.replace(".svg", "").replace("-", " ")
        charts_html += f'<figure><figcaption>{title}</figcaption>{svg}</figure>\n'

html = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>spanguard — span-level prompt-injection guard (live demo)</title>
<style>
:root {{ --ink:#1f2328; --muted:#59636e; --line:#d0d7de; --green:#1a7f37; --red:#cf222e; --bg:#ffffff; --card:#f6f8fa; }}
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; color: var(--ink); background: var(--bg); line-height: 1.55; }}
.wrap {{ max-width: 980px; margin: 0 auto; padding: 24px 20px 64px; }}
h1 {{ font-size: 28px; margin: 8px 0 4px; }}
h2 {{ font-size: 20px; margin-top: 40px; border-bottom: 1px solid var(--line); padding-bottom: 6px; }}
.sub {{ color: var(--muted); margin: 0 0 18px; }}
.card {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; margin: 14px 0; }}
textarea {{ width: 100%; min-height: 120px; font-family: ui-monospace, 'SF Mono', Menlo, monospace; font-size: 13px; padding: 10px; border: 1px solid var(--line); border-radius: 8px; }}
button {{ background: #238636; color: white; border: 0; border-radius: 8px; padding: 9px 16px; font-size: 14px; font-weight: 600; cursor: pointer; }}
button.sec {{ background: #57606a; }}
.presets {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }}
.presets button {{ background: #eaeef2; color: var(--ink); font-weight: 500; font-size: 12.5px; padding: 7px 12px; }}
.grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
@media (max-width: 760px) {{ .grid2 {{ grid-template-columns: 1fr; }} }}
pre {{ background: #0d1117; color: #e6edf3; padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }}
mark {{ background: #ffd8d3; color: var(--red); padding: 0 2px; border-radius: 3px; }}
.stat {{ font-size: 13px; color: var(--muted); margin-top: 6px; }}
.stat b {{ color: var(--green); }}
figure {{ margin: 18px 0; }} figcaption {{ font-size: 12px; color: var(--muted); margin-bottom: 4px; text-transform: capitalize; }}
svg {{ max-width: 100%; height: auto; }}
.badge {{ display:inline-block; background:#ddf4e4; color:var(--green); border-radius: 20px; padding: 2px 12px; font-size: 12px; font-weight: 600; margin-right: 6px; }}
a {{ color: #0969da; }}
footer {{ margin-top: 48px; color: var(--muted); font-size: 12.5px; border-top: 1px solid var(--line); padding-top: 14px; }}
</style></head><body><div class="wrap">
<h1>🛡️ spanguard</h1>
<p class="sub">Span-level prompt-injection guard for AI agent tool traffic · strip the attack, keep the data</p>
<p>
<span class="badge">rules + 135M multilingual span model</span>
<span class="badge">CPU, no per-doc LLM</span>
<span class="badge">fictional data only</span>
</p>

<h2>Try it</h2>
<div class="card">
<div class="presets" id="presets"></div>
<textarea id="input" placeholder="Paste agent tool output: JSON, logs, tickets, web summaries…"></textarea>
<p>
<button onclick="run()">Strip injections</button>
<button class="sec" onclick="document.getElementById('input').value='';run()">Clear</button>
</p>
<div class="grid2">
<div><b>Before (agent would receive)</b><pre id="before"></pre></div>
<div><b>After spanguard</b><pre id="after"></pre></div>
</div>
<div class="stat" id="stat"></div>
<p class="stat">Live text is scanned by the <b>rules engine (JavaScript port, 15 patterns)</b>.
The preset examples show the <b>real gateway output</b> — rules + the trained 135M span model —
precomputed with the committed pipeline. Run the full model locally: <code>pip install spanguard[model]</code>.</p>
</div>

<h2>How it sits in your stack</h2>
{charts_html}

<h2>Why spans, not one-bit classifiers</h2>
<div class="card">
<p>Binary guards face a dilemma: <b>block</b> the document and the agent loses data it needed,
or <b>pass</b> it and the attack goes through. spanguard returns <i>character spans</i>, so both
failure directions are measured — and published — separately:</p>
<ul>
<li><b>escape rate</b> — attack text still readable after the guard (lower is better)</li>
<li><b>over-stripping</b> — benign data destroyed on clean documents (lower is better)</li>
</ul>
<p>Every number is a committed run record you can re-verify; CI fails on regression.</p>
</div>

<footer>
<a href="https://github.com/Hisernberg/spanguard">Source (Apache-2.0)</a> ·
<a href="https://huggingface.co/Nabidnur/spanguard-span-mdistil">span model</a> ·
<a href="https://github.com/Hisernberg/spanguard/tree/main/eval/results">committed run records</a><br>
Everything on this page is fictional. Do not paste real secrets — this is a public demo.
Built for the Meta Global AI Hackathon 2026.
</footer>
</div>
<script>
const PRESETS = {PRESET_JS};
{JS_RULES}
const presetsEl = document.getElementById('presets');
PRESETS.forEach((p, i) => {{
  const b = document.createElement('button');
  b.textContent = p.title;
  b.onclick = () => {{ document.getElementById('input').value = p.text; run(); }};
  presetsEl.appendChild(b);
}});
function hi(text, spans) {{
  let out = '', pos = 0;
  for (const s of spans) {{
    out += esc(text.slice(pos, s.start)) + '<mark>' + esc(text.slice(s.start, s.end)) + '</mark>';
    pos = s.end;
  }}
  return out + esc(text.slice(pos));
}}
function esc(s) {{ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}
function render(el, text, spans, raw) {{
  const show = raw !== undefined ? raw : text;
  el.innerHTML = spans.length ? hi(show, spans) : esc(show);
}}
function run() {{
  const text = document.getElementById('input').value;
  const preset = PRESETS.find(p => p.text === text);
  let spans, after;
  if (preset && preset.spans && preset.spans.length) {{
    spans = preset.spans.map(s => ({{start: s[0], end: s[1], kind: s[2]}}));
    after = preset.stripped;
  }} else {{
    spans = detect(text);
    after = stripWith(text, spans);
  }}
  render(document.getElementById('before'), text, spans);
  document.getElementById('after').innerHTML = esc(after).replace(/\\[stripped\\]/g, '<b style="color:#cf222e">[stripped]</b>');
  const chars = text.length - (text.length - after.length + spans.length * '[stripped]'.length);
  document.getElementById('stat').innerHTML =
    '<b>' + spans.length + '</b> injection span(s) detected · ' +
    'benign characters kept: <b>' + Math.max(0, Math.round(100 * (after.replace(/\\[stripped\\]/g,'').length) / Math.max(1, text.replace(/\\[stripped\\]/g,'').length))) + '%</b>';
  if (!spans.length) document.getElementById('stat').innerHTML = 'No injection patterns detected — document passes through untouched.';
}}
</script>
</body></html>
"""

out = REPO / "deploy" / "space" / "index.html"
out.write_text(html, encoding="utf-8")
print("wrote", out, f"({out.stat().st_size} bytes, presets: {len(json.loads(PRESETS.read_text())) if PRESETS.exists() else 0})")
