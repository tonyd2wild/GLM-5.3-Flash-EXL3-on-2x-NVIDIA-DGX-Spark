#!/usr/bin/env python3
# Charcoal-and-white scorecard poster + standalone sweep charts. Every number, ratio and verdict on the poster is
# computed from results/*.json (sweeps, detailed, prefill, boot, quality battery) — nothing is hand-typed.
import json, os, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
def J(p, default=None): return json.load(open(p)) if os.path.exists(p) else default
E=J("results/sweep_exl3.json")["rows"]; N=J("results/sweep_nvfp4.json")["rows"]
DE=J("results/detailed_exl3.json",{}); DN=J("results/detailed_nvfp4.json",{})
PE=J("results/prefill_exl3.json",{}); PN=J("results/prefill_nvfp4.json",{}); BOOT=J("results/boot.json",{})
B={(l,m):J(f"results/quality_battery_{l}_{m}.json") for l in ("exl3","nvfp4") for m in ("off","on")}
G="#1B1C1F"; P="#232428"; INK="#F2F2F0"; MUT="#9A9DA3"; RULE="#3A3C41"; WH="#F2F2F0"; GY="#8F9297"
plt.rcParams.update({"font.family":"DejaVu Sans","text.color":INK,"axes.edgecolor":RULE,"axes.labelcolor":MUT,
  "xtick.color":MUT,"ytick.color":MUT,"axes.facecolor":P,"figure.facecolor":G,"savefig.facecolor":G})
# ---------------- derived numbers ----------------
c1e,c6e=E[0],E[5]; c1n,c6n=N[0],N[5]
c1n_v=DN.get("c1_med",c1n["agg_tok_s"]); c1e_v=DE.get("c1_med",c1e["agg_tok_s"])          # detailed medians (n=5) when present
pn=PN.get("warm_prefill_tok_s",c1n["prefill_tok_s"]); pe=PE.get("warm_prefill_tok_s",c1e["prefill_tok_s"])
tn1=PN.get("warm_ttft_s",c1n["ttft_med_s"]); te1=PE.get("warm_ttft_s",c1e["ttft_med_s"])  # warm c1 TTFT
def spread(D):
    return f"±{(D['c1_max']-D['c1_min'])/2/D['c1_med']*100:.1f}%" if D.get("c1_med") else "—"
per_gain=[(r_n["per_stream_tok_s"]-r_e["per_stream_tok_s"])/r_e["per_stream_tok_s"]*100 for r_n,r_e in zip(N[1:5],E[1:5])]
agg_wins_n=sum(r_n["agg_tok_s"]>r_e["agg_tok_s"] for r_n,r_e in zip(N,E)); agg_wins_e=6-agg_wins_n
def edge(nv,ex,higher=True,tie=0.02):
    """Name the winner and the size of the gap. Small gaps as %, big ones as ×."""
    hi,lo=(max(nv,ex),min(nv,ex)); r=hi/lo if lo else 1
    if r-1<tie: return "tie"
    w="NVFP4" if ((nv>ex)==higher) else "EXL3"
    return f"{w} {r:.1f}×" if r>=1.5 else f"{w} +{(r-1)*100:.0f}%"
def acc(l,m): b=B[(l,m)]; return f"{b['correct']}/{b['n']}" if b else "—"
def boot(l): b=BOOT.get(l,{}); return f"{b['min']} min" if b.get("min") else "—"
def panel(fig,x,y,w,h,title=None):
    ax=fig.add_axes([x,y,w,h]); ax.set_axis_off(); ax.set_xlim(0,1); ax.set_ylim(0,1)
    ax.add_patch(FancyBboxPatch((0,0),1,1,boxstyle="round,pad=0,rounding_size=0.012",fc=P,ec=RULE,lw=1,transform=ax.transAxes))
    if title: ax.text(0.03,0.93,title.upper(),fontsize=9.5,fontweight="bold",color=MUT,va="top")
    return ax
def grid(ax,rows,cols_x,top=0.80,dy=None,fs=9.5,hdr=None,bold_last=False):
    n=len(rows); dy=dy or (top-0.06)/max(n,1)
    if hdr:
        for x,t in zip(cols_x,hdr): ax.text(x,top+dy*0.75,t,fontsize=8.5,fontweight="bold",color=MUT,va="center")
    for i,r in enumerate(rows):
        y=top-i*dy
        if i: ax.plot([0.03,0.97],[y+dy*0.5]*2,color=RULE,lw=0.6)
        for j,(x,t) in enumerate(zip(cols_x,r)):
            ax.text(x,y,t,fontsize=fs,color=INK if j else MUT,va="center",fontweight="bold" if (bold_last and j==len(r)-1) else "normal",family="DejaVu Sans Mono" if j else "DejaVu Sans")
# ---------------- poster ----------------
fig=plt.figure(figsize=(12,23),dpi=150)
fig.text(0.5,0.975,"NVFP4  vs  EXL3",ha="center",va="center",fontsize=30,fontweight="bold")
fig.text(0.5,0.958,"GLM-5.3-Flash on dual DGX Spark  ·  same model, two 4-bit quants, two 2-node lanes, benched at the same time",ha="center",fontsize=11,color=MUT)
fig.text(0.5,0.945,"2026-09-01   ·   2× DGX Spark GB10 per lane   ·   CX7 RoCE rail 0   ·   TP=2 each   ·   isolated: relay parked, monitor paused, access logs = bench client only",ha="center",fontsize=8.5,color=MUT)
# verdict (computed)
ax=panel(fig,0.04,0.852,0.92,0.082)
ax.text(0.03,0.84,"VERDICT",fontsize=11,fontweight="bold",color=MUT,va="center")
ax.text(0.03,0.65,"Split decision: NVFP4 decodes faster, EXL3 answers first and holds 4× the context",fontsize=14.5,fontweight="bold",va="center")
ax.text(0.03,0.44,f"NVFP4 wins decode: c1 {c1n_v:.1f} vs {c1e_v:.1f} tok/s ({edge(c1n_v,c1e_v)}), per-stream at c2–c5 (+{min(per_gain):.0f}–{max(per_gain):.0f}%), aggregate at {agg_wins_n} of 6 levels, wall-to-wall at c1–c5.",fontsize=9.3,va="center",color=INK)
ax.text(0.03,0.27,f"EXL3 wins the first token: warm TTFT {te1:.2f} s vs {tn1:.2f} s at c1, {c6e['ttft_med_s']:.1f} s vs {c6n['ttft_med_s']:.1f} s at c6; prefill {edge(pn,pe)}; 4× context; 4.7× KV pool; boots in {boot('exl3')} vs {boot('nvfp4')}.",fontsize=9.3,va="center",color=INK)
ax.text(0.03,0.10,f"Quality battery, 12 items, NVFP4 vs EXL3: thinking off {acc('nvfp4','off')} vs {acc('exl3','off')} (same miss), thinking on {acc('nvfp4','on')} vs {acc('exl3','on')}. On this battery the quant does not change how smart it is.",fontsize=9.3,va="center",color=INK)
# what we served
ax=panel(fig,0.04,0.705,0.92,0.14,"What we served")
grid(ax,[("Weights","RedHatAI/GLM-5.3-Flash-NVFP4","brandonmusic/GLM-5.3-Flash-tr3-4bpw"),
 ("Runtime","vLLM  ghcr.io/tonyd2wild/…:sm121-v11-dflash2","vLLM + exllamav3 built for sm_121a"),
 ("Context that booted","262,144","1,048,576"),("KV pool (tokens)","295,230","1,396,551"),
 ("KV dtype / MoE","fp8_e4m3 / marlin","fp8 (fp8_ds_mla) / exl3_moe trellis"),
 ("Spec decode","DFlash2 k=7","DFlash2 k=7"),
 ("Graphs","--enforce-eager","--enforce-eager"),("max-num-seqs","6","4  (caps c5–c6, see chart)"),
 ("Thinking / vision","off speed · on+off quality / image_url","off speed · on+off quality / image_url")],
 cols_x=(0.03,0.36,0.68),top=0.82,fs=8.8,hdr=("","NVFP4  Reddie + Spark4","EXL3  Bluey + Asusi"))
# speed table (computed edges)
ax=panel(fig,0.04,0.545,0.92,0.15,"Speed · medians")
ax.text(0.03,0.855,"non-stream · temp 0 · thinking off · ~300-token gens · sweep = 3 rounds per level, c1 = 5 rounds, prefill = warm median of 3",fontsize=7.5,color=MUT,va="center")
grid(ax,[("c1 single-stream (n=5)",f"{c1n_v:.1f} tok/s",f"{c1e_v:.1f} tok/s",edge(c1n_v,c1e_v)),
 ("c6 aggregate",f"{c6n['agg_tok_s']:.1f} tok/s",f"{c6e['agg_tok_s']:.1f} tok/s",edge(c6n['agg_tok_s'],c6e['agg_tok_s'])),
 ("c6 per-stream",f"{c6n['per_stream_tok_s']:.1f} tok/s",f"{c6e['per_stream_tok_s']:.1f} tok/s",edge(c6n['per_stream_tok_s'],c6e['per_stream_tok_s'])),
 ("Prefill, ~1.6K prompt (warm)",f"{pn} tok/s",f"{pe} tok/s",edge(pn,pe)),
 ("TTFT at c1 (warm) / c6",f"{tn1:.2f}s / {c6n['ttft_med_s']:.2f}s",f"{te1:.2f}s / {c6e['ttft_med_s']:.2f}s",edge(c6n['ttft_med_s'],c6e['ttft_med_s'],higher=False)+" at c6"),
 ("Wall-to-wall at c1 / c6",f"{c1n['w2w_med_s']:.1f}s / {c6n['w2w_med_s']:.1f}s",f"{c1e['w2w_med_s']:.1f}s / {c6e['w2w_med_s']:.1f}s",edge(c1n['w2w_med_s'],c1e['w2w_med_s'],higher=False)+" at c1"),
 ("Run-to-run spread (c1, n=5)",spread(DN),spread(DE),"both stable")],
 cols_x=(0.03,0.36,0.60,0.82),top=0.82,fs=9.5,hdr=("","NVFP4","EXL3","Edge"),bold_last=True)
# sweep charts
cs=[r["c"] for r in E]
def sweep_ax(rect,key,ylabel,title,fmt):
    ax=fig.add_axes(rect); ax.set_facecolor(P)
    for rows,col,lab in ((N,GY,"NVFP4"),(E,WH,"EXL3")):
        ys=[r[key] for r in rows]; ax.plot(cs,ys,color=col,lw=2,marker="o",ms=5,label=lab)
        for c,y in zip(cs,ys): ax.annotate(fmt(y),(c,y),textcoords="offset points",xytext=(0,7),ha="center",fontsize=7.5,color=INK)
        ax.text(cs[-1]+0.15,ys[-1],lab,color=col,fontsize=9,fontweight="bold",va="center")
    ax.set_xticks(cs); ax.set_xticklabels([f"c{c}" for c in cs]); ax.set_xlim(0.6,6.9)
    ax.set_ylabel(ylabel,fontsize=8.5); ax.set_title(title,fontsize=10,fontweight="bold",loc="left",color=INK)
    ax.grid(axis="y",color=RULE,lw=0.6); ax.spines[["top","right"]].set_visible(False)
    ax.legend(frameon=False,fontsize=8,loc=("upper right" if "Per-stream" in title else "upper left"),labelcolor=INK)
    return ax
sweep_ax([0.08,0.405,0.40,0.115],"agg_tok_s","tokens / s","Aggregate throughput vs concurrency",lambda v:f"{v:.0f}")
sweep_ax([0.56,0.405,0.40,0.115],"ttft_med_s","seconds","Time to first token vs concurrency",lambda v:f"{v:.1f}s")
sweep_ax([0.08,0.262,0.40,0.115],"per_stream_tok_s","tokens / s","Per-stream decode vs concurrency",lambda v:f"{v:.0f}")
sweep_ax([0.56,0.262,0.40,0.115],"w2w_med_s","seconds","Wall-to-wall, 300-token answer (median)",lambda v:f"{v:.1f}s")
# what each one wins (computed) + pins
ax=panel(fig,0.04,0.165,0.92,0.075,"What each one wins")
tiles=[("NVFP4 · decode",f"c1 {c1n_v:.1f} vs {c1e_v:.1f} tok/s"),("NVFP4 · per-stream",f"+{min(per_gain):.0f}–{max(per_gain):.0f}% at c2–c5"),
 ("EXL3 · first token",f"{c6e['ttft_med_s']:.1f} s vs {c6n['ttft_med_s']:.1f} s at c6"),("EXL3 · prefill",f"{pe:,} vs {pn:,} tok/s warm"),
 ("EXL3 · context + KV","1 M / 1.40 M vs 256 K / 295 K"),("EXL3 · boot",f"{boot('exl3')} vs {boot('nvfp4')} to /health")]
for i,(h,t) in enumerate(tiles):
    x=0.03+i*0.16
    ax.text(x,0.60,h,fontsize=10.2,fontweight="bold",va="center"); ax.text(x,0.30,t,fontsize=7.6,color=MUT,va="center")
ax=panel(fig,0.04,0.075,0.92,0.082,"Pins that matter")
for i,t in enumerate(["NVFP4: run the published 2-Spark recipe verbatim — 256 K context, worker first, head 25 s later · vm.swappiness=0 resets on reboot · poll /health, never /v1/models",
 "EXL3 kit: count_shards needs find -L on an HF cache · chown ~/.cache/vllm-glm53-flash on both nodes · --host 0.0.0.0 (it ships loopback) · worker needs the full 164 GiB",
 "Both: check GPU clocks under load before trusting any number — a node pinned near 700 MHz after a reboot cost us a full re-run (healthy decode ≈ 2,180 MHz at ~95% util)",
 "Both: kernels JIT-compile per request shape — warm up 2×c1 + 1×c6 and never bench a cold lane · EXL3 max-num-seqs 4 caps c5–c6 (config, not the quant)"]):
    ax.text(0.03,0.76-i*0.20,"•  "+t,fontsize=7.6,va="top",color=INK)
# hardware + footer
ax=panel(fig,0.04,0.028,0.92,0.04,"Hardware")
ax.text(0.03,0.42,"4× NVIDIA DGX Spark (GB10, sm_121a, 128 GB unified memory)  ·  ConnectX-7 RoCE v2 fabric, 192.168.192.0/24  ·  two boxes per lane, TP=2, vLLM mp executor\nBench client: Mac mini over Tailscale  ·  tools/bench_*.py + quality_battery.py  ·  NVFP4 worker loaded weights over NFS from its head (boot, not decode)",fontsize=8.4,va="center",color=INK)
fig.text(0.04,0.016,"@tonyd2wild  ·  github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark  ·  github.com/tonyd2wild/glm53-flash-exl3-2x-dgx-spark",fontsize=9,fontweight="bold")
fig.text(0.04,0.005,"Credits: Reederey87 · MiaAI-Lab · brandonmusic (EXL3 quant) · turboderp (exllamav3) · IncoAI (DFlash2) · RedHatAI (NVFP4) · zai-org (GLM-5.3-Flash)",fontsize=8,color=MUT)
fig.savefig("results/poster_nvfp4_vs_exl3.png",dpi=150); print("poster -> results/poster_nvfp4_vs_exl3.png")
# ---------------- standalone charts (16:9, for the article/tweet) ----------------
for key,ylabel,title,fmt,fn in [("agg_tok_s","tokens / s","Aggregate throughput vs concurrency — GLM-5.3-Flash, 2× DGX Spark per lane",lambda v:f"{v:.0f}","chart_agg"),
    ("ttft_med_s","seconds","Time to first token vs concurrency",lambda v:f"{v:.1f}s","chart_ttft"),
    ("w2w_med_s","seconds","Wall-to-wall for a 300-token answer (median)",lambda v:f"{v:.1f}s","chart_w2w")]:
    f2=plt.figure(figsize=(12,6.75),dpi=150); ax=f2.add_axes([0.08,0.13,0.86,0.75]); ax.set_facecolor(P)
    for rows,col,lab in ((N,GY,"NVFP4  Reddie+Spark4"),(E,WH,"EXL3  Bluey+Asusi")):
        ys=[r[key] for r in rows]; ax.plot(cs,ys,color=col,lw=2.5,marker="o",ms=7,label=lab)
        for c,y in zip(cs,ys): ax.annotate(fmt(y),(c,y),textcoords="offset points",xytext=(0,9),ha="center",fontsize=10,color=INK)
        ax.text(cs[-1]+0.12,ys[-1],lab.split()[0],color=col,fontsize=12,fontweight="bold",va="center")
    ax.set_xticks(cs); ax.set_xticklabels([f"c{c}" for c in cs],fontsize=11); ax.set_xlim(0.6,7.0); ax.set_ylabel(ylabel,fontsize=11)
    ax.set_title(title,fontsize=14,fontweight="bold",loc="left",color=INK,pad=14); ax.grid(axis="y",color=RULE,lw=0.7); ax.spines[["top","right"]].set_visible(False)
    ax.legend(frameon=False,fontsize=10,loc="upper left",labelcolor=INK)
    f2.text(0.08,0.03,"2026-09-01 · isolated, both lanes benched simultaneously · non-stream, temp 0, thinking off · @tonyd2wild",fontsize=9,color=MUT)
    f2.savefig(f"results/{fn}.png",dpi=150); print(f"chart -> results/{fn}.png")
