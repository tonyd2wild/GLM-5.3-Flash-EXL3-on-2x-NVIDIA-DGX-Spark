#!/usr/bin/env python3
"""make_category_report.py  -> results/categories_summary.json, results/categories_summary.md, results/chart_categories.png

Reads results/categories_<lane>_off_c1.json (required), _off_c4.json, _on_c1.json (optional), results/judge_off.json
(optional) and results/prefill_len_<lane>.json (optional) and produces one summary the article generator can embed.
Charcoal-and-white chart: per-category decode tok/s and TTFT (c1, thinking off) for both lanes.
"""
import json, os, statistics, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
def J(p): return json.load(open(p)) if os.path.exists(p) else None
L = ("nvfp4", "exl3"); CATS = ["coding", "reasoning", "json", "html", "prose", "narrative", "summary", "format"]
C1 = {l: J(f"results/categories_{l}_off_c1.json") for l in L}; C4 = {l: J(f"results/categories_{l}_off_c4.json") for l in L}
ON = {l: J(f"results/categories_{l}_on_c1.json") for l in L}; JD = J("results/judge_off.json"); PL = {l: J(f"results/prefill_len_{l}.json") for l in L}
assert all(C1.values()), "run bench_categories.py (c1, off) on both lanes first"
AG = {(l, t): J(f"results/agent_loop_{l}_{t}.json") for l in L for t in ("short", "long")}
DET = J("results/determinism.json") or {}
PWR = {l: J(f"results/power_load_{l}.json") for l in L}
def watts(node):
    p = f"results/power_{node}.csv"
    if not os.path.exists(p): return None
    vals = []
    for line in open(p):
        try: vals.append(float(line.split(",")[0].replace("W", "").strip()))
        except ValueError: pass
    return round(sum(vals) / len(vals), 1) if vals else None
NODES = {"nvfp4": ("reddie", "spark4"), "exl3": ("bluey", "asusi")}
PW = {l: [watts(n) for n in NODES[l]] for l in L}
def s(d, l, c, k):
    x = d.get(l) if d else None; return (x["summary"].get(c, {}).get(k) if x else None)
def fmt(v, nd=1, suf=""): return "—" if v is None else (f"{v:.{nd}f}{suf}" if isinstance(v, float) else f"{v}{suf}")
def pct(v): return "—" if v is None else f"{v*100:.0f}%"
rows = []
for c in CATS:
    jt = (JD or {}).get("tally", {}).get(c, {})
    rows.append({"category": c,
                 "auto_nvfp4": s(C1, "nvfp4", c, "auto_score"), "auto_exl3": s(C1, "exl3", c, "auto_score"),
                 "on_nvfp4": s(ON, "nvfp4", c, "auto_score"), "on_exl3": s(ON, "exl3", c, "auto_score"),
                 "judge_nvfp4": jt.get("nvfp4"), "judge_exl3": jt.get("exl3"), "judge_tie": jt.get("tie"),
                 "ttft_nvfp4": s(C1, "nvfp4", c, "ttft_med_s"), "ttft_exl3": s(C1, "exl3", c, "ttft_med_s"),
                 "dec_nvfp4": s(C1, "nvfp4", c, "decode_med_tok_s"), "dec_exl3": s(C1, "exl3", c, "decode_med_tok_s"),
                 "tok_nvfp4": s(C1, "nvfp4", c, "tokens_med"), "tok_exl3": s(C1, "exl3", c, "tokens_med")})
ov = {l: C1[l]["overall"] for l in L}; ov4 = {l: (C4[l]["overall"] if C4[l] else None) for l in L}; ovon = {l: (ON[l]["overall"] if ON[l] else None) for l in L}
# item-level disagreements on auto-graded categories (thinking off)
IA = {i["id"]: i for i in C1["nvfp4"]["items"]}; IB = {i["id"]: i for i in C1["exl3"]["items"]}
diff = [{"id": k, "category": IA[k]["category"], "nvfp4": IA[k]["score"], "exl3": IB[k]["score"], "nvfp4_fails": IA[k]["fails"], "exl3_fails": IB[k]["fails"]}
        for k in IA if k in IB and IA[k]["score"] is not None and IB[k]["score"] is not None and abs(IA[k]["score"] - IB[k]["score"]) > 1e-9]
jt_all = {}
if JD:
    for c, t in JD["tally"].items():
        for k, v in t.items(): jt_all[k] = jt_all.get(k, 0) + v
def tpj(l):
    w = PW[l]; p = PWR[l]
    if not p or any(x is None for x in w): return None
    return round(p["tok_s"] / sum(w), 3)
summary = {"agent": {f"{l}_{t}": ({k: AG[(l, t)][k] for k in ("turns", "ctx_last", "ttft_med_s", "ttft_p90_s", "ttft_first_s", "ttft_last_s", "decode_med_tok_s", "total_s")} if AG[(l, t)] else None) for l in L for t in ("short", "long")},
           "determinism": DET, "power": {l: {"nodes_w": PW[l], "load": PWR[l], "tok_per_joule": tpj(l)} for l in L},
           "rows": rows, "overall": ov, "overall_c4": ov4, "overall_on": ovon, "judge_total": jt_all, "judge_model": (JD or {}).get("judge"),
           "diff_items": diff, "prefill_len": {l: (PL[l]["rows"] if PL[l] else None) for l in L}, "n_prompts": C1["nvfp4"]["n"]}
json.dump(summary, open("results/categories_summary.json", "w"), indent=1)
# ---- markdown
md = ["## Real prompts: 40 across 8 categories (thinking off, c1, streaming)", "",
      "| category | auto score NVFP4 | auto score EXL3 | judge (NVFP4 / EXL3 / tie) | TTFT NVFP4 | TTFT EXL3 | decode NVFP4 | decode EXL3 | tokens (med) |", "|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    jd = "—" if r["judge_nvfp4"] is None else f"{r['judge_nvfp4']} / {r['judge_exl3']} / {r['judge_tie']}"
    md.append(f"| {r['category']} | {pct(r['auto_nvfp4'])} | {pct(r['auto_exl3'])} | {jd} | {fmt(r['ttft_nvfp4'],2,' s')} | {fmt(r['ttft_exl3'],2,' s')} | {fmt(r['dec_nvfp4'])} | {fmt(r['dec_exl3'])} | {r['tok_nvfp4']} / {r['tok_exl3']} |")
md += ["", f"Overall auto score (checkable categories): NVFP4 {pct(ov['nvfp4']['auto_score'])}, EXL3 {pct(ov['exl3']['auto_score'])}. "
       f"Median TTFT across all 40: NVFP4 {ov['nvfp4']['ttft_med_s']} s, EXL3 {ov['exl3']['ttft_med_s']} s. Median decode: NVFP4 {ov['nvfp4']['decode_med_tok_s']} tok/s, EXL3 {ov['exl3']['decode_med_tok_s']} tok/s."]
if all(ov4.values()): md.append(f"Mixed load, c4 (four different prompt types in flight): aggregate NVFP4 {ov4['nvfp4']['agg_tok_s_med']} tok/s vs EXL3 {ov4['exl3']['agg_tok_s_med']} tok/s; median TTFT {ov4['nvfp4']['ttft_med_s']} s vs {ov4['exl3']['ttft_med_s']} s; auto score {pct(ov4['nvfp4']['auto_score'])} vs {pct(ov4['exl3']['auto_score'])}.")
if all(ovon.values()): md.append(f"Thinking on (coding + reasoning): auto score NVFP4 {pct(ovon['nvfp4']['auto_score'])} vs EXL3 {pct(ovon['exl3']['auto_score'])}; median TTFT {ovon['nvfp4']['ttft_med_s']} s vs {ovon['exl3']['ttft_med_s']} s.")
if jt_all: md.append(f"Blind pairwise judge ({summary['judge_model']}), both orders, win only if consistent: NVFP4 {jt_all.get('nvfp4',0)}, EXL3 {jt_all.get('exl3',0)}, tie {jt_all.get('tie',0)}.")
if diff:
    md += ["", "Items where the auto score differed:"] + [f"- {d['id']} ({d['category']}): NVFP4 {pct(d['nvfp4'])} {('[' + '; '.join(d['nvfp4_fails'])[:60] + ']') if d['nvfp4_fails'] else ''} · EXL3 {pct(d['exl3'])} {('[' + '; '.join(d['exl3_fails'])[:60] + ']') if d['exl3_fails'] else ''}" for d in diff]
else: md.append("\nNo auto-graded item scored differently between the lanes.")
if all(ovon.values()) and all(ON[l]["n"] >= 40 for l in L):
    md += ["", "### Thinking on, all 40 prompts", "", "| category | auto NVFP4 | auto EXL3 | TTFT NVFP4 | TTFT EXL3 | decode NVFP4 | decode EXL3 | tokens (med) |", "|---|---|---|---|---|---|---|---|"]
    for c in CATS: md.append(f"| {c} | {pct(s(ON,'nvfp4',c,'auto_score'))} | {pct(s(ON,'exl3',c,'auto_score'))} | {fmt(s(ON,'nvfp4',c,'ttft_med_s'),2,' s')} | {fmt(s(ON,'exl3',c,'ttft_med_s'),2,' s')} | {fmt(s(ON,'nvfp4',c,'decode_med_tok_s'))} | {fmt(s(ON,'exl3',c,'decode_med_tok_s'))} | {s(ON,'nvfp4',c,'tokens_med')} / {s(ON,'exl3',c,'tokens_med')} |")
    md.append(f"\nOverall with thinking on: auto score NVFP4 {pct(ovon['nvfp4']['auto_score'])} vs EXL3 {pct(ovon['exl3']['auto_score'])}; median TTFT {ovon['nvfp4']['ttft_med_s']} s vs {ovon['exl3']['ttft_med_s']} s; median decode {ovon['nvfp4']['decode_med_tok_s']} vs {ovon['exl3']['decode_med_tok_s']} tok/s.")
if all(AG.values()):
    md += ["", "### Agent loop: the whole conversation re-sent every turn", "", "Every turn re-sends the full history (system prompt, every earlier user turn, every earlier assistant reply) plus one new instruction; the assistant's real reply is appended for the next turn. Thinking off, 200-token replies. The long version carries a 30K-token document in the first turn, so every later turn re-sends it too.", "",
           "| run | turns | final context (tok) | TTFT first turn | TTFT median | TTFT p90 | TTFT last turn | decode (med) | total |", "|---|---|---|---|---|---|---|---|---|"]
    for t in ("short", "long"):
        for l in L:
            g = AG[(l, t)]; md.append(f"| {l.upper()} {t} | {g['turns']} | {g['ctx_last']:,} | {g['ttft_first_s']} s | {g['ttft_med_s']} s | {g['ttft_p90_s']} s | {g['ttft_last_s']} s | {g['decode_med_tok_s']} tok/s | {g['total_s']} s |")
if DET:
    md += ["", "### Determinism at temperature 0", "", "The same 40 prompts three times per lane, temperature 0, same state.", "", "| lane | outputs byte-identical across runs | auto score per run | items whose score changed | token-count spread, median / max |", "|---|---|---|---|---|"]
    for l in L:
        d = DET.get(l)
        if d: md.append(f"| {l.upper()} | {d['identical_outputs']}/{d['n']} ({d['identical_pct']}%) | {' / '.join(pct(x) for x in d['auto_score_per_run'])} | {d['score_flips']} ({', '.join(d['score_flip_ids']) or 'none'}) | {d['token_spread_median']} / {d['token_spread_max']} |")
if all(tpj(l) for l in L):
    md += ["", "### Tokens per joule", "", "GPU power from nvidia-smi on both nodes of each lane (1 Hz for 60 s) during a c4 counting load; tokens per joule = lane throughput divided by the sum of the two nodes' average GPU power. GPU power only, not wall power.", "",
           "| lane | throughput under load | node GPU power (W) | lane GPU power (W) | tokens per joule |", "|---|---|---|---|---|"]
    for l in L: md.append(f"| {l.upper()} | {PWR[l]['tok_s']} tok/s | {PW[l][0]} + {PW[l][1]} | {round(sum(PW[l]),1)} | {tpj(l)} |")
if all(PL.values()):
    md += ["", "### Prefill vs prompt length", "", "Cold = first request at that length, a new prompt: this is the real prefill compute. Repeat = the identical prompt sent again, which is a prefix-cache hit on both engines and measures the cache, not prefill.", "", "| prompt tokens | NVFP4 cold tok/s (s) | EXL3 cold tok/s (s) | NVFP4 repeat | EXL3 repeat |", "|---|---|---|---|---|"]
    for rn, re_ in zip(PL["nvfp4"]["rows"], PL["exl3"]["rows"]):
        if rn.get("error") or re_.get("error"): md.append(f"| {rn.get('target')} | {'error' if rn.get('error') else rn['warm_tok_s']} | {'error' if re_.get('error') else re_['warm_tok_s']} |"); continue
        md.append(f"| {rn['prompt_tokens']:,} | {rn['cold_tok_s']:,} ({rn['cold_s']} s) | {re_['cold_tok_s']:,} ({re_['cold_s']} s) | {rn['warm_tok_s']:,} ({rn['warm_s']} s) | {re_['warm_tok_s']:,} ({re_['warm_s']} s) |")
open("results/categories_summary.md", "w").write("\n".join(md) + "\n"); print("-> results/categories_summary.md")
# ---- chart
G="#1B1C1F"; P="#232428"; INK="#F2F2F0"; MUT="#9A9DA3"; RULE="#3A3C41"; WH="#F2F2F0"; GY="#8F9297"
plt.rcParams.update({"font.family":"DejaVu Sans","text.color":INK,"axes.edgecolor":RULE,"axes.labelcolor":MUT,"xtick.color":MUT,"ytick.color":MUT,"axes.facecolor":P,"figure.facecolor":G,"savefig.facecolor":G})
fig, axs = plt.subplots(1, 3, figsize=(15, 5.2), dpi=150); x = range(len(CATS)); w = 0.38
for ax, key, title, f in ((axs[0], "dec", "Decode tok/s per category (median, c1)", lambda v: f"{v:.0f}"), (axs[1], "ttft", "Time to first token per category (median, c1)", lambda v: f"{v:.1f}"), (axs[2], "auto", "Auto score per category (thinking off)", lambda v: f"{v*100:.0f}")):
    vn = [r[f"{key}_nvfp4"] or 0 for r in rows]; ve = [r[f"{key}_exl3"] or 0 for r in rows]
    ax.bar([i - w/2 for i in x], vn, w, color=GY, label="NVFP4"); ax.bar([i + w/2 for i in x], ve, w, color=WH, label="EXL3")
    for i, (a_, b_) in enumerate(zip(vn, ve)):
        if a_: ax.text(i - w/2, a_, f(a_), ha="center", va="bottom", fontsize=7, color=INK)
        if b_: ax.text(i + w/2, b_, f(b_), ha="center", va="bottom", fontsize=7, color=INK)
    ax.set_xticks(list(x)); ax.set_xticklabels(CATS, rotation=30, ha="right", fontsize=8); ax.set_title(title, fontsize=10, loc="left", fontweight="bold", color=INK)
    ax.grid(axis="y", color=RULE, lw=0.6); ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    if key == "auto": ax.set_ylim(0, 1.15)
fig.text(0.01, 0.01, "2026-09-01 · 40 real prompts, identical to both lanes · streaming, temp 0 · isolated · @tonyd2wild", fontsize=8, color=MUT)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig("results/chart_categories.png"); print("-> results/chart_categories.png")
