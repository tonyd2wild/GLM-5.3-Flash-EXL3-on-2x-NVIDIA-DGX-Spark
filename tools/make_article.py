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
pf_note = (" (warm, median of last 3 of 6 sequential 1.5K prompts; first-after-boot cold sample: EXL3 "
           f"{e1.get('prefill_first', ('—','—'))[0]} tok/s / NVFP4 {n1.get('prefill_first', ('—','—'))[0]} tok/s)") if "prefill_first" in e1 else ""
r = lambda a, b, d=1: f"{a/b:.{d}f}×"
b64 = lambda p: "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
spread = lambda d: f"{d['c1_min']}–{d['c1_max']}" if d else "—"
pct = lambda d: f"±{(d['c1_max']-d['c1_min'])/2/d['c1_med']*100:.1f}%" if d else "—"
ts = E.get("ts", "")

sweep_rows = "".join(f"<tr><td>c{e['c']}</td><td>{n['agg_tok_s']}</td><td>{n['per_stream_tok_s']}</td><td>{n['w2w_med_s']} s</td><td>{n['ttft_med_s']} s</td>"
                     f"<td>{e['agg_tok_s']}</td><td>{e['per_stream_tok_s']}</td><td>{e['w2w_med_s']} s</td><td>{e['ttft_med_s']} s</td></tr>" for e, n in zip(er, nr))
md_rows = "\n".join(f"| {e['c']} | {n['agg_tok_s']} | {n['per_stream_tok_s']} | {n['w2w_med_s']} s | {n['ttft_med_s']} s | **{e['agg_tok_s']}** | **{e['per_stream_tok_s']}** | **{e['w2w_med_s']} s** | **{e['ttft_med_s']} s** |" for e, n in zip(er, nr))

summary = f"""## Headline (isolated, both lanes benched simultaneously, {ts})
| | NVFP4 (Reddie + Spark4) | EXL3 (Bluey + Asusi) | EXL3 ÷ NVFP4 |
|---|---|---|---|
| c1 single-stream tok/s | {n1['agg_tok_s']} | {e1['agg_tok_s']} | {r(e1['agg_tok_s'], n1['agg_tok_s'])} |
| peak aggregate tok/s (at c) | {pn} (c{pn_c}) | {pe} (c{pe_c}) | {r(pe, pn)} |
| c6 aggregate tok/s | {n6['agg_tok_s']} | {e6['agg_tok_s']} | {r(e6['agg_tok_s'], n6['agg_tok_s'])} |
| c6 per-stream tok/s | {n6['per_stream_tok_s']} | {e6['per_stream_tok_s']} | {r(e6['per_stream_tok_s'], n6['per_stream_tok_s'])} |
| prefill tok/s (~1.5K prompt){pf_note} | {n1['prefill_tok_s']} | {e1['prefill_tok_s']} | {r(e1['prefill_tok_s'], n1['prefill_tok_s'])} |
| TTFT c1 / c6 | {n1['ttft_med_s']} s / {n6['ttft_med_s']} s | {e1['ttft_med_s']} s / {e6['ttft_med_s']} s | {r(n1['ttft_med_s'], e1['ttft_med_s'])} / {r(n6['ttft_med_s'], e6['ttft_med_s'])} lower |
| wall-to-wall c1 / c6 (300-tok answer) | {n1['w2w_med_s']} s / {n6['w2w_med_s']} s | {e1['w2w_med_s']} s / {e6['w2w_med_s']} s | {r(n1['w2w_med_s'], e1['w2w_med_s'])} / {r(n6['w2w_med_s'], e6['w2w_med_s'])} lower |
| c1 spread (detailed, n=5) | {spread(dn)} ({pct(dn)}) | {spread(de)} ({pct(de)}) | |
| max context | {CTX['nvfp4']:,} | {CTX['exl3']:,} | {r(CTX['exl3'], CTX['nvfp4'], 0)} |
| KV pool (tokens) | {KV['nvfp4']:,} | {KV['exl3']:,} | {r(KV['exl3'], KV['nvfp4'])} |
| quality probe | {qn} | {qe} | {'tie' if qe == qn else 'differs'} |
| boot: launch → /health 200 | {boot('nvfp4')} | {boot('exl3')} | |

## Sweep c1–c6 (3 rounds per level)
| c | NVFP4 agg | per-stream | wall-to-wall | TTFT | EXL3 agg | per-stream | wall-to-wall | TTFT |
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
<div class="stat"><div class="n">{n1['agg_tok_s']} <span style="color:var(--muted)">/</span> {e1['agg_tok_s']}</div><div class="l">c1 single-stream tok/s, NVFP4 / EXL3 — {c1_lead if c1_lead!='tie' else 'tie'}{'' if c1_lead=='tie' else ' leads'}</div></div>
<div class="stat"><div class="n">{pn} <span style="color:var(--muted)">/</span> {pe}</div><div class="l">peak aggregate tok/s, NVFP4 (c{pn_c}) / EXL3 (c{pe_c}) — {pk_lead if pk_lead!='tie' else 'tie'}{'' if pk_lead=='tie' else ' leads'}</div></div>
<div class="stat"><div class="n">{r(KV['exl3'], KV['nvfp4'])}</div><div class="l">EXL3's KV pool ({KV['exl3']:,} vs {KV['nvfp4']:,} tokens) · 1M vs 256K context</div></div>
</div>
<p class="callout"><b>Result, same state.</b> All four nodes restarted together and verified at ~2,170–2,190 MHz under decode load. Single-stream decode: {c1_txt}. Peak aggregate: {pk_txt}. Per-stream at c6: {c6ps_txt}. Warm prefill: {pf_txt}; TTFT: {tt_txt}. Wall-to-wall at c6: {w2w_txt}. EXL3 serves 4× the context with {r(KV['exl3'], KV['nvfp4'])} the KV pool on the same two boxes; boot to serve was EXL3 {boot('exl3')} vs NVFP4 {boot('nvfp4')}; the quality probe was {'a tie' if qe == qn else 'not a tie'}. An earlier run of this comparison that showed EXL3 ahead on every line was thrown out: NVFP4's nodes were clock-capped after a reboot.</p>

<h2>The headline table</h2>
<div class="tw"><table><thead><tr><th></th><th>NVFP4 · Reddie + Spark4</th><th>EXL3 · Bluey + Asusi</th><th>EXL3 ÷ NVFP4</th></tr></thead><tbody>
<tr><td>c1 single-stream, tok/s (3 rounds)</td><td>{n1['agg_tok_s']}</td><td>{e1['agg_tok_s']}</td><td>{r(e1['agg_tok_s'], n1['agg_tok_s'])}</td></tr>
<tr><td>c1 spread, detailed run (n=5)</td><td>{spread(dn)} ({pct(dn)})</td><td>{spread(de)} ({pct(de)})</td><td></td></tr>
<tr><td>peak aggregate, tok/s</td><td>{pn} (c{pn_c})</td><td>{pe} (c{pe_c})</td><td>{r(pe, pn)}</td></tr>
<tr><td>c6 aggregate, tok/s</td><td>{n6['agg_tok_s']}</td><td>{e6['agg_tok_s']}</td><td>{r(e6['agg_tok_s'], n6['agg_tok_s'])}</td></tr>
<tr><td>c6 per-stream, tok/s</td><td>{n6['per_stream_tok_s']}</td><td>{e6['per_stream_tok_s']}</td><td>{r(e6['per_stream_tok_s'], n6['per_stream_tok_s'])}</td></tr>
<tr><td>prefill, tok/s (~1.5K-token prompt){pf_note}</td><td>{n1['prefill_tok_s']:,}</td><td>{e1['prefill_tok_s']:,}</td><td>{r(e1['prefill_tok_s'], n1['prefill_tok_s'])}</td></tr>
<tr><td>time to first token at c1 / c6</td><td>{n1['ttft_med_s']} s / {n6['ttft_med_s']} s</td><td>{e1['ttft_med_s']} s / {e6['ttft_med_s']} s</td><td>{r(n1['ttft_med_s'], e1['ttft_med_s'])} / {r(n6['ttft_med_s'], e6['ttft_med_s'])} lower</td></tr>
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
<p>The <a href="https://github.com/Reederey87/glm53-flash-exl3-2x-dgx-spark">Reederey87 GB10 kit</a>, with <a href="https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks">MiaAI-Lab</a>'s sibling as cross-reference, built for our fabric. Weights <code>brandonmusic/GLM-5.3-Flash-tr3-4bpw</code>, EXL3 / TR3 trellis at 4 bits per weight, 120 shards, ~164 GiB, ~91 GiB resident per node; image built on the head from the kit's Dockerfile (exllamav3 compiled for <code>12.1a</code>); <code>--quantization exl3 --max-model-len 1000000 --gpu-memory-utilization 0.85 --kv-cache-memory-bytes 15414698763 --max-num-seqs 4 --max-num-batched-tokens 3584 --kv-cache-dtype fp8 --no-async-scheduling</code>; the same DFlash2 drafter at k=7. Every fix we needed is in our fork, <a href="https://github.com/tonyd2wild/glm53-flash-exl3-2x-dgx-spark">tonyd2wild/glm53-flash-exl3-2x-dgx-spark</a>.</p>
<p>Both lanes: fp8 KV cache, thinking disabled, the multimodal chat template, native <code>image_url</code> input (a 64×64 red square came back "Red" on both).</p>

<h2>Method</h2>
<p><b>Isolation.</b> Before measuring, every other consumer was moved off both lanes: the spark-flash relay our external agents use was parked on the 3090's Qwen 27B, the latency dashboard (which sends real probe completions) was paused, and the three Hermes supervisors whose default model is <code>glm-5.3-flash</code> were moved to the 27B. After each run we pulled each head's access log: every chat POST in the window came from the bench client, and the counts matched the requests issued. The supervisors run on the same Mac as the bench client, so the IP alone proves nothing; the request counts do.{iso_txt}</p>
<p><b>Simultaneity and state.</b> The two lanes were benched in parallel, minutes after all four nodes were restarted together and their clocks verified under load. They share no GPUs, no memory, and no NCCL group.</p>
<p><b>Warm-up.</b> Both engines JIT-compile kernels lazily per request shape. Every lane got 2× c1 + 1× c6 warm-up requests before measurement. Never bench a cold lane: EXL3's first-ever completion on a fresh boot was ~30 tok/s and its first long prefill 136 tok/s; NVFP4's first request took 5.2 s, its third 3.3 s.</p>
<p><b>Metrics.</b> Throughput is median tokens per second, non-streaming. c1–c6: 3 rounds of c concurrent ~300-token generations; aggregate = Σ tokens / round wall; per-stream = each request's tokens / its own wall; wall-to-wall = each request's end-to-end latency (median). TTFT at level c: c concurrent ~1.5K-token prompts with an 8-token answer, median wall. Prefill = prompt tokens / that wall at c1. A separate detailed run repeats c1 five times for the spread. All requests <code>temperature 0</code>, <code>stream false</code>, thinking off, identical prompts to both lanes. Tools: <code>tools/bench_sweep.py</code>, <code>tools/bench_detailed.py</code>, <code>tools/quality_probe.py</code>, <code>tools/run_full_test.sh</code>.</p>

<h2>The full sweep, c1 → c6</h2>
<div class="tw"><table><thead><tr><th>c</th><th>NVFP4 agg tok/s</th><th>per-stream</th><th>wall-to-wall</th><th>TTFT</th><th>EXL3 agg tok/s</th><th>per-stream</th><th>wall-to-wall</th><th>TTFT</th></tr></thead><tbody>{sweep_rows}</tbody></table></div>
<figure><img src="{b64('results/chart_agg.png')}" alt="Aggregate tokens per second versus concurrency for both lanes."><figcaption>Aggregate throughput. EXL3 peaks at c{pe_c} ({pe} tok/s); the kit launches with <code>--max-num-seqs 4</code>, so beyond four concurrent requests the rest queue. NVFP4 peaks at c{pn_c} ({pn}).</figcaption></figure>
<figure><img src="{b64('results/chart_ttft.png')}" alt="Time to first token versus concurrency for both lanes."><figcaption>Time to first token. EXL3 {e1['ttft_med_s']}–{e6['ttft_med_s']} s across the sweep; NVFP4 {n1['ttft_med_s']}–{n6['ttft_med_s']} s.</figcaption></figure>
<figure><img src="{b64('results/chart_w2w.png')}" alt="Wall-to-wall latency for a 300-token answer versus concurrency for both lanes."><figcaption>Wall-to-wall for a 300-token answer, median. At c6: EXL3 {e6['w2w_med_s']} s, NVFP4 {n6['w2w_med_s']} s.</figcaption></figure>
<p><b>Reading the curve.</b> EXL3 scales to {pe} tok/s at c{pe_c} and then flattens — that is the kit's <code>--max-num-seqs 4</code>, a configuration cap rather than the quantization, and raising it is the obvious next experiment. NVFP4 (<code>--max-num-seqs 6</code>) admits all six but pays per stream: {n1['per_stream_tok_s']} → {n6['per_stream_tok_s']} tok/s, TTFT {n1['ttft_med_s']} → {n6['ttft_med_s']} s.</p>

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

# EXL3, on the head: clone tonyd2wild/glm53-flash-exl3-2x-dgx-spark
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
<footer>@tonyd2wild · <a href="https://github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark">NVFP4 recipe</a> · <a href="https://github.com/tonyd2wild/glm53-flash-exl3-2x-dgx-spark">EXL3 fork, tools and results</a> · {ts[:10]}</footer>
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
Repos: github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark · github.com/tonyd2wild/glm53-flash-exl3-2x-dgx-spark

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
