#!/usr/bin/env python3
"""bench_prefill_len.py <base_url> <served_model> <lane> [--sizes 8000,16000,32000,64000,128000,250000] [--reps 3]

Prefill throughput vs prompt length. For each target length builds a prompt of repeated technical prose (~4 chars per
token; the server's usage.prompt_tokens is what gets recorded), asks for an 8-token answer, non-stream, thinking off,
temperature 0, and reports prefill tok/s = prompt_tokens / wall (wall ~= TTFT). The first request at each size is a NEW prompt (cold = real prefill
compute); the remaining reps repeat the identical prompt and therefore hit the prefix cache (reported as 'warm' = cache replay, not prefill). Sequential, one request at a time.
Writes results/prefill_len_<lane>.json.
"""
import sys, json, time, statistics, argparse, urllib.request
ap = argparse.ArgumentParser(); ap.add_argument("base"); ap.add_argument("model"); ap.add_argument("lane")
ap.add_argument("--sizes", default="8000,16000,32000,64000,128000,250000"); ap.add_argument("--reps", type=int, default=3)
a = ap.parse_args(); URL = a.base.rstrip("/") + "/v1/chat/completions"
PARA = ("The DGX Spark pairs a Grace CPU with a Blackwell GPU on one package and shares 128 GB of unified memory between them, "
        "so a model's weights, its KV cache and the operating system's page cache all compete for the same pool. Tensor parallel "
        "serving across two Sparks moves activations over a ConnectX-7 link on every layer, which is why prefill and decode both "
        "care about the fabric as much as the silicon. ")
def prompt_for(n_tokens):
    reps = max(1, int(n_tokens * 4.0 / len(PARA)))
    return "Read the following text and reply with the single word OK.\n\n" + PARA * reps
def call(prompt):
    body = json.dumps({"model": a.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 8,
                       "stream": False, "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t = time.time(); r = json.load(urllib.request.urlopen(req, timeout=1800)); dt = time.time() - t
    return r.get("usage", {}).get("prompt_tokens", 0), dt
rows = []
for target in [int(s) for s in a.sizes.split(",")]:
    p = prompt_for(target); runs = []
    for i in range(a.reps):
        try: pt, dt = call(p)
        except Exception as e: print(f"  [{a.lane}] {target:>7}: request {i+1} failed: {str(e)[:120]}", flush=True); break
        runs.append((pt, dt)); print(f"  [{a.lane}] {pt:>7} tok  run {i+1}: {pt/dt:7.0f} tok/s  ({dt:6.1f}s)", flush=True)
    if not runs: rows.append({"target": target, "error": True}); continue
    rates = [pt / dt for pt, dt in runs]
    rows.append({"target": target, "prompt_tokens": runs[0][0], "cold_tok_s": round(rates[0]), "cold_s": round(runs[0][1], 1),
                 "warm_tok_s": (round(statistics.median(rates[1:])) if len(rates) > 1 else None), "warm_s": (round(statistics.median(d for _, d in runs[1:]), 1) if len(runs) > 1 else None),
                 "all_tok_s": [round(x) for x in rates]})
out = {"lane": a.lane, "model": a.model, "reps": a.reps, "rows": rows, "ts": time.strftime("%Y-%m-%d %H:%M")}
json.dump(out, open(f"results/prefill_len_{a.lane}.json", "w"), indent=1)
print(f"[{a.lane}] prefill vs length -> results/prefill_len_{a.lane}.json")
for r in rows:
    if not r.get("error"): print(f"    {r['prompt_tokens']:>7} tok: cold {r['cold_tok_s']} tok/s ({r['cold_s']}s)  warm {r['warm_tok_s']} tok/s ({r['warm_s']}s)")
