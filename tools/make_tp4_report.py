#!/usr/bin/env python3
"""make_tp4_report.py -> results/tp4_vs_tp2.md, results/tp4_vs_tp2.json, results/chart_tp4.png

NVFP4 TP4 (all four Sparks, CUDA graphs) against the two TP2 lanes measured earlier the same night, same tools, same
prompts, same isolation. Reads results/{sweep,detailed,ttft_fresh,prefill_len,categories_*,agent_loop_*,
quality_battery_*,power_load_*}_<lane> for lanes nvfp4tp4, nvfp4, exl3 and results/power_tp4_<node>.csv.
"""
import json, os, statistics, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
def J(p): return json.load(open(p)) if os.path.exists(p) else None
L = [("nvfp4tp4", "NVFP4 TP4"), ("nvfp4", "NVFP4 TP2"), ("exl3", "EXL3 TP2")]
S = {l: J(f"results/sweep_{l}.json") for l, _ in L}; D = {l: J(f"results/detailed_{l}.json") or {} for l, _ in L}
T = {l: J(f"results/ttft_fresh_{l}.json") for l, _ in L}; PL = {l: J(f"results/prefill_len_{l}.json") for l, _ in L}
C1 = {l: J(f"results/categories_{l}_off_c1.json") for l, _ in L}; C4 = {l: J(f"results/categories_{l}_off_c4.json") for l, _ in L}
ON = {l: J(f"results/categories_{l}_on_c1.json") for l, _ in L}
AG = {(l, t): J(f"results/agent_loop_{l}_{t}.json") for l, _ in L for t in ("short", "long")}
QB = {(l, m): J(f"results/quality_battery_{l}_{m}.json") for l, _ in L for m in ("off", "on")}
PW = {l: J(f"results/power_load_{l}.json") for l, _ in L}; BOOT = J("results/boot.json") or {}
def watts(path):
    if not os.path.exists(path): return None
    v = []
    for line in open(path):
        try: v.append(float(line.split(",")[0].replace("W", "").strip()))
        except ValueError: pass
    v = v[8:66] if len(v) >= 66 else v; return round(sum(v) / len(v), 1) if v else None
NODEW = {"nvfp4tp4": [watts(f"results/power_tp4_{n}.csv") for n in ("reddie", "spark4", "asusi", "bluey")],
         "nvfp4": [watts(f"results/power_{n}.csv") for n in ("reddie", "spark4")], "exl3": [watts(f"results/power_{n}.csv") for n in ("bluey", "asusi")]}
def tpj(l):
    w = NODEW[l]; p = PW[l]; return round(p["tok_s"] / sum(w), 2) if (p and w and all(x is not None for x in w)) else None
def row(l, c, k):
    s = S[l]; return next((r[k] for r in s["rows"] if r["c"] == c), None) if s else None
def fr(l, c): t = T[l]; return next((r["ttft_med_s"] for r in t["rows"] if r["c"] == c), None) if t else None
def f(v, nd=1, suf=""): return "—" if v is None else (f"{v:,.{nd}f}{suf}" if isinstance(v, (int, float)) else f"{v}{suf}")
def pct(v): return "—" if v is None else f"{v*100:.0f}%"
def cat(d, l, c, k): x = d.get(l); return x["summary"].get(c, {}).get(k) if x else None
def det(l):
    runs = [p for p in [f"results/categories_{l}_off_c1.json", f"results/categories_{l}_off_c1_run2.json", f"results/categories_{l}_off_c1_run3.json"] if os.path.exists(p)]
    if len(runs) < 2: return None
    R = [{i["id"]: i for i in json.load(open(p))["items"]} for p in runs]; ids = [k for k in R[0] if all(k in r for r in R)]
    ident = sum(all(r[k]["output"] == R[0][k]["output"] for r in R[1:]) for k in ids)
    scores = [round(sum(i["score"] for i in r.values() if i["score"] is not None) / max(1, sum(i["score"] is not None for i in r.values())), 3) for r in R]
    return {"runs": len(runs), "identical": ident, "n": len(ids), "scores": scores}
CATS = ["coding", "reasoning", "json", "html", "prose", "narrative", "summary", "format"]
def gain(a, b, higher=True):
    if a is None or b is None or not b: return "—"
    g = (a - b) / b * 100; return f"{'+' if g >= 0 else ''}{g:.0f}%" + ("" if higher else " (lower is better)")
md = ["## NVFP4 TP4 (4 Sparks, CUDA graphs) vs the TP2 lanes", "",
      "Same night, same tools, same prompts, same isolation. TP4 = all four Sparks in one tensor-parallel group with CUDA graphs on (the validated 08-31 recipe), RedHat NVFP4 base weights, 1M context. The TP2 lanes are the two-node pairs benched earlier: NVFP4 TP2 (Reddie + Spark4, eager) and EXL3 TP2 (Bluey + Asusi, eager). The TP4 lane uses all four boxes, so per-box it is half a lane; read the per-box column for what the hardware is doing.", "",
      "| metric | NVFP4 TP4 | NVFP4 TP2 | EXL3 TP2 | TP4 vs NVFP4 TP2 |", "|---|---|---|---|---|"]
rows = [("c1 single-stream tok/s (sweep)", [row(l, 1, "agg_tok_s") for l, _ in L], True),
        ("c1 single-stream tok/s (detailed, n=5)", [D[l].get("c1_med") for l, _ in L], True),
        ("c6 aggregate tok/s", [row(l, 6, "agg_tok_s") for l, _ in L], True),
        ("c6 per-stream tok/s", [row(l, 6, "per_stream_tok_s") for l, _ in L], True),
        ("peak aggregate tok/s", [(max(r["agg_tok_s"] for r in S[l]["rows"]) if S[l] else None) for l, _ in L], True),
        ("TTFT fresh 1.6K prompt, c1 (s)", [fr(l, 1) for l, _ in L], False), ("TTFT fresh, c6 (s)", [fr(l, 6) for l, _ in L], False),
        ("prefill fresh 1.6K tok/s", [(T[l]["rows"][0]["prefill_tok_s"] if T[l] else None) for l, _ in L], True),
        ("cold prefill at ~211K tok/s", [(PL[l]["rows"][-1]["cold_tok_s"] if PL[l] and not PL[l]["rows"][-1].get("error") else None) for l, _ in L], True),
        ("wall-to-wall c1 / c6 (s)", [f"{row(l,1,'w2w_med_s')} / {row(l,6,'w2w_med_s')}" if S[l] else None for l, _ in L], None),
        ("real prompts auto score, thinking off", [(C1[l]["overall"]["auto_score"] if C1[l] else None) for l, _ in L], True),
        ("real prompts median decode tok/s", [(C1[l]["overall"]["decode_med_tok_s"] if C1[l] else None) for l, _ in L], True),
        ("mixed c4 aggregate tok/s / TTFT s", [f"{C4[l]['overall']['agg_tok_s_med']} / {C4[l]['overall']['ttft_med_s']}" if C4[l] else None for l, _ in L], None),
        ("thinking on auto score", [(ON[l]["overall"]["auto_score"] if ON[l] and ON[l]["n"] >= 40 else None) for l, _ in L], True),
        ("agent loop 30K doc: TTFT med s / total s", [f"{AG[(l,'long')]['ttft_med_s']} / {AG[(l,'long')]['total_s']}" if AG[(l, "long")] else None for l, _ in L], None),
        ("12-item battery off / on", [f"{QB[(l,'off')]['correct']}/12 / {QB[(l,'on')]['correct']}/12" if QB[(l, "off")] and QB[(l, "on")] else None for l, _ in L], None),
        ("load throughput tok/s (c4 counting, 60 s)", [(PW[l]["tok_s"] if PW[l] else None) for l, _ in L], True),
        ("lane GPU power W (all nodes)", [(round(sum(NODEW[l]), 1) if NODEW[l] and all(x is not None for x in NODEW[l]) else None) for l, _ in L], False),
        ("tokens per joule", [tpj(l) for l, _ in L], True),
        ("boot launch → healthy (min)", [(BOOT.get(l, {}).get("min")) for l, _ in L], False)]
out_rows = []
for name, vals, higher in rows:
    a, b = vals[0], vals[1]
    if higher is None or isinstance(a, str) or isinstance(b, str): g = ""
    elif name.startswith("real prompts auto") or name.startswith("thinking on"): g = gain(a, b, True) if (a is not None and b is not None) else "—"
    else: g = gain(a, b, higher)
    cells = [pct(v) if (name.startswith("real prompts auto") or name.startswith("thinking on")) and isinstance(v, float) else f(v) for v in vals]
    md.append(f"| {name} | {cells[0]} | {cells[1]} | {cells[2]} | {g} |"); out_rows.append({"metric": name, "tp4": a, "tp2": b, "exl3": vals[2], "gain": g})
md += ["", "### Per category, thinking off (auto score / decode tok/s / TTFT s)", "", "| category | NVFP4 TP4 | NVFP4 TP2 | EXL3 TP2 |", "|---|---|---|---|"]
for c in CATS:
    md.append("| " + c + " | " + " | ".join(f"{pct(cat(C1,l,c,'auto_score'))} / {f(cat(C1,l,c,'decode_med_tok_s'))} / {f(cat(C1,l,c,'ttft_med_s'),2)}" for l, _ in L) + " |")
d = {l: det(l) for l, _ in L}
if any(d.values()):
    md += ["", "### Determinism (3 runs at temp 0)", "", "| lane | identical outputs | auto score per run |", "|---|---|---|"]
    for l, n in L:
        if d[l]: md.append(f"| {n} | {d[l]['identical']}/{d[l]['n']} | {' / '.join(pct(x) for x in d[l]['scores'])} |")
if PL["nvfp4tp4"]:
    md += ["", "### Cold prefill vs length, tok/s", "", "| prompt tokens | NVFP4 TP4 | NVFP4 TP2 | EXL3 TP2 |", "|---|---|---|---|"]
    for i, r in enumerate(PL["nvfp4tp4"]["rows"]):
        if r.get("error"): continue
        o = [PL[l]["rows"][i] if PL[l] and i < len(PL[l]["rows"]) else None for l in ("nvfp4", "exl3")]
        md.append(f"| {r['prompt_tokens']:,} | {r['cold_tok_s']:,} | {(o[0]['cold_tok_s'] if o[0] and not o[0].get('error') else '—')} | {(o[1]['cold_tok_s'] if o[1] and not o[1].get('error') else '—')} |")
open("results/tp4_vs_tp2.md", "w").write("\n".join(md) + "\n"); json.dump({"rows": out_rows, "determinism": d, "node_watts": NODEW}, open("results/tp4_vs_tp2.json", "w"), indent=1)
print("-> results/tp4_vs_tp2.md")
# chart: aggregate + fresh TTFT for the three lanes
G="#1B1C1F"; P="#232428"; INK="#F2F2F0"; MUT="#9A9DA3"; RULE="#3A3C41"
plt.rcParams.update({"font.family":"DejaVu Sans","text.color":INK,"axes.edgecolor":RULE,"axes.labelcolor":MUT,"xtick.color":MUT,"ytick.color":MUT,"axes.facecolor":P,"figure.facecolor":G,"savefig.facecolor":G})
fig, axs = plt.subplots(1, 3, figsize=(15, 5), dpi=150); cs = [1, 2, 3, 4, 5, 6]
styles = {"nvfp4tp4": ("#F2F2F0", "-"), "nvfp4": ("#8F9297", "-"), "exl3": ("#8F9297", "--")}
for ax, key, src, title in ((axs[0], "agg_tok_s", "sweep", "Aggregate tok/s vs concurrency"), (axs[1], "per_stream_tok_s", "sweep", "Per-stream tok/s vs concurrency"), (axs[2], "ttft", "fresh", "TTFT, fresh 1.6K prompts (s)")):
    for l, n in L:
        ys = [row(l, c, key) for c in cs] if src == "sweep" else [fr(l, c) for c in cs]
        if any(y is None for y in ys): continue
        col, ls = styles[l]; ax.plot(cs, ys, color=col, ls=ls, lw=2.2, marker="o", ms=5, label=n)
        for c, y in zip(cs, ys): ax.annotate(f"{y:.0f}" if key != "ttft" else f"{y:.1f}", (c, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=7, color=INK)
    ax.set_xticks(cs); ax.set_xticklabels([f"c{c}" for c in cs]); ax.set_title(title, fontsize=10, loc="left", fontweight="bold", color=INK)
    ax.grid(axis="y", color=RULE, lw=0.6); ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, fontsize=8, labelcolor=INK)
fig.text(0.01, 0.01, "2026-09-01/02 · NVFP4 TP4 (4 Sparks, CUDA graphs) vs NVFP4 TP2 and EXL3 TP2 (2 Sparks each, eager) · temp 0 · isolated · @tonyd2wild", fontsize=8, color=MUT)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig("results/chart_tp4.png"); print("-> results/chart_tp4.png")
