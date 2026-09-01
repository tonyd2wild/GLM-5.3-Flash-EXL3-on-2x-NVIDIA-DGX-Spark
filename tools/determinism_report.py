#!/usr/bin/env python3
"""determinism_report.py  -> results/determinism.json, prints a summary

Compares repeated runs of the 40-prompt category benchmark at temperature 0 on each lane:
results/categories_<lane>_off_c1.json (run 1), _run2.json, _run3.json. For every prompt it counts whether the final
answer text was byte-identical across runs, whether the auto score changed, and the token-count spread. Temperature 0
is not batch-invariant on either engine; this puts a number on it.
"""
import json, os, statistics
L = ("nvfp4", "exl3"); out = {}
for l in L:
    runs = [p for p in [f"results/categories_{l}_off_c1.json", f"results/categories_{l}_off_c1_run2.json", f"results/categories_{l}_off_c1_run3.json"] if os.path.exists(p)]
    if len(runs) < 2: print(f"[{l}] fewer than 2 runs, skipping"); continue
    R = [{i["id"]: i for i in json.load(open(p))["items"]} for p in runs]
    ids = [k for k in R[0] if all(k in r for r in R)]
    ident = sum(all(r[k]["output"] == R[0][k]["output"] for r in R[1:]) for k in ids)
    score_flip = [k for k in ids if len({round(r[k]["score"], 3) if r[k]["score"] is not None else None for r in R}) > 1]
    tok_spread = [max(r[k]["completion_tokens"] for r in R) - min(r[k]["completion_tokens"] for r in R) for k in ids]
    scores = [round(sum(i["score"] for i in r.values() if i["score"] is not None) / max(1, sum(i["score"] is not None for i in r.values())), 3) for r in R]
    by_cat = {}
    for k in ids:
        c = R[0][k]["category"]; b = by_cat.setdefault(c, {"n": 0, "identical": 0, "score_flips": 0})
        b["n"] += 1; b["identical"] += all(r[k]["output"] == R[0][k]["output"] for r in R[1:]); b["score_flips"] += (k in score_flip)
    out[l] = {"runs": len(runs), "n": len(ids), "identical_outputs": ident, "identical_pct": round(100 * ident / len(ids)), "score_flips": len(score_flip),
              "score_flip_ids": score_flip, "auto_score_per_run": scores, "token_spread_median": int(statistics.median(tok_spread)), "token_spread_max": max(tok_spread), "by_category": by_cat}
    print(f"[{l}] {len(runs)} runs: {ident}/{len(ids)} outputs byte-identical ({out[l]['identical_pct']}%), {len(score_flip)} score flips {score_flip}, auto score per run {scores}, token spread median {out[l]['token_spread_median']} max {max(tok_spread)}")
    for c, b in by_cat.items(): print(f"    {c:10} identical {b['identical']}/{b['n']}  score flips {b['score_flips']}")
json.dump(out, open("results/determinism.json", "w"), indent=1); print("-> results/determinism.json")
