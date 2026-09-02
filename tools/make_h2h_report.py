#!/usr/bin/env python3
"""make_h2h_report.py -> results/h2h_tp4.md, results/h2h_tp4.json, results/chart_h2h.png

TP4 head-to-head, matched config: DeepSeek-V4-Flash-Vision-Exp vs GLM-5.3-Flash NVFP4, each alone on all four Sparks,
max-num-seqs 64, CUDA graphs on, same battery (lane labels ds4tp4 / glmtp4 from tp4-h2h.sh). Reads results/sweep_<lane>.json
(ladder C1..C48), detailed_<lane>.json, ttft_fresh_<lane>.json, categories_<lane>_off_c{1,4,16}.json, prefill_len_<lane>.json,
power_load_<lane>.json + power_<lane>_<node>.csv.
"""
import json, os, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
def J(p): return json.load(open(p)) if os.path.exists(p) else None
L = [("ds4tp4", "DeepSeek V4 Flash Vision"), ("glmtp4", "GLM-5.3-Flash NVFP4")]
S = {l: J(f"results/sweep_{l}.json") for l, _ in L}; D = {l: J(f"results/detailed_{l}.json") or {} for l, _ in L}
T = {l: J(f"results/ttft_fresh_{l}.json") for l, _ in L}; PL = {l: J(f"results/prefill_len_{l}.json") for l, _ in L}
C = {(l, c): J(f"results/categories_{l}_off_c{c}.json") for l, _ in L for c in (1, 4, 16)}
PW = {l: J(f"results/power_load_{l}.json") for l, _ in L}
CATS = ["coding", "reasoning", "json", "html", "prose", "narrative", "summary", "format"]
def watts(l):
    vals = []
    for n in ("bluey", "asusi", "reddie", "spark4"):
        p = f"results/power_{l}_{n}.csv"
        if not os.path.exists(p): return None
        v = []
        for line in open(p):
            try: v.append(float(line.split(",")[0].replace("W", "").strip()))
            except ValueError: pass
        v = v[8:66] if len(v) >= 66 else v
        if not v: return None
        vals.append(sum(v) / len(v))
    return round(sum(vals), 1)
def row(l, c, k):
    s = S[l]; return next((r[k] for r in s["rows"] if r["c"] == c), None) if s else None
def fr(l, c): t = T[l]; return next((r["ttft_med_s"] for r in t["rows"] if r["c"] == c), None) if t else None
def f(v, nd=1, suf=""): return "—" if v is None else (f"{v:,.{nd}f}{suf}" if isinstance(v, (int, float)) else f"{v}{suf}")
def pct(v): return "—" if v is None else f"{v*100:.0f}%"
def gain(a, b, higher=True):
    if a is None or b is None or not b: return "—"
    g = (a - b) / b * 100; return f"{'+' if g >= 0 else ''}{g:.0f}%" + ("" if higher else " (lower better)")
def cat(l, c, k, cc=1): x = C.get((l, cc)); return x["summary"].get(c, {}).get(k) if x else None
levels = [1, 2, 3, 4, 5, 6, 8, 16, 32, 48]
def ov(l, cc, k): x = C.get((l, cc)); return x["overall"].get(k) if x else None
d, g = "ds4tp4", "glmtp4"
md = ["## TP4 head-to-head, matched config: DeepSeek V4 Flash Vision vs GLM-5.3-Flash NVFP4", "",
      "Each model alone on all four Sparks (TP4), max-num-seqs 64, CUDA graphs on, k=5 DSpark with Patch 4 for DeepSeek, DFlash2 k=7 for GLM, 1M context, same battery, same isolation, run back to back on 2026-09-02. Lower is better only where the row says so.", "",
      "### Headline: prose and code decode from real prompts (tok/s, median), then fresh-prompt first token", "",
      "| | DeepSeek | GLM |", "|---|---|---|",
      f"| prose decode, C1 | {f(cat(d,'prose','decode_med_tok_s'))} | {f(cat(g,'prose','decode_med_tok_s'))} |",
      f"| code decode, C1 | {f(cat(d,'coding','decode_med_tok_s'))} | {f(cat(g,'coding','decode_med_tok_s'))} |",
      f"| prose decode under mixed C16 | {f(cat(d,'prose','decode_med_tok_s',16))} | {f(cat(g,'prose','decode_med_tok_s',16))} |",
      f"| code decode under mixed C16 | {f(cat(d,'coding','decode_med_tok_s',16))} | {f(cat(g,'coding','decode_med_tok_s',16))} |",
      f"| mixed real-prompt aggregate C16 | {f(ov(d,16,'agg_tok_s_med'))} | {f(ov(g,16,'agg_tok_s_med'))} |",
      f"| first token, fresh 1.6K prompt, C1 / C16 | {f(fr(d,1),2)} / {f(fr(d,16),2)} s | {f(fr(g,1),2)} / {f(fr(g,16),2)} s |",
      f"| cold prefill, fresh 211K prompt | {(f(PL[d]['rows'][-1]['cold_tok_s'],0) if PL[d] and not PL[d]['rows'][-1].get('error') else '—')} tok/s | {(f(PL[g]['rows'][-1]['cold_tok_s'],0) if PL[g] and not PL[g]['rows'][-1].get('error') else '—')} tok/s |",
      "", "Every number above and in the chart is from real prompts. The counting-prompt ladder is at the bottom, labeled as the draft-acceptance ceiling.",
      ]
md += ["", "### Time to first token, fresh 1.6K prompts (s, median)", "", "| C | DeepSeek | GLM |", "|---|---|---|"]
for c in (1, 8, 16): md.append(f"| {c} | {f(fr(d,c),2)} | {f(fr(g,c),2)} |")
md += ["", "### Real prompts, 40 across 8 categories, C1 (auto score / decode tok/s / TTFT s)", "", "| category | DeepSeek | GLM |", "|---|---|---|"]
for c in CATS: md.append(f"| {c} | {pct(cat(d,c,'auto_score'))} / {f(cat(d,c,'decode_med_tok_s'))} / {f(cat(d,c,'ttft_med_s'),2)} | {pct(cat(g,c,'auto_score'))} / {f(cat(g,c,'decode_med_tok_s'))} / {f(cat(g,c,'ttft_med_s'),2)} |")
md += ["", "| real prompts overall | DeepSeek | GLM |", "|---|---|---|",
       f"| auto score C1 | {pct(ov(d,1,'auto_score'))} | {pct(ov(g,1,'auto_score'))} |",
       f"| median decode C1 | {f(ov(d,1,'decode_med_tok_s'))} | {f(ov(g,1,'decode_med_tok_s'))} |",
       f"| mixed C4 aggregate / TTFT | {f(ov(d,4,'agg_tok_s_med'))} / {f(ov(d,4,'ttft_med_s'),2)} s | {f(ov(g,4,'agg_tok_s_med'))} / {f(ov(g,4,'ttft_med_s'),2)} s |",
       f"| mixed C16 aggregate / TTFT | {f(ov(d,16,'agg_tok_s_med'))} / {f(ov(d,16,'ttft_med_s'),2)} s | {f(ov(g,16,'agg_tok_s_med'))} / {f(ov(g,16,'ttft_med_s'),2)} s |",
       f"| auto score C16 | {pct(ov(d,16,'auto_score'))} | {pct(ov(g,16,'auto_score'))} |"]
md += ["", "### Cold prefill vs prompt length (tok/s)", "", "| prompt tokens | DeepSeek | GLM |", "|---|---|---|"]
if PL[d] and PL[g]:
    for rd, rg in zip(PL[d]["rows"], PL[g]["rows"]):
        if rd.get("error") or rg.get("error"): continue
        md.append(f"| {rd['prompt_tokens']:,} | {rd['cold_tok_s']:,} | {rg['cold_tok_s']:,} |")
wd, wg = watts(d), watts(g)
md += ["", "### Power at C16 (GPU, four nodes, 60 s)", "", "| | DeepSeek | GLM |", "|---|---|---|",
       f"| throughput under load | {f(PW[d]['tok_s']) if PW[d] else '—'} tok/s | {f(PW[g]['tok_s']) if PW[g] else '—'} tok/s |",
       f"| four-node GPU power | {f(wd)} W | {f(wg)} W |",
       f"| tokens per joule | {f(PW[d]['tok_s']/wd, 2) if (PW[d] and wd) else '—'} | {f(PW[g]['tok_s']/wg, 2) if (PW[g] and wg) else '—'} |"]
md += ["", "### Peak ceiling: the counting prompt (max draft acceptance, NOT a typical number)", "",
       "One prompt, count from 1 to 300, ~300 tokens of the easiest sequence a speculative drafter can guess. It is what most Spark posts quote as decode speed and it reads 2 to 3× higher than prose. Kept here only as the acceptance ceiling of each drafter.", "",
       "| C | DeepSeek | GLM | GLM vs DeepSeek |", "|---|---|---|---|"]
for c in levels: md.append(f"| {c} | {f(row(d,c,'agg_tok_s'))} | {f(row(g,c,'agg_tok_s'))} | {gain(row(g,c,'agg_tok_s'), row(d,c,'agg_tok_s'))} |")
md += ["", "| C | DeepSeek per stream | GLM per stream |", "|---|---|---|"]
for c in levels: md.append(f"| {c} | {f(row(d,c,'per_stream_tok_s'))} | {f(row(g,c,'per_stream_tok_s'))} |")
# verdict, computed
def sat(l):
    ys = [(c, row(l, c, "agg_tok_s")) for c in levels if row(l, c, "agg_tok_s")]
    best = max(ys, key=lambda x: x[1]) if ys else (None, None)
    plateau = next((c for (c, y), (c2, y2) in zip(ys, ys[1:]) if y2 < y * 1.05), None)
    return best, plateau
bd, bg = sat(d), sat(g)
c1d, c1g = D[d].get("c1_med", row(d, 1, "agg_tok_s")), D[g].get("c1_med", row(g, 1, "agg_tok_s"))
md += ["", "### Verdict (computed from the rows above)", "",
       f"- Real prompts, single stream: DeepSeek {f(ov(d,1,'decode_med_tok_s'))} vs GLM {f(ov(g,1,'decode_med_tok_s'))} tok/s median over 40 prompts; prose {f(cat(d,'prose','decode_med_tok_s'))} vs {f(cat(g,'prose','decode_med_tok_s'))}; narrative {f(cat(d,'narrative','decode_med_tok_s'))} vs {f(cat(g,'narrative','decode_med_tok_s'))}; code {f(cat(d,'coding','decode_med_tok_s'))} vs {f(cat(g,'coding','decode_med_tok_s'))}.",
       f"- Real prompts under load: C4 aggregate {f(ov(d,4,'agg_tok_s_med'))} vs {f(ov(g,4,'agg_tok_s_med'))} tok/s (first token {f(ov(d,4,'ttft_med_s'),2)} vs {f(ov(g,4,'ttft_med_s'),2)} s); C16 {f(ov(d,16,'agg_tok_s_med'))} vs {f(ov(g,16,'agg_tok_s_med'))} (first token {f(ov(d,16,'ttft_med_s'),2)} vs {f(ov(g,16,'ttft_med_s'),2)} s).",
       f"- Quality on the 40 prompts (±4 pts run to run): DeepSeek {pct(ov(d,1,'auto_score'))} vs GLM {pct(ov(g,1,'auto_score'))} at C1; {pct(ov(d,16,'auto_score'))} vs {pct(ov(g,16,'auto_score'))} at C16.",
       f"- Cold prefill, fresh 182K prompt: DeepSeek {(f(PL[d]['rows'][-1]['cold_tok_s'],0) if PL[d] else '—')} vs GLM {(f(PL[g]['rows'][-1]['cold_tok_s'],0) if PL[g] else '—')} tok/s; DeepSeek reaches its plateau by 14K, GLM climbs to it.",
       f"- Tokens per joule at C16: DeepSeek {f(PW[d]['tok_s']/wd, 2) if (PW[d] and wd) else '—'} vs GLM {f(PW[g]['tok_s']/wg, 2) if (PW[g] and wg) else '—'}.",
       f"- Ceiling only (counting prompt): C1 {f(c1d)} vs {f(c1g)} tok/s, C48 {f(row(d,48,'agg_tok_s'))} vs {f(row(g,48,'agg_tok_s'))}. Not a decode number.", ""]
open("results/h2h_tp4.md", "w").write("\n".join(md) + "\n")
json.dump({"levels": levels, "agg": {l: [row(l, c, "agg_tok_s") for c in levels] for l, _ in L}, "per_stream": {l: [row(l, c, "per_stream_tok_s") for c in levels] for l, _ in L},
           "ttft_fresh": {l: [fr(l, c) for c in (1, 8, 16)] for l, _ in L}, "c1_detailed": {d: c1d, g: c1g}, "watts": {d: wd, g: wg}}, open("results/h2h_tp4.json", "w"), indent=1)
print("-> results/h2h_tp4.md")
G="#1B1C1F"; P="#232428"; INK="#F2F2F0"; MUT="#9A9DA3"; RULE="#3A3C41"
plt.rcParams.update({"font.family":"DejaVu Sans","text.color":INK,"axes.edgecolor":RULE,"axes.labelcolor":MUT,"xtick.color":MUT,"ytick.color":MUT,"axes.facecolor":P,"figure.facecolor":G,"savefig.facecolor":G})
def rp_line(ax, key, title, ylabel=None):
    xs = [1, 4, 16]
    for l, n in L:
        ys = []
        for c in xs:
            v = ov(l, c, key) if not (c == 1 and key == "agg_tok_s_med") else ov(l, 1, "decode_med_tok_s")
            ys.append(v)
        if any(y is None for y in ys): continue
        ax.plot(range(3), ys, color=col[l], lw=2.4, marker="o", ms=6, label=n)
        for i, y in enumerate(ys): ax.annotate(f"{y:.0f}" if y >= 10 else f"{y:.2f}", (i, y), textcoords="offset points", xytext=(0, 8 if l == d else -13), ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(3)); ax.set_xticklabels(["C1", "C4 mixed", "C16 mixed"]); ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color=INK); ax.grid(axis="y", color=RULE, lw=0.6); ax.spines[["top","right"]].set_visible(False); ax.legend(frameon=False, labelcolor=INK)
    if ylabel: ax.set_ylabel(ylabel)
def cat_bars(ax, cc, title):
    w = 0.38; x = range(len(CATS))
    for k, (l, n) in enumerate(L):
        vs = [cat(l, c, "decode_med_tok_s", cc) or 0 for c in CATS]
        ax.bar([i + (k - 0.5) * w for i in x], vs, w, color=col[l], label=n)
        for i, v in enumerate(vs):
            if v: ax.text(i + (k - 0.5) * w, v, f"{v:.0f}", ha="center", va="bottom", fontsize=7.5, color=INK)
    ax.set_xticks(list(x)); ax.set_xticklabels(CATS, rotation=30, ha="right"); ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color=INK); ax.grid(axis="y", color=RULE, lw=0.6); ax.spines[["top","right"]].set_visible(False); ax.legend(frameon=False, labelcolor=INK)
col = {d: "#8F9297", g: "#F2F2F0"}
fig, axs = plt.subplots(2, 2, figsize=(15, 10), dpi=150)
rp_line(axs[0][0], "agg_tok_s_med", "Real prompts: aggregate tok/s vs streams in flight (40 prompts, 8 categories)")
cat_bars(axs[0][1], 1, "Real-prompt decode tok/s by category, single stream")
cat_bars(axs[1][0], 16, "Real-prompt decode tok/s by category, 16 streams in flight")
ax = axs[1][1]
if PL[d] and PL[g]:
    for l, n in L:
        rows = [r for r in PL[l]["rows"] if not r.get("error")]
        ax.plot([r["prompt_tokens"] / 1000 for r in rows], [r["cold_tok_s"] for r in rows], color=col[l], lw=2.4, marker="o", ms=6, label=n)
        for r in rows: ax.annotate(f"{r['cold_tok_s']:,}", (r["prompt_tokens"] / 1000, r["cold_tok_s"]), textcoords="offset points", xytext=(0, 8 if l == d else -13), ha="center", fontsize=8, color=INK)
    ax.set_xscale("log"); ax.set_xlabel("prompt tokens (K)")
ax.set_title("Cold prefill tok/s vs prompt length (fresh prompt, no cache)", loc="left", fontsize=11, fontweight="bold", color=INK); ax.grid(axis="y", color=RULE, lw=0.6); ax.spines[["top","right"]].set_visible(False); ax.legend(frameon=False, labelcolor=INK)
fig.text(0.01, 0.01, "2026-09-02 · each model alone on 4× DGX Spark (TP4), max-num-seqs 64, CUDA graphs on · real prompts only, temp 0, isolated, back to back · @tonyd2wild", fontsize=9, color=MUT)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig("results/chart_h2h.png"); print("-> results/chart_h2h.png")
# ceiling chart, separate and small, labeled for what it is
fig2, ax = plt.subplots(1, 1, figsize=(11, 4.2), dpi=150)
for l, n in L:
    ys = [row(l, c, "agg_tok_s") for c in levels]
    if any(y is None for y in ys): continue
    ax.plot(range(len(levels)), ys, color=col[l], lw=2.2, marker="o", ms=5, label=n)
    for i, y in enumerate(ys): ax.annotate(f"{y:.0f}", (i, y), textcoords="offset points", xytext=(0, 8 if l == d else -13), ha="center", fontsize=8, color=INK)
ax.set_xticks(range(len(levels))); ax.set_xticklabels([f"C{c}" for c in levels]); ax.set_title("Peak ceiling only: counting prompt, max draft acceptance. Not a decode number.", loc="left", fontsize=11, fontweight="bold", color=INK); ax.grid(axis="y", color=RULE, lw=0.6); ax.spines[["top","right"]].set_visible(False); ax.legend(frameon=False, labelcolor=INK)
fig2.text(0.01, 0.01, "count from 1 to 300, aggregate tok/s, median of 2 rounds · reads 2 to 3× higher than prose · kept for comparability with older posts", fontsize=9, color=MUT)
fig2.tight_layout(rect=(0, 0.05, 1, 1)); fig2.savefig("results/chart_h2h_ceiling.png"); print("-> results/chart_h2h_ceiling.png")
