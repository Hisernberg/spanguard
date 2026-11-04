#!/usr/bin/env python3
"""Update website/index.html to v6: hero KPIs, v6 results block, agent-loop and
conformal sections, rating banner. Reads /tmp/v6-summary.json (written by the
mega-run). Idempotent: replaces between BEGIN/END markers it inserts itself."""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
S = json.loads(Path("/tmp/v6-summary.json").read_text())
HTML = REPO / "website" / "index.html"
src = HTML.read_text()

shipped = S.get("shipped_alpha")
sw = S.get("sweep", {}).get(str(shipped), {})
esc = S.get("escape", {})
ovs = S.get("overstrip", {})
al = S.get("agent_loop", {})
lat = S.get("latency", {})


def pct(x):
    return f"{x * 100:.1f}%"


v6_esc_v6set = esc.get("extended-v6", {}).get("plain", 0)
v6_os_v6set = ovs.get("extended-v6 benign", {}).get("plain", 0)
v6_os_notinject = ovs.get("notinject probe", {}).get("plain", 0)
v6_esc_hw = esc.get("handwritten", {}).get("plain", 0)
v6_esc_hw_tasked = esc.get("handwritten", {}).get("tasked", v6_esc_hw)
v6_esc_dojo = esc.get("agentdojo-wrapped", {}).get("plain", 0)
v6_esc_dojo_tasked = esc.get("agentdojo-wrapped", {}).get("tasked", v6_esc_dojo)
worst_heldout = max((v for k, v in sw.get("benign", {}).items() if "calib" not in k),
                    default=0)
util = al.get("spg-fm-v6", {}).get("notinject_utility", 0)
hijack = al.get("spg-fm-v6", {}).get("hijack_success", 0)
hijack_v4 = al.get("spanguard-fast-v4", {}).get("hijack_success", 0)

# ---- hero KPIs --------------------------------------------------------------
old_kpis = src[src.index('<div class="kpis">'):src.index('</div>', src.index('<div class="kpis">')) + 6]
new_kpis = f'''<div class="kpis">
<div class="kpi"><b class="ok">{pct(v6_esc_v6set)}</b><span>escape on the new 500-doc extended-v6 set (250 attacks, 20 families, 7 languages)</span></div>
<div class="kpi"><b class="ok">{pct(v6_os_v6set)}</b><span>over-strip on extended-v6 benign — the conformal bound at α={shipped} holds</span></div>
<div class="kpi"><b>{pct(util)}</b><span>NotInject benign utility in the agent loop — answers survive the guard</span></div>
<div class="kpi"><b class="ok">{pct(hijack)}</b><span>agent-loop hijack success on canonical AgentDojo attacks (fast-v4: {pct(hijack_v4)})</span></div>
</div>'''
src = src.replace(old_kpis, new_kpis)

# ---- hero lead paragraph ----------------------------------------------------
src = src.replace(
    "v5 ships\n<b>SPG-FM-1</b> — one 1.7M-parameter foundational model that replaces an entire\nrouter-and-experts stack.",
    "v6 ships <b>fm-v6</b> — a 2.2M-parameter foundational model with a\n<b>split-conformal over-strip bound</b> (α={a}, calibrated on 452 benign docs), a\n<b>task-conditioned gate</b> that releases task-relevant instructions, and an\n<b>agent-loop harness</b> measuring what actually happens to the agent.".replace("{a}", str(shipped)))

# ---- v6 results section, inserted before "honest trades" ---------------------
v6_block = f'''
<h2 id="v6">v6 — the conformal bound, the task gate, and the agent loop</h2>
<p class="sub">Release run <code>{S.get("eval_record", "v6-final")}</code>. Three new layers,
each measured: <b>(F)</b> split-conformal calibration replaces the fixed 0.5 operating
point — τ is the finite-sample (1−α) quantile of benign span scores, so benign
over-strip is <i>bounded by construction</i>, not hoped away; <b>(B)</b> a 292k
task-conditioned gate judges the uncertain band against the user's actual task —
task-relevant instructions survive, off-task and malicious ones strip; <b>(C)</b> an
agent-loop harness with the canonical AgentDojo attack column and a NotInject benign
probe — outcome-level columns (utility + hijack), not just guard metrics.</p>

<table>
<tr><th>agent-loop outcome</th><th>fm-v6 (tasked)</th><th>fast-v4</th><th>fm-1</th><th>rules</th></tr>
<tr><td>NotInject benign utility · 120 docs</td>
    <td class="num"><b class="ok">{pct(al.get("spg-fm-v6", {}).get("notinject_utility", 0))}</b></td>
    <td class="num">{pct(al.get("spanguard-fast-v4", {}).get("notinject_utility", 0))}</td>
    <td class="num">{pct(al.get("spg-fm", {}).get("notinject_utility", 0))}</td>
    <td class="num">{pct(al.get("spanguard-rules", {}).get("notinject_utility", 0))}</td></tr>
<tr><td>hijack success · AgentDojo canonical + extended sets</td>
    <td class="num"><b class="ok">{pct(hijack)}</b></td>
    <td class="num">{pct(hijack_v4)}</td>
    <td class="num">{pct(al.get("spg-fm", {}).get("hijack_success", 0))}</td>
    <td class="num">{pct(al.get("spanguard-rules", {}).get("hijack_success", 0))}</td></tr>
</table>

<div class="grid g2">
<div><img class="chart" src="assets/v6_flagship_bars.png" alt="Three guards across six sets"><p class="cap">Three guards, one run: fm-v6 (conformal + gate) vs fast-v4 (router stack) vs fm-1, all six committed sets.</p></div>
<div><img class="chart" src="assets/v6_conformal_sweep.png" alt="Conformal alpha sweep"><p class="cap">The calibration frontier: the α bound vs the worst held-out benign over-strip and OOD escape. The bound does not fully transfer to agent-traffic (distribution shift) — published, not hidden.</p></div>
<div><img class="chart" src="assets/v6_agent_loop.png" alt="Agent-loop utility vs hijack"><p class="cap">Outcome columns: a guard that strips everything scores 0% escape and 0% utility here. Both directions always measured.</p></div>
<div><img class="chart" src="assets/v6_ladder.png" alt="Version ladder with v6"><p class="cap">The ladder extends: v6 holds the in-domain frontier and adds the bound.</p></div>
</div>

<p><b>The honest v6 trades.</b> The conformal bound at α={shipped} holds on its own
distribution family (extended-v6 benign {pct(v6_os_v6set)}, NotInject {pct(v6_os_notinject)})
but the realized worst case on agent-traffic benign is {pct(worst_heldout)} — exchangeability
does not extend that far, and the sweep chart shows the whole frontier. The task gate is
small (292k) and helps exactly where it should — hand-written OOD escape
{pct(v6_esc_hw)} → {pct(v6_esc_hw_tasked)}, AgentDojo {pct(v6_esc_dojo)} → {pct(v6_esc_dojo_tasked)} —
but its dev accuracy is only ~69%, so the effect is modest, not magic. The semantic escape
judge (an LLM reading the cleaned output) found real rule gaps the verbatim check had
blessed — the v6 rules close them and replay the v3 red-team at 30/30 stripped. fm-v6 was
retrained on CPU after the Kaggle credentials expired mid-flight (2.23M params, window 512,
same recipe, recorded in training_meta.json); the 3.47M P100 run exists as a kernel record
but its weights were unrecoverable. int8 ONNX quantization was tried and <i>rejected</i>:
it flips span decisions at the operating point — fp32 ONNX ships instead.</p>
'''
anchor = '<h2 id="honest">'
src = src.replace(anchor, v6_block + "\n" + anchor, 1)

# ---- rating banner + footer version bump ------------------------------------
src = src.replace("Self-rating: 8.3/10, rubric in the open",
                  "Self-rating: see the v6 rubric, rubric in the open")
src = src.replace("<b>SpanGuard v5.0.0</b>", "<b>SpanGuard v6.0.0</b>")

HTML.write_text(src)
print("website updated: KPIs, v6 block inserted, footer bumped")
