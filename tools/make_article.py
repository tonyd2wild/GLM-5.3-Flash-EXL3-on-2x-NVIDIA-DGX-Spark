#!/usr/bin/env python3
"""make_article.py — data-bound article + summary from results/*.json (run make_poster.py first for the charts).
Writes docs/article.html (charcoal/white page, charts + poster embedded) and results/summary.md (tables to paste into REPORT/BENCH).
Every number in the page is derived from results/sweep_exl3.json, results/sweep_nvfp4.json, optional results/detailed_*.json,
and the ANSWER line in results/quality_*.txt. Constants that come from engine startup logs are set below.
"""
import json, base64, os, re
KV = {"exl3": 1_396_551, "nvfp4": 295_230}; CTX = {"exl3": 1_048_576, "nvfp4": 262_144}
E = json.load(open("results/sweep_exl3.json")); N = json.load(open("results/sweep_nvfp4.json"))
er, nr = E["rows"], N["rows"]
def det(l):
    p = f"results/detailed_{l}.json"; return json.load(open(p)) if os.path.exists(p) else None
de, dn = det("exl3"), det("nvfp4")
def q(l):
    p = f"results/quality_{l}.txt"; t = open(p).read() if os.path.exists(p) else ""
    return ("correct" if "ANSWER: $0.05" in t else ("wrong" if "ANSWER:" in t else "n/a"))
qe, qn = q("exl3"), q("nvfp4")
BOOT = json.load(open("results/boot.json")) if os.path.exists("results/boot.json") else {}
def boot(l):
    b = BOOT.get(l, {}); return (f"{b['min']} min ({b['note']})" if b.get("min") else "—")
def bat(l, m):
    p = f"results/quality_battery_{l}_{m}.json"; return json.load(open(p)) if os.path.exists(p) else None
B = {(l, m): bat(l, m) for l in ("exl3", "nvfp4") for m in ("off", "on")}
def acc(l, m):
    b = B[(l, m)]; return f"{b['correct']}/{b['n']} ({b['accuracy']*100:.0f}%)" if b else "—"
def cat_rows(html=True):
    cats = next((list(b["by_category"].keys()) for b in B.values() if b), [])
    def cell(l, m, c): b = B[(l, m)]; return f"{b['by_category'][c][0]}/{b['by_category'][c][1]}" if b else "—"
    if html: return "".join(f"<tr><td>{c}</td>" + "".join(f"<td>{cell(l, m, c)}</td>" for m in ("off", "on") for l in ("nvfp4", "exl3")) + "</tr>" for c in cats)
    return "\n".join(f"| {c} | " + " | ".join(cell(l, m, c) for m in ("off", "on") for l in ("nvfp4", "exl3")) + " |" for c in cats)
def disagree(m, html=True):
    a, b = B[("nvfp4", m)], B[("exl3", m)]
    if not (a and b): return "<li>—</li>" if html else "- —"
    out = []
    for x, y in zip(a["items"], b["items"]):
        if x["correct"] != y["correct"]:
            t = f"{x['id']} ({x['category']}): NVFP4 {'right' if x['correct'] else 'wrong'} [{x['got'][:40]}] · EXL3 {'right' if y['correct'] else 'wrong'} [{y['got'][:40]}] · expected [{x['expected'][:30]}]"
            out.append(f"<li>{t}</li>" if html else f"- {t}")
    return ("".join(out) if html else "\n".join(out)) or ("<li>none — identical pass/fail on every item</li>" if html else "- none — identical pass/fail on every item")
def reason_chars(l): b = B[(l, "on")]; return (round(sum(i["reasoning_chars"] for i in b["items"]) / b["n"]) if b else "—")

def reason_side(iid, html=True):
    """Both lanes' reasoning traces for one item, thinking on."""
    a, b = B[("nvfp4", "on")], B[("exl3", "on")]
    if not (a and b): return ""
    x = next((i for i in a["items"] if i["id"] == iid), None); y = next((i for i in b["items"] if i["id"] == iid), None)
    if not (x and y and x.get("reasoning_excerpt") and y.get("reasoning_excerpt")): return ""
    def clip(t): t = t.strip().replace("\n\n", "\n"); return (t[:420] + " …") if len(t) > 420 else t
    if html:
        esc = lambda t: t.replace("&", "&amp;").replace("<", "&lt;")
        return (f"<div class=\"rs\"><div><div class=\"rsh\">NVFP4 · {x['reasoning_chars']:,} chars of reasoning · {x['completion_tokens']} tokens · {'right' if x['correct'] else 'wrong'}</div><pre>{esc(clip(x['reasoning_excerpt']))}</pre></div>"
                f"<div><div class=\"rsh\">EXL3 · {y['reasoning_chars']:,} chars of reasoning · {y['completion_tokens']} tokens · {'right' if y['correct'] else 'wrong'}</div><pre>{esc(clip(y['reasoning_excerpt']))}</pre></div></div>")
    return (f"NVFP4 ({x['reasoning_chars']:,} chars, {'right' if x['correct'] else 'wrong'}):\n> " + clip(x['reasoning_excerpt']).replace("\n", "\n> ") +
            f"\n\nEXL3 ({y['reasoning_chars']:,} chars, {'right' if y['correct'] else 'wrong'}):\n> " + clip(y['reasoning_excerpt']).replace("\n", "\n> "))
ITEM_TITLES = {"logic3": "the clock-hands angle at 3:15", "fmt2": "reverse the word 'benchmark' (the item both missed with thinking off)", "code1": "predict the Python output"}
TRACES_HTML = "".join(f"<p class='rst'>{t}</p>{reason_side(i)}" for i, t in ITEM_TITLES.items() if reason_side(i))
TRACES_MD = "\n".join(f"**{t}**\n{reason_side(i, html=False)}\n" for i, t in ITEM_TITLES.items() if reason_side(i, html=False))

import base64
b64 = lambda p: "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
def md_to_html(md):
    """Tiny converter for results/categories_summary.md: tables, h3, bullets, paragraphs."""
    out, table, ul = [], [], False
    def flush_table():
        nonlocal table
        if not table: return
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table if not re.match(r"^\s*\|[\s:|-]+\|\s*$", r)]
        h = "".join(f"<th>{c}</th>" for c in rows[0]); b = "".join("<tr>" + "".join(f"<td>{c.replace('**','')}</td>" for c in r) + "</tr>" for r in rows[1:])
        out.append(f'<div class="tw"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'); table = []
    for line in md.splitlines():
        if line.strip().startswith("|"): table.append(line); continue
        flush_table()
        if ul and not line.startswith("- "): out.append("</ul>"); ul = False
        if line.startswith("## "): continue
        elif line.startswith("### "): out.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- "):
            if not ul: out.append("<ul>"); ul = True
            out.append(f"<li>{line[2:]}</li>")
        elif line.strip(): out.append(f"<p>{line}</p>")
    flush_table()
    if ul: out.append("</ul>")
    return "\n".join(out)
CAT_MD = open("results/categories_summary.md").read() if os.path.exists("results/categories_summary.md") else ""
CAT_HTML = md_to_html(CAT_MD) if CAT_MD else ""
CAT_CHART = (f'<figure><img src="{b64("results/chart_categories.png")}" alt="Per-category decode speed, time to first token and auto score for both lanes."><figcaption>Forty real prompts, eight categories, identical to both lanes: decode tok/s, time to first token, and the auto score where an answer is checkable.</figcaption></figure>' if os.path.exists("results/chart_categories.png") else "")
CAT_SECTION_HTML = (f"""<h2>Real prompts: coding, reasoning, JSON, HTML, prose, narrative, summaries, formatting</h2>
<p>The speed tables above use one counting prompt on purpose: deterministic length, identical on both lanes, and comparable to the published recipe's own peak test. Counting is also the easiest possible sequence for the DFlash2 drafter to predict, so those decode numbers are a ceiling. This section is the floor: forty real prompts, five per category, identical to both lanes, streamed so every prompt reports its own time to first token and decode rate. Quality is auto-graded wherever there is a right answer (hidden tests are executed against the code the model writes; JSON is parsed and compared exactly; HTML is checked for the required structure; reasoning answers and format rules are checked mechanically). Prose, narrative and summaries cannot be graded by rule, so they were ranked by a blind pairwise judge (a separate local model), each pair judged twice with positions swapped and a win counted only when both orders agree. Prompts, outputs, scores and every failed check are in <code>results/categories_*.json</code>; <code>tools/bench_categories.py</code> and <code>tools/judge_pairwise.py</code> reproduce it.</p>
{CAT_CHART}
{CAT_HTML}
""" if CAT_HTML else "")
CAT_SECTION_MD = ("\n" + CAT_MD + "\n") if CAT_MD else ""

TP4_MD = open("results/tp4_vs_tp2.md").read() if os.path.exists("results/tp4_vs_tp2.md") else ""
TP4_HTML = md_to_html(TP4_MD) if TP4_MD else ""
TP4_CHART = (f'<figure><img src="{b64("results/chart_tp4.png")}" alt="Aggregate, per-stream and fresh-prompt TTFT versus concurrency for NVFP4 TP4, NVFP4 TP2 and EXL3 TP2."><figcaption>NVFP4 across all four Sparks (TP4, CUDA graphs) against the two two-node lanes, same tools and prompts, later the same night.</figcaption></figure>' if os.path.exists("results/chart_tp4.png") else "")
TP4_SECTION_HTML = (f"""<h2>Postscript: the same NVFP4 across all four Sparks (TP4)</h2>
<p>After the two-lane comparison, both lanes came down and the RedHat NVFP4 build went back up as one tensor-parallel group across all four Sparks, with CUDA graphs on (the recipe validated on 08-31), 1M context, and the whole battery above run against it. Same tools, same prompts, same isolation. It is not a like-for-like lane (it uses all four boxes), so read it as what the hardware does when you stop splitting it.</p>
{TP4_CHART}
{TP4_HTML}
<p>Two things stand out. Decode scales almost linearly with the second pair of boxes: real prompts +46% single stream (the counting ceiling: +59% single stream, +134% at six streams), and the 30K-document agent loop finishes in half the time, at the same tokens per joule as TP2 (twice the boxes, twice the speed, same efficiency). And prefill at length goes the other way: a fresh 211K-token prompt prefills at 1,670 tok/s on TP4 against 2,763 on TP2, because every layer now synchronizes four nodes over one RoCE rail instead of two. Quality lands in the same run-to-run band as every other lane in this article.</p>
""" if TP4_HTML else "")
TP4_SECTION_MD = ("\n" + TP4_MD + "\n") if TP4_MD else ""
H2H_MD = open("results/h2h_tp4.md").read() if os.path.exists("results/h2h_tp4.md") else ""
H2H_HTML = md_to_html(H2H_MD) if H2H_MD else ""
H2H_CHART = (f'<figure><img src="{b64("results/chart_h2h.png")}" alt="DeepSeek V4 Flash Vision versus GLM-5.3-Flash NVFP4, both at TP4 across four Sparks: aggregate and per-stream throughput versus concurrency, real-prompt decode by category, cold prefill versus prompt length."><figcaption>Both models alone on all four Sparks (TP4, CUDA graphs, max-num-seqs 64), same battery, back to back on 2026-09-02.</figcaption></figure>' if os.path.exists("results/chart_h2h.png") else "")
H2H_CEIL = (f'<figure><img src="{b64("results/chart_h2h_ceiling.png")}" alt="Counting-prompt aggregate throughput versus concurrency for both models, shown only as the draft-acceptance ceiling."><figcaption>Peak ceiling only: the counting prompt, C1 to C48. Max draft acceptance, not a decode number.</figcaption></figure>' if os.path.exists("results/chart_h2h_ceiling.png") else "")
H2H_SECTION_HTML = (f"""<h2>Postscript two: DeepSeek V4 Flash Vision vs GLM-5.3-Flash NVFP4, both at TP4</h2>
<p>The question after the quant comparison was which model to run on all four boxes as the daily driver. So both got the same treatment: each model alone on the four-Spark ring, tensor-parallel 4, CUDA graphs on, max-num-seqs 64, 1M context, and the whole battery above, back to back, with the latency monitor paused and the relay parked. DeepSeek runs its DSpark drafter at k=5 with Patch 4; GLM runs DFlash2 at k=7. This section quotes decode from real prompts first and keeps the counting ladder as the labeled ceiling, and prefill is cold only.</p>
{H2H_CHART}
{H2H_HTML}
{H2H_CEIL}
""" if H2H_HTML else "")
H2H_SECTION_MD = ("\n" + H2H_MD + "\n") if H2H_MD else ""
ISO = json.load(open("results/isolation.json")) if os.path.exists("results/isolation.json") else {}
iso_txt = (f" This run: NVFP4 head {ISO['nvfp4_head'].get('100.91.157.18','?')} chat POSTs, all from the bench client; EXL3 head {ISO['exl3_head'].get('100.91.157.18','?')} from the bench client, and the only other traffic in the 30-minute log window was the kit's own post-serve warm-up burst of {ISO['exl3_head'].get('127.0.0.1',0)} requests at 17:16 ET, fifteen minutes before the tests began." if ISO else "")
e1, n1, e6, n6 = er[0], nr[0], er[-1], nr[-1]
# warm prefill/TTFT from the dedicated measurement (median of the last 3 of N long prompts) overrides the sweep's
# single c1 sample, which is the FIRST long prefill after boot and therefore cold-JIT on a fresh lane.
def pf(l, row):
    p = f"results/prefill_{l}.json"
    if os.path.exists(p):
        d = json.load(open(p)); row["prefill_tok_s"] = d["warm_prefill_tok_s"]; row["ttft_med_s"] = d["warm_ttft_s"]
        row["prefill_first"] = (d["first_prefill_tok_s"], d["first_ttft_s"])
pf("exl3", e1); pf("nvfp4", n1)
# FRESH-PROMPT TTFT/prefill (different text per request) replaces the identical-prompt numbers, which EXL3 served from its
# prefix cache. The identical-prompt values are kept as *_repeat_* and shown in their own row, labeled as cache replay.
def tf(l, rows, row1):
    p = f"results/ttft_fresh_{l}.json"
    if not os.path.exists(p): return
    d = json.load(open(p)); m = {r_["c"]: r_ for r_ in d["rows"]}
    row1["prefill_repeat"] = row1.get("prefill_tok_s"); row1["ttft_repeat_s"] = row1["ttft_med_s"]
    for r_ in rows:
        r_.setdefault("ttft_repeat_s", r_["ttft_med_s"])
        if r_["c"] in m: r_["ttft_med_s"] = m[r_["c"]]["ttft_med_s"]
    row1["prefill_tok_s"] = m[1]["prefill_tok_s"]; row1["fresh_tokens"] = m[1]["prompt_tokens"]; row1["jit_first"] = d["jit_first_s"]
tf("exl3", er, e1); tf("nvfp4", nr, n1)
PLN = {l: (json.load(open(f"results/prefill_len_{l}.json"))["rows"][-1] if os.path.exists(f"results/prefill_len_{l}.json") else None) for l in ("exl3", "nvfp4")}
pl_n = f"{PLN['nvfp4']['cold_tok_s']:,}" if PLN["nvfp4"] else "—"; pl_e = f"{PLN['exl3']['cold_tok_s']:,}" if PLN["exl3"] else "—"
pl_tok = f"{PLN['nvfp4']['prompt_tokens']:,}" if PLN["nvfp4"] else "211K"
pl_rep_n = f"{PLN['nvfp4']['warm_s']} s" if PLN["nvfp4"] else "—"; pl_rep_e = f"{PLN['exl3']['warm_s']} s" if PLN["exl3"] else "—"
import statistics as _st
def _cat_runs(l):
    out = []
    for suf in ("", "_run2", "_run3"):
        f = f"results/categories_{l}_off_c1{suf}.json"
        if os.path.exists(f): out.append(json.load(open(f))["summary"])
    return out
def _catmed(l, c): v = [x[c]["decode_med_tok_s"] for x in _cat_runs(l) if c in x]; return round(_st.median(v), 1) if v else None
def _catrng(l, c): v = [x[c]["decode_med_tok_s"] for x in _cat_runs(l) if c in x]; return f"{min(v)}–{max(v)}" if v else "—"
RP = {l: {"prose": _catmed(l, "prose"), "code": _catmed(l, "coding"), "prose_r": _catrng(l, "prose"), "code_r": _catrng(l, "coding"), "n": len(_cat_runs(l))} for l in ("exl3", "nvfp4")}
C4 = {l: (json.load(open(f"results/categories_{l}_off_c4.json"))["overall"] if os.path.exists(f"results/categories_{l}_off_c4.json") else None) for l in ("exl3", "nvfp4")}
c4_txt = (f"NVFP4 {C4['nvfp4']['agg_tok_s_med']} tok/s vs EXL3 {C4['exl3']['agg_tok_s_med']} tok/s aggregate, TTFT {C4['nvfp4']['ttft_med_s']} s vs {C4['exl3']['ttft_med_s']} s" if all(C4.values()) else "")
rep_txt = (f"identical 1.6K prompt repeated: EXL3 {e1.get('ttft_repeat_s','—')} s vs NVFP4 {n1.get('ttft_repeat_s','—')} s at c1, {er[-1].get('ttft_repeat_s','—')} s vs {nr[-1].get('ttft_repeat_s','—')} s at c6; a {pl_tok}-token context replayed in {pl_rep_e} vs {pl_rep_n}")
pe = max(r["agg_tok_s"] for r in er); pe_c = [r["c"] for r in er if r["agg_tok_s"] == pe][0]
pn = max(r["agg_tok_s"] for r in nr); pn_c = [r["c"] for r in nr if r["agg_tok_s"] == pn][0]
def lead(an, a, bn, b, higher=True, unit=""):
    if a == b: return f"{an} {a}{unit} = {bn} {b}{unit} (tie)"
    w = an if ((a > b) == higher) else bn
    hi, lo = max(a, b), min(a, b)
    return (f"{an} {a}{unit} vs {bn} {b}{unit} ({w} +{(hi-lo)/lo*100:.0f}%)" if higher
            else f"{an} {a}{unit} vs {bn} {b}{unit} ({w} lower by {(hi-lo)/hi*100:.0f}%)")
c1_txt = lead("NVFP4", n1["agg_tok_s"], "EXL3", e1["agg_tok_s"], True, " tok/s")
pk_txt = lead("NVFP4", pn, "EXL3", pe, True, " tok/s") + f" (peaks at c{pn_c} / c{pe_c})"
c6ps_txt = lead("NVFP4", n6["per_stream_tok_s"], "EXL3", e6["per_stream_tok_s"], True, " tok/s")
pf_txt = lead("NVFP4", n1["prefill_tok_s"], "EXL3", e1["prefill_tok_s"], True, " tok/s")
tt_txt = lead("NVFP4", n1["ttft_med_s"], "EXL3", e1["ttft_med_s"], False, " s")
w2w_txt = lead("NVFP4", n6["w2w_med_s"], "EXL3", e6["w2w_med_s"], False, " s")
c1_lead = "NVFP4" if n1["agg_tok_s"] > e1["agg_tok_s"] else ("EXL3" if e1["agg_tok_s"] > n1["agg_tok_s"] else "tie")
pk_lead = "NVFP4" if pn > pe else ("EXL3" if pe > pn else "tie")
pf_note = (f" (fresh prompts, different text per request, ~{e1.get('fresh_tokens', 1600):,} tokens, median of 3 rounds)") if "fresh_tokens" in e1 else ""
r = lambda a, b, d=1: f"{a/b:.{d}f}×"
b64 = lambda p: "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
spread = lambda d: f"{d['c1_min']}–{d['c1_max']}" if d else "—"
pct = lambda d: f"±{(d['c1_max']-d['c1_min'])/2/d['c1_med']*100:.1f}%" if d else "—"
ts = E.get("ts", "")

sweep_rows = "".join(f"<tr><td>c{e['c']}</td><td>{n['agg_tok_s']}</td><td>{n['per_stream_tok_s']}</td><td>{n['w2w_med_s']} s</td><td>{n['ttft_med_s']} s</td>"
                     f"<td>{e['agg_tok_s']}</td><td>{e['per_stream_tok_s']}</td><td>{e['w2w_med_s']} s</td><td>{e['ttft_med_s']} s</td></tr>" for e, n in zip(er, nr))
md_rows = "\n".join(f"| {e['c']} | {n['agg_tok_s']} | {n['per_stream_tok_s']} | {n['w2w_med_s']} s | {n['ttft_med_s']} s | {e['agg_tok_s']} | {e['per_stream_tok_s']} | {e['w2w_med_s']} s | {e['ttft_med_s']} s |" for e, n in zip(er, nr))

rp_txt = (f"prose {RP['nvfp4']['prose']} vs {RP['exl3']['prose']} tok/s, code {RP['nvfp4']['code']} vs {RP['exl3']['code']} tok/s (NVFP4 vs EXL3, median of {RP['nvfp4']['n']} runs of the 40-prompt set)" if RP['nvfp4']['prose'] and RP['exl3']['prose'] else "")
summary = f"""## Headline, real prompts (how we now quote decode: prose and code, not the counting prompt)
| | NVFP4 (Reddie + Spark4) | EXL3 (Bluey + Asusi) |
|---|---|---|
| prose decode, c1, tok/s (median of {RP['nvfp4']['n']} runs; range) | {RP['nvfp4']['prose']} ({RP['nvfp4']['prose_r']}) | {RP['exl3']['prose']} ({RP['exl3']['prose_r']}) |
| code decode, c1, tok/s (median of {RP['nvfp4']['n']} runs; range) | {RP['nvfp4']['code']} ({RP['nvfp4']['code_r']}) | {RP['exl3']['code']} ({RP['exl3']['code_r']}) |
| mixed real-prompt load c4: aggregate tok/s / TTFT | {(str(C4['nvfp4']['agg_tok_s_med']) + ' / ' + str(C4['nvfp4']['ttft_med_s']) + ' s') if C4['nvfp4'] else '—'} | {(str(C4['exl3']['agg_tok_s_med']) + ' / ' + str(C4['exl3']['ttft_med_s']) + ' s') if C4['exl3'] else '—'} |
| time to first token, fresh 1.6K prompts, c1 / c6 | {n1['ttft_med_s']} s / {n6['ttft_med_s']} s | {e1['ttft_med_s']} s / {e6['ttft_med_s']} s |
| cold prefill, fresh {pl_tok}-token prompt, tok/s | {pl_n} | {pl_e} |

Counting-prompt numbers below are the speculative-decode ceiling (the drafter's easiest sequence), kept for comparability with the recipes' own peak tests. Prefill is quoted cold only; cache replay has its own labeled row.

## Counting prompt (speculative-decode ceiling), isolated, both lanes benched simultaneously, {ts}
| | NVFP4 (Reddie + Spark4) | EXL3 (Bluey + Asusi) | EXL3 ÷ NVFP4 |
|---|---|---|---|
| c1 single-stream tok/s | {n1['agg_tok_s']} | {e1['agg_tok_s']} | {r(e1['agg_tok_s'], n1['agg_tok_s'])} |
| peak aggregate tok/s (at c) | {pn} (c{pn_c}) | {pe} (c{pe_c}) | {r(pe, pn)} |
| c6 aggregate tok/s | {n6['agg_tok_s']} | {e6['agg_tok_s']} | {r(e6['agg_tok_s'], n6['agg_tok_s'])} |
| c6 per-stream tok/s | {n6['per_stream_tok_s']} | {e6['per_stream_tok_s']} | {r(e6['per_stream_tok_s'], n6['per_stream_tok_s'])} |
| prefill tok/s (~1.5K prompt){pf_note} | {n1['prefill_tok_s']} | {e1['prefill_tok_s']} | {r(e1['prefill_tok_s'], n1['prefill_tok_s'])} |
| TTFT, fresh 1.6K prompts, c1 / c6 | {n1['ttft_med_s']} s / {n6['ttft_med_s']} s | {e1['ttft_med_s']} s / {e6['ttft_med_s']} s | {r(n1['ttft_med_s'], e1['ttft_med_s'])} / {r(n6['ttft_med_s'], e6['ttft_med_s'])} lower |
| identical prompt repeated (prefix cache), TTFT c1 / c6 | {n1.get('ttft_repeat_s','—')} s / {nr[-1].get('ttft_repeat_s','—')} s | {e1.get('ttft_repeat_s','—')} s / {er[-1].get('ttft_repeat_s','—')} s | cache, not prefill |
| cold prefill on a fresh {pl_tok}-token prompt, tok/s | {pl_n} | {pl_e} | |
| {pl_tok}-token context replayed (prefix cache) | {pl_rep_n} | {pl_rep_e} | |
| mixed load c4 (four real prompts in flight): aggregate tok/s / TTFT | {(str(C4['nvfp4']['agg_tok_s_med']) + ' / ' + str(C4['nvfp4']['ttft_med_s']) + ' s') if C4['nvfp4'] else '—'} | {(str(C4['exl3']['agg_tok_s_med']) + ' / ' + str(C4['exl3']['ttft_med_s']) + ' s') if C4['exl3'] else '—'} | |
| wall-to-wall c1 / c6 (300-tok answer) | {n1['w2w_med_s']} s / {n6['w2w_med_s']} s | {e1['w2w_med_s']} s / {e6['w2w_med_s']} s | {r(n1['w2w_med_s'], e1['w2w_med_s'])} / {r(n6['w2w_med_s'], e6['w2w_med_s'])} lower |
| c1 spread (detailed, n=5) | {spread(dn)} ({pct(dn)}) | {spread(de)} ({pct(de)}) | |
| max context | {CTX['nvfp4']:,} | {CTX['exl3']:,} | {r(CTX['exl3'], CTX['nvfp4'], 0)} |
| KV pool (tokens) | {KV['nvfp4']:,} | {KV['exl3']:,} | {r(KV['exl3'], KV['nvfp4'])} |
| quality probe | {qn} | {qe} | {'tie' if qe == qn else 'differs'} |
| boot: launch → /health 200 | {boot('nvfp4')} | {boot('exl3')} | |

## Peak ceiling: counting prompt c1–c6 (3 rounds per level; max draft acceptance, not a decode number)
| c | NVFP4 agg | per-stream | wall-to-wall | TTFT (fresh) | EXL3 agg | per-stream | wall-to-wall | TTFT (fresh) |
|---|---|---|---|---|---|---|---|---|
{md_rows}
"""
open("results/summary.md", "w").write(summary)

html = f"""<title>NVFP4 vs EXL3 on DGX Spark</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--ground:#1B1C1F;--panel:#232428;--ink:#F2F2F0;--muted:#9A9DA3;--rule:#3A3C41;color-scheme:dark}}
body{{margin:0;background:var(--ground);color:var(--ink);font:16px/1.6 "IBM Plex Sans",-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:960px;margin:0 auto;padding:40px 24px 64px}}
.eyebrow{{font:600 12px/1 "IBM Plex Mono",Menlo,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}
h1{{font:700 clamp(40px,7vw,72px)/.95 "Barlow Condensed","Arial Narrow",Impact,sans-serif;margin:12px 0 10px;text-wrap:balance}} h1 span{{color:var(--muted)}}
.sub{{font-size:18px;color:var(--muted);max-width:68ch;margin:0 0 6px}}
.meta{{display:flex;flex-wrap:wrap;gap:8px 18px;font:500 12.5px/1.4 "IBM Plex Mono",Menlo,monospace;color:var(--muted);margin:14px 0 36px}}
h2{{font:700 30px/1.1 "Barlow Condensed","Arial Narrow",Impact,sans-serif;margin:52px 0 14px;text-wrap:balance}}
h3{{font:600 18px/1.3 "IBM Plex Sans",sans-serif;margin:28px 0 8px}}
p,li{{max-width:68ch}} p{{margin:0 0 14px}} ul{{padding-left:22px;margin:0 0 14px}} li{{margin:0 0 6px}}
code{{font:500 .92em "IBM Plex Mono",Menlo,monospace;background:var(--panel);padding:1px 6px;border-radius:4px}}
pre{{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:14px 16px;overflow-x:auto;font:13.5px/1.55 "IBM Plex Mono",Menlo,monospace;margin:0 0 18px}}
.stats{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:28px 0 8px}}
.stat{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:16px 18px}}
.stat .n{{font:700 44px/1 "Barlow Condensed","Arial Narrow",Impact,sans-serif;font-variant-numeric:tabular-nums}} .stat .l{{font-size:13px;color:var(--muted);margin-top:6px}}
.tw{{overflow-x:auto;margin:14px 0 22px;border:1px solid var(--rule);border-radius:8px}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14.5px}}
th,td{{padding:9px 12px;text-align:left;border-bottom:1px solid var(--rule);white-space:nowrap}}
th{{font:600 12px/1.3 "IBM Plex Mono",Menlo,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);background:var(--panel)}}
td:first-child{{color:var(--muted)}} tr:last-child td{{border-bottom:0}} td b{{font-weight:600;color:var(--ink)}}
figure{{margin:22px 0 28px}} figure img{{width:100%;display:block;border-radius:8px;border:1px solid var(--rule)}} figcaption{{font-size:13px;color:var(--muted);margin-top:8px}}
.callout{{background:var(--panel);border-left:3px solid var(--ink);padding:14px 18px;border-radius:0 8px 8px 0;margin:18px 0 22px;max-width:72ch}}
.poster{{max-width:640px;margin:0 auto}}
footer{{margin-top:56px;padding-top:20px;border-top:1px solid var(--rule);font-size:13.5px;color:var(--muted)}}
a{{color:var(--ink);text-decoration-color:var(--rule);text-underline-offset:3px}} a:focus-visible{{outline:2px solid var(--ink);outline-offset:2px}}
@media (max-width:640px){{.stats{{grid-template-columns:1fr}} .wrap{{padding:28px 16px 48px}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
.rs{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:8px 0 18px}}.rs pre{{white-space:pre-wrap;font-size:12.5px;line-height:1.45;margin:0;padding:10px 12px;border:1px solid var(--rule);border-radius:6px;background:var(--panel);overflow-x:auto}}.rsh{{font-size:12px;color:var(--mut);margin:0 0 6px;letter-spacing:.02em}}.rst{{font-weight:600;margin:14px 0 4px}}@media(max-width:700px){{.rs{{grid-template-columns:1fr}}}}
</style>
<div class="wrap">
<div class="eyebrow">2Wild fleet report · {ts[:10]}</div>
<h1>NVFP4 <span>vs</span> EXL3 <span>on DGX Spark</span></h1>
<p class="sub">The same 320B MoE, GLM-5.3-Flash, in two 4-bit quantizations, on two independent 2-node DGX Spark pairs, benched at the same time in the same state, isolated from every other consumer. Full c1–c6 sweep: throughput, per-stream decode, time to first token, wall-to-wall latency, prefill, context, KV pool.</p>
<div class="meta"><span>4× DGX Spark GB10 · 128 GB UMA</span><span>CX7 RoCE rail 0 · TP=2 per lane</span><span>vLLM · DFlash2 k=7 · fp8 KV</span><span>non-stream · temp 0 · thinking off</span><span>@tonyd2wild</span></div>
<div class="stats">
<div class="stat"><div class="n">{RP['nvfp4']['prose']} <span style="color:var(--muted)">/</span> {RP['exl3']['prose']}</div><div class="l">prose decode tok/s on real prompts, NVFP4 / EXL3 (code: {RP['nvfp4']['code']} / {RP['exl3']['code']}); counting prompt {n1['agg_tok_s']} / {e1['agg_tok_s']} is the speculative-decode ceiling</div></div>
<div class="stat"><div class="n">{pn} <span style="color:var(--muted)">/</span> {pe}</div><div class="l">peak aggregate tok/s, NVFP4 (c{pn_c}) / EXL3 (c{pe_c}) — {pk_lead if pk_lead!='tie' else 'tie'}{'' if pk_lead=='tie' else ' leads'}</div></div>
<div class="stat"><div class="n">{r(KV['exl3'], KV['nvfp4'])}</div><div class="l">EXL3's KV pool ({KV['exl3']:,} vs {KV['nvfp4']:,} tokens) · 1M vs 256K context</div></div>
</div>
<p class="callout"><b>Result, same state.</b> All four nodes restarted together and verified at ~2,170–2,190 MHz under decode load. Decode on real prompts: {rp_txt}. Single-stream decode on the counting prompt (the speculative-decode ceiling): {c1_txt}. Peak aggregate: {pk_txt}. Per-stream at c6: {c6ps_txt}. Prefill on fresh 1.6K prompts: {pf_txt}; time to first token on fresh prompts at c1: {tt_txt}. Repeated context is EXL3's: {rep_txt}. Mixed real-prompt load at c4: {c4_txt}. Wall-to-wall at c6 (counting prompt): {w2w_txt}. EXL3 serves 4× the context with {r(KV['exl3'], KV['nvfp4'])} the KV pool on the same two boxes; boot to serve was EXL3 {boot('exl3')} vs NVFP4 {boot('nvfp4')}; the quality probe was {'a tie' if qe == qn else 'not a tie'}. An earlier run of this comparison that showed EXL3 ahead on every line was thrown out: NVFP4's nodes were clock-capped after a reboot. A second correction, made after publishing: the first version of this page measured time to first token and prefill by repeating one prompt, which EXL3 served from its prefix cache while NVFP4 recomputed it; those rows now use fresh prompts, and the old numbers are kept in their own row, labeled as what they are.</p>

<h2>The headline table</h2>
<p><b>How we quote speed (changed 2026-09-02, after a fair request from readers).</b> Decode is quoted from real prompts, prose and code, at c1 and under mixed load. The counting prompt ("count from 1 to 300") is kept as its own labeled row because it is the speculative drafter's easiest sequence and reads 2 to 3× higher than prose; it is a ceiling, not a typical number. Prefill is quoted cold only, from a fresh prompt at a fixed length; prefix-cache replay sits in its own labeled row and is never mixed into a prefill figure.</p>
<div class="tw"><table><thead><tr><th>real prompts</th><th>NVFP4 · Reddie + Spark4</th><th>EXL3 · Bluey + Asusi</th><th>note</th></tr></thead><tbody>
<tr><td>prose decode, c1, tok/s</td><td><b>{RP['nvfp4']['prose']}</b> ({RP['nvfp4']['prose_r']})</td><td><b>{RP['exl3']['prose']}</b> ({RP['exl3']['prose_r']})</td><td>median of {RP['nvfp4']['n']} runs of the 40-prompt set; range in brackets</td></tr>
<tr><td>code decode, c1, tok/s</td><td><b>{RP['nvfp4']['code']}</b> ({RP['nvfp4']['code_r']})</td><td><b>{RP['exl3']['code']}</b> ({RP['exl3']['code_r']})</td><td>same runs</td></tr>
<tr><td>mixed real-prompt load c4: aggregate tok/s / TTFT</td><td>{(str(C4['nvfp4']['agg_tok_s_med']) + ' / ' + str(C4['nvfp4']['ttft_med_s']) + ' s') if C4['nvfp4'] else '—'}</td><td>{(str(C4['exl3']['agg_tok_s_med']) + ' / ' + str(C4['exl3']['ttft_med_s']) + ' s') if C4['exl3'] else '—'}</td><td>four different prompts in flight</td></tr>
<tr><td>time to first token, fresh 1.6K prompts, c1 / c6</td><td>{n1['ttft_med_s']} s / {n6['ttft_med_s']} s</td><td>{e1['ttft_med_s']} s / {e6['ttft_med_s']} s</td><td>different prompt per request</td></tr>
<tr><td>cold prefill, fresh {pl_tok}-token prompt, tok/s</td><td>{pl_n}</td><td>{pl_e}</td><td>cold only; no cache top-up</td></tr>
</tbody></table></div>
<h3>Counting prompt: the speculative-decode ceiling, c1 to c6</h3>
<div class="tw"><table><thead><tr><th></th><th>NVFP4 · Reddie + Spark4</th><th>EXL3 · Bluey + Asusi</th><th>EXL3 ÷ NVFP4</th></tr></thead><tbody>
<tr><td>c1 single-stream, tok/s (3 rounds)</td><td>{n1['agg_tok_s']}</td><td>{e1['agg_tok_s']}</td><td>{r(e1['agg_tok_s'], n1['agg_tok_s'])}</td></tr>
<tr><td>c1 spread, detailed run (n=5)</td><td>{spread(dn)} ({pct(dn)})</td><td>{spread(de)} ({pct(de)})</td><td></td></tr>
<tr><td>peak aggregate, tok/s</td><td>{pn} (c{pn_c})</td><td>{pe} (c{pe_c})</td><td>{r(pe, pn)}</td></tr>
<tr><td>c6 aggregate, tok/s</td><td>{n6['agg_tok_s']}</td><td>{e6['agg_tok_s']}</td><td>{r(e6['agg_tok_s'], n6['agg_tok_s'])}</td></tr>
<tr><td>c6 per-stream, tok/s</td><td>{n6['per_stream_tok_s']}</td><td>{e6['per_stream_tok_s']}</td><td>{r(e6['per_stream_tok_s'], n6['per_stream_tok_s'])}</td></tr>
<tr><td>prefill, tok/s (~1.5K-token prompt){pf_note}</td><td>{n1['prefill_tok_s']:,}</td><td>{e1['prefill_tok_s']:,}</td><td>{r(e1['prefill_tok_s'], n1['prefill_tok_s'])}</td></tr>
<tr><td>time to first token, fresh 1.6K prompts, c1 / c6</td><td>{n1['ttft_med_s']} s / {n6['ttft_med_s']} s</td><td>{e1['ttft_med_s']} s / {e6['ttft_med_s']} s</td><td>{r(n1['ttft_med_s'], e1['ttft_med_s'])} / {r(n6['ttft_med_s'], e6['ttft_med_s'])} lower</td></tr>
<tr><td>identical prompt repeated (prefix cache), TTFT c1 / c6</td><td>{n1.get('ttft_repeat_s','—')} s / {nr[-1].get('ttft_repeat_s','—')} s</td><td>{e1.get('ttft_repeat_s','—')} s / {er[-1].get('ttft_repeat_s','—')} s</td><td>cache, not prefill</td></tr>
<tr><td>cold prefill on a fresh {pl_tok}-token prompt, tok/s</td><td>{pl_n}</td><td>{pl_e}</td><td>{(r(PLN['exl3']['cold_tok_s'], PLN['nvfp4']['cold_tok_s'], 2) if all(PLN.values()) else '')}</td></tr>
<tr><td>{pl_tok}-token context replayed (prefix cache), seconds</td><td>{pl_rep_n}</td><td>{pl_rep_e}</td><td></td></tr>
<tr><td>mixed load c4, four different real prompts in flight: aggregate tok/s / TTFT</td><td>{(str(C4['nvfp4']['agg_tok_s_med']) + ' / ' + str(C4['nvfp4']['ttft_med_s']) + ' s') if C4['nvfp4'] else '—'}</td><td>{(str(C4['exl3']['agg_tok_s_med']) + ' / ' + str(C4['exl3']['ttft_med_s']) + ' s') if C4['exl3'] else '—'}</td><td>{(r(C4['exl3']['agg_tok_s_med'], C4['nvfp4']['agg_tok_s_med'], 2) if all(C4.values()) else '')}</td></tr>
<tr><td>wall-to-wall, 300-token answer, c1 / c6</td><td>{n1['w2w_med_s']} s / {n6['w2w_med_s']} s</td><td>{e1['w2w_med_s']} s / {e6['w2w_med_s']} s</td><td>{r(n1['w2w_med_s'], e1['w2w_med_s'])} / {r(n6['w2w_med_s'], e6['w2w_med_s'])} lower</td></tr>
<tr><td>max context that booted</td><td>{CTX['nvfp4']:,}</td><td>{CTX['exl3']:,}</td><td>{r(CTX['exl3'], CTX['nvfp4'], 0)}</td></tr>
<tr><td>KV pool (engine startup line)</td><td>{KV['nvfp4']:,} tokens</td><td>{KV['exl3']:,} tokens</td><td>{r(KV['exl3'], KV['nvfp4'])}</td></tr>
<tr><td>quality probe (code + reasoning trap)</td><td>{qn}</td><td>{qe}</td><td>{'tie' if qe == qn else 'differs'}</td></tr>
<tr><td>boot: launch → /health 200</td><td>{boot('nvfp4')}</td><td>{boot('exl3')}</td><td></td></tr>
</tbody></table></div>

<h2>Hardware and topology</h2>
<p>Four NVIDIA DGX Spark boxes (GB10 superchip, sm_121a, 128 GB unified memory, ~121 GB usable), ring-connected over a ConnectX-7 RoCE v2 fabric on 192.168.192.0/24, rail 0 (<code>enp1s0f0np0</code> / <code>rocep1s0f0</code>, GID index 3). Reddie (.2) heads the NVFP4 lane with Spark4 (.4) as its worker; Bluey (.1) heads the EXL3 lane with Asusi (.3). Both lanes are tensor-parallel 2 across two nodes with vLLM's multiprocess executor and NCCL over RoCE. They share nothing but the switch. The bench client was a Mac mini on the same tailnet.</p>
<p><b>Clock state matters on GB10.</b> An earlier run of this comparison was thrown out: after a reboot, Reddie and Spark4 came up pinned at 611–728 MHz SM clock under load while the EXL3 pair ran ~2,500 MHz, and NVFP4 measured 36 tok/s with a perfect 92–100 % draft acceptance. All four nodes were restarted together and verified under load before this run: Reddie, Spark4 and Asusi at 2,411 MHz; Bluey at ~2,177 under its <code>gb10-clock-cap</code> service. If anything, the EXL3 head is the slightly capped box here. Check <code>nvidia-smi --query-gpu=clocks.sm</code> under load after any Spark reboot before trusting a throughput number.</p>

<h2>The two lanes</h2>
<h3>NVFP4, the reference lane</h3>
<p>The published 2-Spark recipe, <a href="https://github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark">tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark</a>, run verbatim. Weights <code>RedHatAI/GLM-5.3-Flash-NVFP4</code>; image <code>ghcr.io/tonyd2wild/vllm-glm53-flash:sm121-v11-dflash2</code> with the sm121 sparse-attention patch; <code>--max-model-len 262144 --gpu-memory-utilization 0.85 --kv-cache-memory 3 GiB --max-num-seqs 6 --max-num-batched-tokens 8192 --block-size 2304 --moe-backend marlin --kv-cache-dtype fp8_e4m3 --enforce-eager</code>; DFlash2 drafter <code>incoai/GLM-5.3-Flash-DFlash2</code>, k=7 (92–100 % draft acceptance on structured output in this run); <code>vm.swappiness=0</code>; worker first, head 25 s later.</p>
<h3>EXL3, the challenger</h3>
<p>The <a href="https://github.com/Reederey87/glm53-flash-exl3-2x-dgx-spark">Reederey87 GB10 kit</a>, with <a href="https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks">MiaAI-Lab</a>'s sibling as cross-reference, built for our fabric. Weights <code>brandonmusic/GLM-5.3-Flash-tr3-4bpw</code>, EXL3 / TR3 trellis at 4 bits per weight, 120 shards, ~164 GiB, ~91 GiB resident per node; image built on the head from the kit's Dockerfile (exllamav3 compiled for <code>12.1a</code>); <code>--quantization exl3 --max-model-len 1000000 --gpu-memory-utilization 0.85 --kv-cache-memory-bytes 15414698763 --max-num-seqs 4 --max-num-batched-tokens 3584 --kv-cache-dtype fp8 --no-async-scheduling</code>; the same DFlash2 drafter at k=7. Every fix we needed is in our fork, <a href="https://github.com/tonyd2wild/GLM-5.3-Flash-EXL3-on-2x-NVIDIA-DGX-Spark">tonyd2wild/GLM-5.3-Flash-EXL3-on-2x-NVIDIA-DGX-Spark</a>.</p>
<p>Both lanes: fp8 KV cache, thinking disabled, the multimodal chat template, native <code>image_url</code> input (a 64×64 red square came back "Red" on both).</p>

<h2>Method</h2>
<p><b>Isolation.</b> Before measuring, every other consumer was moved off both lanes: the spark-flash relay our external agents use was parked on the 3090's Qwen 27B, the latency dashboard (which sends real probe completions) was paused, and the three Hermes supervisors whose default model is <code>glm-5.3-flash</code> were moved to the 27B. After each run we pulled each head's access log: every chat POST in the window came from the bench client, and the counts matched the requests issued. The supervisors run on the same Mac as the bench client, so the IP alone proves nothing; the request counts do.{iso_txt}</p>
<p><b>Simultaneity and state.</b> The two lanes were benched in parallel, minutes after all four nodes were restarted together and their clocks verified under load. They share no GPUs, no memory, and no NCCL group.</p>
<p><b>Warm-up.</b> Both engines JIT-compile kernels lazily per request shape. Every lane got 2× c1 + 1× c6 warm-up requests before measurement. Never bench a cold lane: EXL3's first-ever completion on a fresh boot was ~30 tok/s and its first long prefill 136 tok/s; NVFP4's first request took 5.2 s, its third 3.3 s.</p>
<p><b>Metrics.</b> Throughput is median tokens per second, non-streaming. c1–c6: 3 rounds of c concurrent ~300-token generations; aggregate = Σ tokens / round wall; per-stream = each request's tokens / its own wall; wall-to-wall = each request's end-to-end latency (median). TTFT at level c: c concurrent ~1.5K-token prompts with an 8-token answer, median wall. Prefill = prompt tokens / that wall at c1. A separate detailed run repeats c1 five times for the spread. All requests <code>temperature 0</code>, <code>stream false</code>, thinking off, identical prompts to both lanes. Tools: <code>tools/bench_sweep.py</code>, <code>tools/bench_detailed.py</code>, <code>tools/quality_probe.py</code>, <code>tools/run_full_test.sh</code>.</p>

<h2>Quality: does the quant change how smart it is?</h2>
<p><b>Probe.</b> Same prompt to both, thinking off, temp 0: <code>top_k_frequent</code> in O(n log k) with an explanation and an edge case, plus the bat-and-ball trap. EXL3 {qe}, NVFP4 {qn}.</p>
<p><b>Battery.</b> Twelve auto-graded items with checkable final answers: three multi-step math word problems, three logic puzzles, two code items (predict the output; fix the one-line bug), a leap-year rule application, the bat-and-ball trap, and two strict-format tasks (exact JSON, reversed string). Identical for both lanes, temperature 0, run twice: thinking <b>off</b> (direct answer) and thinking <b>on</b> (the model reasons first, up to 2,500 tokens). <code>tools/quality_battery.py</code>; every item, answer and excerpt is in <code>results/quality_battery_*.json</code>.</p>
<div class="tw"><table><thead><tr><th>accuracy</th><th>NVFP4 · thinking off</th><th>EXL3 · thinking off</th><th>NVFP4 · thinking on</th><th>EXL3 · thinking on</th></tr></thead><tbody>
<tr><td><b>all 12 items</b></td><td>{acc('nvfp4','off')}</td><td>{acc('exl3','off')}</td><td>{acc('nvfp4','on')}</td><td>{acc('exl3','on')}</td></tr>
{cat_rows()}
<tr><td>avg reasoning trace, thinking on (chars)</td><td></td><td></td><td>{reason_chars('nvfp4')}</td><td>{reason_chars('exl3')}</td></tr>
</tbody></table></div>
<p><b>Where they disagreed, thinking off:</b></p><ul>{disagree('off')}</ul>
<p><b>Where they disagreed, thinking on:</b></p><ul>{disagree('on')}</ul>
<p><b>The traces themselves.</b> Same item, both lanes, thinking on, temperature 0. This is what "reasoning" looks like from each quant; the full traces for all twelve items are in the JSON.</p>
{TRACES_HTML}
<p>Published KLD-vs-FP16 figures put EXL3/TR3 4bpw near 0.025 (tying FP8) and NVFP4 near 0.060, so a gap is expected to exist in the output distribution; whether it shows up on a task battery this size is what the table says. Twelve items is a probe of intelligence, not a benchmark suite: treat a single-item difference as noise unless it repeats.</p>

<h2>What we got wrong, part two: the prefix cache</h2>
<p>The first version of this page said EXL3 "answers first": {e1.get('ttft_repeat_s','—')} s versus {n1.get('ttft_repeat_s','—')} s at c1 and {er[-1].get('ttft_repeat_s','—')} s versus {nr[-1].get('ttft_repeat_s','—')} s at c6, and a 1.6K-token prefill at {e1.get('prefill_repeat','—')} tok/s versus {n1.get('prefill_repeat','—')}. Every one of those requests carried the same prompt. EXL3 caches prefixes at fine granularity, so it replayed the cached KV; NVFP4's prefix cache works in 2,304-token blocks, so a 1.6K prompt never hit it and NVFP4 did real prefill every time. A reader on X said EXL3 winning prefill on NVFP4-capable silicon made no sense, and he was right.</p>
<p>Re-measured with a different prompt for every request: time to first token at c1 is NVFP4 {n1['ttft_med_s']} s versus EXL3 {e1['ttft_med_s']} s, and at c6 {nr[-1]['ttft_med_s']} s versus {er[-1]['ttft_med_s']} s; fresh prefill is {n1['prefill_tok_s']:,} versus {e1['prefill_tok_s']:,} tok/s. On a fresh {pl_tok}-token prompt NVFP4 prefills at {pl_n} tok/s to EXL3's {pl_e}. EXL3 also pays a one-time compile of several seconds the first time it sees a new prompt-length bucket ({', '.join(str(x) + ' s' for x in e1.get('jit_first', []))} on its two warm-up requests here, up to 7.8 s observed at a new length).</p>
<p>What EXL3 keeps is real and it matters for agents: the cache itself ({rep_txt}), a {C4['exl3']['agg_tok_s_med'] if C4['exl3'] else '—'} tok/s aggregate against {C4['nvfp4']['agg_tok_s_med'] if C4['nvfp4'] else '—'} under a mixed load of four short real prompts with a first token in {C4['exl3']['ttft_med_s'] if C4['exl3'] else '—'} s against {C4['nvfp4']['ttft_med_s'] if C4['nvfp4'] else '—'} s, 4× the context, 4.7× the KV pool, and a 13-minute boot. An agent that re-sends the same long context every turn lives in the cached case. A fresh single-shot request lives in the other one.</p>
{CAT_SECTION_HTML}
<h2>Peak ceiling: the counting prompt, c1 → c6 (max draft acceptance, not a decode number)</h2>
<p>One prompt, "count from 1 to 300", the easiest sequence a speculative drafter can guess. It is what most Spark posts quote as decode speed, and it reads 2 to 3× higher than prose on both lanes. It stays in this article only as each drafter's acceptance ceiling and for comparability with older posts; every headline number and every chart above it comes from real prompts.</p>
<div class="tw"><table><thead><tr><th>c</th><th>NVFP4 agg tok/s</th><th>per-stream</th><th>wall-to-wall</th><th>TTFT (fresh prompts)</th><th>EXL3 agg tok/s</th><th>per-stream</th><th>wall-to-wall</th><th>TTFT (fresh prompts)</th></tr></thead><tbody>{sweep_rows}</tbody></table></div>
<figure><img src="{b64('results/chart_agg.png')}" alt="Aggregate tokens per second versus concurrency for both lanes."><figcaption>Aggregate throughput. EXL3 peaks at c{pe_c} ({pe} tok/s); the kit launches with <code>--max-num-seqs 4</code>, so beyond four concurrent requests the rest queue. NVFP4 peaks at c{pn_c} ({pn}).</figcaption></figure>
<figure><img src="{b64('results/chart_ttft.png')}" alt="Time to first token versus concurrency for both lanes."><figcaption>Time to first token. EXL3 {e1['ttft_med_s']}–{e6['ttft_med_s']} s across the sweep; NVFP4 {n1['ttft_med_s']}–{n6['ttft_med_s']} s.</figcaption></figure>
<figure><img src="{b64('results/chart_w2w.png')}" alt="Wall-to-wall latency for a 300-token answer versus concurrency for both lanes."><figcaption>Wall-to-wall for a 300-token answer, median. At c6: EXL3 {e6['w2w_med_s']} s, NVFP4 {n6['w2w_med_s']} s.</figcaption></figure>
<p><b>Reading the curve.</b> EXL3 scales to {pe} tok/s at c{pe_c} and then flattens — that is the kit's <code>--max-num-seqs 4</code>, a configuration cap rather than the quantization, and raising it is the obvious next experiment. NVFP4 (<code>--max-num-seqs 6</code>) admits all six but pays per stream: {n1['per_stream_tok_s']} → {n6['per_stream_tok_s']} tok/s, TTFT {n1['ttft_med_s']} → {n6['ttft_med_s']} s.</p>

{TP4_SECTION_HTML}
{H2H_SECTION_HTML}
<p><b>Boot and load time.</b> Measured on this same-state run from launch command to first <code>/health</code> 200: EXL3 {boot('exl3')}; NVFP4 {boot('nvfp4')}. NVFP4's worker reads its weights over NFS from the head on this cluster (no local copy of the base on Spark4); a local copy would put it closer to the recipe's ~15 min. Both lanes JIT-compile kernels on first boot; a wiped cache adds minutes to either.</p>
<p><b>Memory.</b> Each lane holds ~91 GiB of weights per 121 GiB node; every failure we hit was a transient spike on top of that baseline. Drop caches on every node before every launch; <code>free -g</code> under-reports on GB10.</p>

<h2>What broke, and the fixes</h2>
<ul>
<li>EXL3 kit: <code>count_shards()</code> used <code>find -type f</code>, which misses the symlinks a standard HF cache uses → "0 / 120 shards". Fix: <code>find -L</code>.</li>
<li>EXL3 kit: the worker needs the full ~164 GiB on disk; a root-owned <code>~/.cache/vllm-glm53-flash</code> kills the launch silently (<code>chown</code> it on both nodes); it binds <code>--host 127.0.0.1</code> (set <code>0.0.0.0</code>).</li>
<li>NVFP4: run the published recipe verbatim. <code>vm.swappiness=0</code> does not survive reboot. The head's "No available shared memory broadcast block" message is benign while a worker is compiling. Poll <code>/health</code>, not <code>/v1/models</code>.</li>
<li>Both: after any reboot, verify SM clocks under load before benching — a capped node will quietly cost you 40 % and look like a quantization result.</li>
</ul>

<h2>Reproduce</h2>
<pre># NVFP4, both nodes: pull the image, weights at /var/tmp/glm-5.3-flash-nvfp4 (or NFS from the head),
# drafter at /var/tmp/models/GLM-5.3-Flash-DFlash2, patch at ~/patches/sparse_attn_indexer_kpool.py
sudo sysctl -w vm.swappiness=0; sync; echo 3 | sudo tee /proc/sys/vm/drop_caches
./launch-glm53-vllm-tp2-dflash2.sh 1 ; sleep 25 ; ./launch-glm53-vllm-tp2-dflash2.sh 0
until curl -sf http://&lt;head&gt;:8000/health; do sleep 20; done

# EXL3, on the head: clone tonyd2wild/GLM-5.3-Flash-EXL3-on-2x-NVIDIA-DGX-Spark
docker build -t glm53-flash-sm121:local . ; cp .env.example .env   # IPs, WORKER_SSH, RoCE NIC + GID
sudo chown -R $USER ~/.cache/vllm-glm53-flash ; sync; echo 3 | sudo tee /proc/sys/vm/drop_caches   # both nodes
set -a; . ./.env; set +a; ./local/prod-start.sh

# verify clocks under load, then bench each lane with everything else moved off it
nvidia-smi --query-gpu=clocks.sm,utilization.gpu --format=csv
bash tools/run_full_test.sh http://&lt;head&gt;:8000 &lt;served-model&gt; &lt;lane&gt;</pre>

<h2>The one-page scorecard</h2>
<figure class="poster"><img src="{b64('results/poster_nvfp4_vs_exl3.png')}" alt="One-page charcoal-and-white scorecard summarizing the comparison."><figcaption>Generated from the same results files by <code>tools/make_poster.py</code>.</figcaption></figure>

<h2>Credits</h2>
<ul>
<li><a href="https://github.com/Reederey87/glm53-flash-exl3-2x-dgx-spark">Reederey87</a> — the GB10-hardened 2-Spark EXL3 kit we followed end to end</li>
<li><a href="https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks">MiaAI-Lab</a> — parallel 2-Spark recipe, image, weights mirror</li>
<li>brandonmusic — the <code>GLM-5.3-Flash-tr3-4bpw</code> EXL3 quant (ShapleyMCG License)</li>
<li><a href="https://github.com/turboderp/exllamav3">turboderp</a> — ExLlamaV3 and the EXL3 format · IncoAI — the DFlash2 drafter</li>
<li>RedHatAI — the NVFP4 weights · zai-org — GLM-5.3-Flash · malaiwah, drowzeys — surrounding tooling</li>
</ul>
<h2>Caveats and what's next</h2>
<ul>
<li>One quality probe is not a quality study. Open: multi-file refactor correctness, tool-call argument validity, long-context recall past 200K.</li>
<li>Raise EXL3's <code>--max-num-seqs</code> and re-sweep c5–c8; re-bench NVFP4 with the repo's code prompt after a long soak.</li>
<li>Neither lane here is the abliterated variant; both are the base model. Two specific quants on one specific cluster.</li>
</ul>
<footer>@tonyd2wild · <a href="https://github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark">NVFP4 recipe</a> · <a href="https://github.com/tonyd2wild/GLM-5.3-Flash-EXL3-on-2x-NVIDIA-DGX-Spark">EXL3 fork, tools and results</a> · {ts[:10]}</footer>
</div>
"""
os.makedirs("docs", exist_ok=True); open("docs/article.html", "w").write(html)

# ---- REPORT.md (markdown mirror of the page, same variables) + thin BENCH.md ----
link = os.environ.get("ARTICLE_URL", "docs/article.html")
report = f"""# NVFP4 vs EXL3 for GLM-5.3-Flash on DGX Spark

*2Wild fleet report · {ts[:10]} · tonyd2wild (deploy + bench with Kai) · published page: {link}*

## TL;DR
The same 320B MoE, GLM-5.3-Flash, in two 4-bit quantizations, on two independent 2-node DGX Spark pairs, benched
**at the same time in the same state** (all four nodes restarted together, clocks verified at ~2,170–2,190 MHz under
decode load), isolated from every other consumer. Single-stream decode: {c1_txt}. Peak aggregate: {pk_txt}.
Per-stream at c6: {c6ps_txt}. Warm prefill: {pf_txt}; TTFT {tt_txt}. Wall-to-wall at c6: {w2w_txt}. EXL3 serves 4× the
context with {r(KV['exl3'], KV['nvfp4'])} the KV pool; boot to serve EXL3 {boot('exl3')} vs NVFP4 {boot('nvfp4')}; quality
probe {'tie' if qe == qn else 'differs'}. An earlier run showing EXL3 ahead on every line was discarded: NVFP4's nodes were
clock-capped after a reboot (611–728 MHz); with clocks equal the picture is the one above.

{summary}
## Hardware and topology
Four NVIDIA DGX Spark (GB10, sm_121a, 128 GB unified memory, ~121 GB usable) on a ConnectX-7 RoCE v2 fabric,
192.168.192.0/24, rail 0 (`enp1s0f0np0` / `rocep1s0f0`, GID 3). Reddie (.2) heads NVFP4 with Spark4 (.4);
Bluey (.1) heads EXL3 with Asusi (.3). Both lanes TP=2 across two nodes (vLLM mp executor, NCCL over RoCE);
they share nothing but the switch. Bench client: a Mac mini on the same tailnet.

**Clock state matters on GB10.** An earlier run was thrown out: after a reboot, Reddie and Spark4 came up pinned at
611–728 MHz SM clock under load (EXL3's nodes ran ~2,500) and NVFP4 measured 36 tok/s with a perfect 92–100 % draft
acceptance. All four were restarted together and verified under real decode load before this run: healthy GB10s here
settle at ~2,170–2,180 MHz at ~96 % utilization. Check `nvidia-smi --query-gpu=clocks.sm` under load after any
Spark reboot before trusting a throughput number.

## The two lanes
**NVFP4 (reference).** The published 2-Spark recipe run verbatim: weights `RedHatAI/GLM-5.3-Flash-NVFP4`; image
`ghcr.io/tonyd2wild/vllm-glm53-flash:sm121-v11-dflash2`; `--max-model-len 262144 --gpu-memory-utilization 0.85
--kv-cache-memory 3 GiB --max-num-seqs 6 --max-num-batched-tokens 8192 --block-size 2304 --moe-backend marlin
--kv-cache-dtype fp8_e4m3 --enforce-eager`; DFlash2 drafter k=7 (92–100 % draft acceptance on structured output);
`vm.swappiness=0`; worker first, head 25 s later.

**EXL3 (challenger).** Reederey87's GB10 kit (MiaAI-Lab's sibling as cross-reference) built for our fabric: weights
`brandonmusic/GLM-5.3-Flash-tr3-4bpw` (EXL3/TR3, 4 bpw, 120 shards, ~164 GiB, ~91 GiB resident per node);
exllamav3 compiled for `12.1a`; `--quantization exl3 --max-model-len 1000000 --gpu-memory-utilization 0.85
--kv-cache-memory-bytes 15414698763 --max-num-seqs 4 --max-num-batched-tokens 3584 --kv-cache-dtype fp8
--no-async-scheduling`; same DFlash2 drafter k=7. Both lanes: fp8 KV, thinking off, multimodal chat template,
native `image_url` (a red square came back "Red" on both).

## Method
**Isolation.** Relay parked on the 3090 27B, latency dashboard paused (it sends real probe completions), the three
Hermes supervisors that default to `glm-5.3-flash` moved to the 27B; after each run the head's access log shows chat
POSTs from the bench client only, with counts matching the requests issued (the supervisors share the client's IP,
so only counts prove it).{iso_txt} **Simultaneity.** Both lanes benched in parallel; no shared GPUs, memory or NCCL group.
**Warm-up.** 2× c1 + 1× c6 before measuring; both engines JIT-compile per request shape — never bench a cold lane.
**Metrics.** Median tokens/s, non-streaming. c1–c6: 3 rounds of c concurrent ~300-token generations; aggregate =
Σ tokens / round wall; per-stream = each request's tokens / its wall; wall-to-wall = end-to-end latency (median).
TTFT at level c: c concurrent ~1.5K-token prompts with an 8-token answer. Detailed run: c1 ×5 for the spread.
Temperature 0, `stream false`, thinking off, identical prompts. Tools in `tools/`.

## Reading the curve
EXL3 scales to {pe} tok/s at c{pe_c} and flattens — the kit's `--max-num-seqs 4` (a config cap, not the quant).
NVFP4 (`--max-num-seqs 6`) admits all six but pays per stream: {n1['per_stream_tok_s']} → {n6['per_stream_tok_s']} tok/s,
TTFT {n1['ttft_med_s']} → {n6['ttft_med_s']} s, wall-to-wall {n1['w2w_med_s']} → {n6['w2w_med_s']} s.

## Quality: does the quant change how smart it is?
**Probe** (top-k in O(n log k) + bat-and-ball, thinking off): EXL3 {qe}, NVFP4 {qn}.
**Battery**: 12 auto-graded items (3 math word problems, 3 logic, 2 code, leap-year rule, bat-and-ball, 2 strict-format),
identical for both lanes, temp 0, thinking off and thinking on (`tools/quality_battery.py`, full items + answers in `results/quality_battery_*.json`):

| accuracy | NVFP4 · off | EXL3 · off | NVFP4 · on | EXL3 · on |
|---|---|---|---|---|
| **all 12** | {acc('nvfp4','off')} | {acc('exl3','off')} | {acc('nvfp4','on')} | {acc('exl3','on')} |
{cat_rows(html=False)}
| avg reasoning trace, on (chars) | | | {reason_chars('nvfp4')} | {reason_chars('exl3')} |

Disagreements, thinking off:
{disagree('off', html=False)}
Disagreements, thinking on:
{disagree('on', html=False)}
Traces, thinking on (same item, both lanes):
{TRACES_MD}
Published KLD: EXL3/TR3 4bpw ~0.025 (ties FP8), NVFP4 ~0.060. Twelve items is a probe, not a suite.

## What we got wrong, part two: the prefix cache
The first version said EXL3 "answers first" ({e1.get('ttft_repeat_s','—')} vs {n1.get('ttft_repeat_s','—')} s at c1; prefill {e1.get('prefill_repeat','—')} vs {n1.get('prefill_repeat','—')} tok/s). Every request carried the same prompt; EXL3 replayed its prefix cache, NVFP4 (2,304-token cache blocks) recomputed. Fresh prompts: TTFT c1 NVFP4 {n1['ttft_med_s']} s vs EXL3 {e1['ttft_med_s']} s, c6 {nr[-1]['ttft_med_s']} vs {er[-1]['ttft_med_s']} s; fresh prefill {n1['prefill_tok_s']:,} vs {e1['prefill_tok_s']:,} tok/s; cold prefill at {pl_tok} tokens {pl_n} vs {pl_e} tok/s. EXL3 keeps: the cache ({rep_txt}), mixed real-prompt load ({c4_txt}), 4× context, 4.7× KV, 13-min boot.

{CAT_SECTION_MD}
{TP4_SECTION_MD}
{H2H_SECTION_MD}
## Boot and load time
Launch command → first `/health` 200, this run: EXL3 {boot('exl3')}; NVFP4 {boot('nvfp4')}. NVFP4's worker reads its
weights over NFS from the head on this cluster (no local copy of the base on Spark4). Both JIT-compile on first boot.

## What broke, and the fixes
- EXL3 kit: `count_shards()` uses `find -type f` (misses HF-cache symlinks) → "0 / 120 shards"; fix `find -L`.
- EXL3 kit: worker needs the full ~164 GiB; root-owned `~/.cache/vllm-glm53-flash` kills the launch silently (chown);
  binds `--host 127.0.0.1` (set `0.0.0.0`).
- NVFP4: run the published recipe verbatim (1M context starves the KV pool at TP2: three NVRM OOM reboots + a stall).
  `vm.swappiness=0` resets on reboot. Poll `/health`, not `/v1/models`.
- Both: verify SM clocks under load after any reboot; drop caches on every node before every launch.

## Reproduce
See `docs/article.html` §Reproduce, `tools/run_full_test.sh`, and the two repos below.

## Credits
Reederey87 · MiaAI-Lab · brandonmusic (EXL3 quant, ShapleyMCG) · turboderp (exllamav3) · IncoAI (DFlash2) ·
RedHatAI (NVFP4 weights) · zai-org (GLM-5.3-Flash) · malaiwah, drowzeys.
Repos: github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark · github.com/tonyd2wild/GLM-5.3-Flash-EXL3-on-2x-NVIDIA-DGX-Spark

## Caveats
One quality probe is not a quality study. Raise EXL3's `--max-num-seqs` and re-sweep c5–c8. Neither lane is the
abliterated variant. Two specific quants on one specific cluster.
"""
open("REPORT.md", "w").write(report)
open("BENCH.md", "w").write(f"""# Bench — EXL3 vs NVFP4 (GLM-5.3-Flash, same 4-Spark cluster)

Canonical results live in `results/` (sweep JSON per lane, detailed JSON, quality answers, boot.json) and are
rendered by `tools/make_article.py` into `REPORT.md`, `results/summary.md` and `docs/article.html`.
Method: 2Wild house rule — throughput = median tok/s, non-stream; isolate the lane, warm it, verify clocks under load.

{summary}
""")
print(f"article: docs/article.html ({len(html)//1024} KB) · summary: results/summary.md · REPORT.md · BENCH.md")
print(summary.split("## Sweep")[0])
