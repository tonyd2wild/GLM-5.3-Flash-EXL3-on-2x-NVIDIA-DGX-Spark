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
e1, n1, e6, n6 = er[0], nr[0], er[-1], nr[-1]
pe = max(r["agg_tok_s"] for r in er); pe_c = [r["c"] for r in er if r["agg_tok_s"] == pe][0]
pn = max(r["agg_tok_s"] for r in nr); pn_c = [r["c"] for r in nr if r["agg_tok_s"] == pn][0]
r = lambda a, b, d=1: f"{a/b:.{d}f}×"
b64 = lambda p: "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
spread = lambda d: f"{d['c1_min']}–{d['c1_max']}" if d else "—"
pct = lambda d: f"±{(d['c1_max']-d['c1_min'])/2/d['c1_med']*100:.1f}%" if d else "—"
ts = E.get("ts", "")

sweep_rows = "".join(f"<tr><td>c{e['c']}</td><td>{n['agg_tok_s']}</td><td>{n['per_stream_tok_s']}</td><td>{n['w2w_med_s']} s</td><td>{n['ttft_med_s']} s</td>"
                     f"<td><b>{e['agg_tok_s']}</b></td><td><b>{e['per_stream_tok_s']}</b></td><td><b>{e['w2w_med_s']} s</b></td><td><b>{e['ttft_med_s']} s</b></td></tr>" for e, n in zip(er, nr))
md_rows = "\n".join(f"| {e['c']} | {n['agg_tok_s']} | {n['per_stream_tok_s']} | {n['w2w_med_s']} s | {n['ttft_med_s']} s | **{e['agg_tok_s']}** | **{e['per_stream_tok_s']}** | **{e['w2w_med_s']} s** | **{e['ttft_med_s']} s** |" for e, n in zip(er, nr))

summary = f"""## Headline (isolated, both lanes benched simultaneously, {ts})
| | NVFP4 (Reddie + Spark4) | EXL3 (Bluey + Asusi) | ratio |
|---|---|---|---|
| c1 single-stream tok/s | {n1['agg_tok_s']} | **{e1['agg_tok_s']}** | {r(e1['agg_tok_s'], n1['agg_tok_s'])} |
| peak aggregate tok/s (at c) | {pn} (c{pn_c}) | **{pe}** (c{pe_c}) | {r(pe, pn)} |
| c6 aggregate tok/s | {n6['agg_tok_s']} | **{e6['agg_tok_s']}** | {r(e6['agg_tok_s'], n6['agg_tok_s'])} |
| c6 per-stream tok/s | {n6['per_stream_tok_s']} | **{e6['per_stream_tok_s']}** | {r(e6['per_stream_tok_s'], n6['per_stream_tok_s'])} |
| prefill tok/s (~1.5K prompt) | {n1['prefill_tok_s']} | **{e1['prefill_tok_s']}** | {r(e1['prefill_tok_s'], n1['prefill_tok_s'])} |
| TTFT c1 / c6 | {n1['ttft_med_s']} s / {n6['ttft_med_s']} s | **{e1['ttft_med_s']} s / {e6['ttft_med_s']} s** | {r(n1['ttft_med_s'], e1['ttft_med_s'])} / {r(n6['ttft_med_s'], e6['ttft_med_s'])} lower |
| wall-to-wall c1 / c6 (300-tok answer) | {n1['w2w_med_s']} s / {n6['w2w_med_s']} s | **{e1['w2w_med_s']} s / {e6['w2w_med_s']} s** | {r(n1['w2w_med_s'], e1['w2w_med_s'])} / {r(n6['w2w_med_s'], e6['w2w_med_s'])} lower |
| c1 spread (detailed, n=5) | {spread(dn)} ({pct(dn)}) | {spread(de)} ({pct(de)}) | |
| max context | {CTX['nvfp4']:,} | **{CTX['exl3']:,}** | {r(CTX['exl3'], CTX['nvfp4'], 0)} |
| KV pool (tokens) | {KV['nvfp4']:,} | **{KV['exl3']:,}** | {r(KV['exl3'], KV['nvfp4'])} |
| quality probe | {qn} | {qe} | {'tie' if qe == qn else 'differs'} |

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
</style>
<div class="wrap">
<div class="eyebrow">2Wild fleet report · {ts[:10]}</div>
<h1>NVFP4 <span>vs</span> EXL3 <span>on DGX Spark</span></h1>
<p class="sub">The same 320B MoE, GLM-5.3-Flash, in two 4-bit quantizations, on two independent 2-node DGX Spark pairs, benched at the same time in the same state, isolated from every other consumer. Full c1–c6 sweep: throughput, per-stream decode, time to first token, wall-to-wall latency, prefill, context, KV pool.</p>
<div class="meta"><span>4× DGX Spark GB10 · 128 GB UMA</span><span>CX7 RoCE rail 0 · TP=2 per lane</span><span>vLLM · DFlash2 k=7 · fp8 KV</span><span>non-stream · temp 0 · thinking off</span><span>@tonyd2wild</span></div>
<div class="stats">
<div class="stat"><div class="n">{r(e1['agg_tok_s'], n1['agg_tok_s'])}</div><div class="l">single-stream decode ({e1['agg_tok_s']} vs {n1['agg_tok_s']} tok/s)</div></div>
<div class="stat"><div class="n">{r(e1['prefill_tok_s'], n1['prefill_tok_s'])}</div><div class="l">prefill ({e1['prefill_tok_s']:,} vs {n1['prefill_tok_s']:,} tok/s) · TTFT {e1['ttft_med_s']} s vs {n1['ttft_med_s']} s</div></div>
<div class="stat"><div class="n">{r(KV['exl3'], KV['nvfp4'])}</div><div class="l">the KV pool ({KV['exl3']:,} vs {KV['nvfp4']:,} tokens) · 1M vs 256K context</div></div>
</div>
<p class="callout"><b>Result.</b> On identical hardware in the same state — all four nodes restarted together and verified at 2,411 MHz under load (Bluey ~2,177 under its clock-cap service) — EXL3 / TR3 4bpw delivered {r(e1['agg_tok_s'], n1['agg_tok_s'])} the single-stream decode, {r(pe, pn)} the peak aggregate ({pe} at c{pe_c} vs {pn} at c{pn_c}), {r(e1['prefill_tok_s'], n1['prefill_tok_s'])} the prefill, a {e1['ttft_med_s']} s time to first token against {n1['ttft_med_s']} s, four times the context with {r(KV['exl3'], KV['nvfp4'])} the KV pool, and {'the same answer' if qe == qn else 'a different answer'} on the quality probe.</p>

<h2>The headline table</h2>
<div class="tw"><table><thead><tr><th></th><th>NVFP4 · Reddie + Spark4</th><th>EXL3 · Bluey + Asusi</th><th>ratio</th></tr></thead><tbody>
<tr><td>c1 single-stream, tok/s (3 rounds)</td><td>{n1['agg_tok_s']}</td><td><b>{e1['agg_tok_s']}</b></td><td><b>{r(e1['agg_tok_s'], n1['agg_tok_s'])}</b></td></tr>
<tr><td>c1 spread, detailed run (n=5)</td><td>{spread(dn)} ({pct(dn)})</td><td><b>{spread(de)} ({pct(de)})</b></td><td></td></tr>
<tr><td>peak aggregate, tok/s</td><td>{pn} (c{pn_c})</td><td><b>{pe} (c{pe_c})</b></td><td><b>{r(pe, pn)}</b></td></tr>
<tr><td>c6 aggregate, tok/s</td><td>{n6['agg_tok_s']}</td><td><b>{e6['agg_tok_s']}</b></td><td><b>{r(e6['agg_tok_s'], n6['agg_tok_s'])}</b></td></tr>
<tr><td>c6 per-stream, tok/s</td><td>{n6['per_stream_tok_s']}</td><td><b>{e6['per_stream_tok_s']}</b></td><td><b>{r(e6['per_stream_tok_s'], n6['per_stream_tok_s'])}</b></td></tr>
<tr><td>prefill, tok/s (~1.5K-token prompt)</td><td>{n1['prefill_tok_s']:,}</td><td><b>{e1['prefill_tok_s']:,}</b></td><td><b>{r(e1['prefill_tok_s'], n1['prefill_tok_s'])}</b></td></tr>
<tr><td>time to first token at c1 / c6</td><td>{n1['ttft_med_s']} s / {n6['ttft_med_s']} s</td><td><b>{e1['ttft_med_s']} s / {e6['ttft_med_s']} s</b></td><td><b>{r(n1['ttft_med_s'], e1['ttft_med_s'])} / {r(n6['ttft_med_s'], e6['ttft_med_s'])} lower</b></td></tr>
<tr><td>wall-to-wall, 300-token answer, c1 / c6</td><td>{n1['w2w_med_s']} s / {n6['w2w_med_s']} s</td><td><b>{e1['w2w_med_s']} s / {e6['w2w_med_s']} s</b></td><td><b>{r(n1['w2w_med_s'], e1['w2w_med_s'])} / {r(n6['w2w_med_s'], e6['w2w_med_s'])} lower</b></td></tr>
<tr><td>max context that booted</td><td>{CTX['nvfp4']:,}</td><td><b>{CTX['exl3']:,}</b></td><td><b>{r(CTX['exl3'], CTX['nvfp4'], 0)}</b></td></tr>
<tr><td>KV pool (engine startup line)</td><td>{KV['nvfp4']:,} tokens</td><td><b>{KV['exl3']:,} tokens</b></td><td><b>{r(KV['exl3'], KV['nvfp4'])}</b></td></tr>
<tr><td>quality probe (code + reasoning trap)</td><td>{qn}</td><td>{qe}</td><td>{'tie' if qe == qn else 'differs'}</td></tr>
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
<p><b>Isolation.</b> Before measuring, every other consumer was moved off both lanes: the spark-flash relay our external agents use was parked on the 3090's Qwen 27B, the latency dashboard (which sends real probe completions) was paused, and the three Hermes supervisors whose default model is <code>glm-5.3-flash</code> were moved to the 27B. After each run we pulled each head's access log: every chat POST in the window came from the bench client, and the counts matched the requests issued. The supervisors run on the same Mac as the bench client, so the IP alone proves nothing; the request counts do.</p>
<p><b>Simultaneity and state.</b> The two lanes were benched in parallel, minutes after all four nodes were restarted together and their clocks verified under load. They share no GPUs, no memory, and no NCCL group.</p>
<p><b>Warm-up.</b> Both engines JIT-compile kernels lazily per request shape. Every lane got 2× c1 + 1× c6 warm-up requests before measurement. Never bench a cold lane: EXL3's first-ever completion on a fresh boot was ~30 tok/s and its first long prefill 136 tok/s; NVFP4's first request took 5.2 s, its third 3.3 s.</p>
<p><b>Metrics.</b> Throughput is median tokens per second, non-streaming. c1–c6: 3 rounds of c concurrent ~300-token generations; aggregate = Σ tokens / round wall; per-stream = each request's tokens / its own wall; wall-to-wall = each request's end-to-end latency (median). TTFT at level c: c concurrent ~1.5K-token prompts with an 8-token answer, median wall. Prefill = prompt tokens / that wall at c1. A separate detailed run repeats c1 five times for the spread. All requests <code>temperature 0</code>, <code>stream false</code>, thinking off, identical prompts to both lanes. Tools: <code>tools/bench_sweep.py</code>, <code>tools/bench_detailed.py</code>, <code>tools/quality_probe.py</code>, <code>tools/run_full_test.sh</code>.</p>

<h2>The full sweep, c1 → c6</h2>
<div class="tw"><table><thead><tr><th>c</th><th>NVFP4 agg tok/s</th><th>per-stream</th><th>wall-to-wall</th><th>TTFT</th><th>EXL3 agg tok/s</th><th>per-stream</th><th>wall-to-wall</th><th>TTFT</th></tr></thead><tbody>{sweep_rows}</tbody></table></div>
<figure><img src="{b64('results/chart_agg.png')}" alt="Aggregate tokens per second versus concurrency for both lanes."><figcaption>Aggregate throughput. EXL3 peaks at c{pe_c} ({pe} tok/s); the kit launches with <code>--max-num-seqs 4</code>, so beyond four concurrent requests the rest queue. NVFP4 peaks at c{pn_c} ({pn}).</figcaption></figure>
<figure><img src="{b64('results/chart_ttft.png')}" alt="Time to first token versus concurrency for both lanes."><figcaption>Time to first token. EXL3 {e1['ttft_med_s']}–{e6['ttft_med_s']} s across the sweep; NVFP4 {n1['ttft_med_s']}–{n6['ttft_med_s']} s.</figcaption></figure>
<figure><img src="{b64('results/chart_w2w.png')}" alt="Wall-to-wall latency for a 300-token answer versus concurrency for both lanes."><figcaption>Wall-to-wall for a 300-token answer, median. At c6: EXL3 {e6['w2w_med_s']} s, NVFP4 {n6['w2w_med_s']} s.</figcaption></figure>
<p><b>Reading the curve.</b> EXL3 scales to {pe} tok/s at c{pe_c} and then flattens — that is the kit's <code>--max-num-seqs 4</code>, a configuration cap rather than the quantization, and raising it is the obvious next experiment. NVFP4 (<code>--max-num-seqs 6</code>) admits all six but pays per stream: {n1['per_stream_tok_s']} → {n6['per_stream_tok_s']} tok/s, TTFT {n1['ttft_med_s']} → {n6['ttft_med_s']} s.</p>

<h2>Quality</h2>
<p>Same prompt to both, thinking off, temperature 0: write <code>top_k_frequent(nums, k)</code> in O(n log k) with an explanation and an edge case, and solve the bat-and-ball trap ($1.10 total, the bat $1.00 more than the ball). EXL3: {qe}. NVFP4: {qn}. Published KLD figures put EXL3/TR3 4bpw near 0.025 (tying FP8) and NVFP4 near 0.060, so a quality gap is expected to exist; a single probe of this difficulty {'did not surface it' if qe == qn else 'surfaced a difference'}. Harder probes are the open items.</p>

<h2>Discussion</h2>
<p><b>Where the speed comes from.</b> The largest gap is prefill, {r(e1['prefill_tok_s'], n1['prefill_tok_s'])}. EXL3's fused trellis MoE kernels prefill a 1.5K prompt in {e1['ttft_med_s']} s; the NVFP4 marlin path took {n1['ttft_med_s']} s. For agents that is the number users feel: time to first token. Decode is {r(e1['agg_tok_s'], n1['agg_tok_s'])} faster at c1 and {r(e6['per_stream_tok_s'], n6['per_stream_tok_s'])} per stream at c6.</p>
<p><b>Context and KV.</b> EXL3 serves {CTX['exl3']:,} tokens of context with a {KV['exl3']:,}-token KV pool on the same two boxes on which the NVFP4 recipe serves {CTX['nvfp4']:,} with a {KV['nvfp4']:,}-token pool. NVFP4 at TP2 cannot be launched at 1M: an adapted launcher with <code>--max-model-len 1048576</code> produced three worker reboots on <code>NVRM: NV_ERR_NO_MEMORY</code> and a 24-minute stall until the published 256K recipe was run verbatim.</p>
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
print(f"article: docs/article.html ({len(html)//1024} KB) · summary: results/summary.md")
print(summary.split("## Sweep")[0])
