#!/usr/bin/env python3
"""bench_prefill.py <base_url> <served_model> <lane>   -> results/prefill_<lane>.json

Warm prefill / TTFT measurement. Both engines JIT-compile the long-prompt prefill path on its FIRST use after
boot (EXL3's first 1.5K prefill: 136-430 tok/s cold vs ~3,200 warm), so a single sample right after boot is not
the lane's prefill speed. Fires N (default 6) identical ~1.5K-token prompts with an 8-token answer, sequentially,
and reports the median of the LAST 3 (warm) plus the first (cold) for the record. prefill tok/s = prompt_tokens/wall;
wall ≈ TTFT.
"""
import sys, json, time, statistics, urllib.request
base, model, lane = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 6
LONG = ("Summarize the following in one sentence.\n\n" +
        ("The DGX Spark is a compact AI workstation built on the GB10 superchip with unified memory. " * 80))
def call():
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": LONG}], "temperature": 0,
                       "max_tokens": 8, "stream": False, "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
    t = time.time(); r = json.load(urllib.request.urlopen(req, timeout=300)); dt = time.time() - t
    return r.get("usage", {}).get("prompt_tokens", 0), dt
runs = [call() for _ in range(N)]
rates = [p / d for p, d in runs if d]; walls = [d for _, d in runs]
out = {"lane": lane, "model": model, "n": N, "prompt_tokens": runs[0][0],
       "first_prefill_tok_s": round(rates[0]), "first_ttft_s": round(walls[0], 2),
       "warm_prefill_tok_s": round(statistics.median(rates[-3:])), "warm_ttft_s": round(statistics.median(walls[-3:]), 2),
       "all_tok_s": [round(x) for x in rates]}
json.dump(out, open(f"results/prefill_{lane}.json", "w"), indent=1)
print(f"[{lane}] prefill ~{runs[0][0]} tok prompt: first {out['first_prefill_tok_s']} tok/s ({out['first_ttft_s']}s)  "
      f"warm(median last 3) {out['warm_prefill_tok_s']} tok/s ({out['warm_ttft_s']}s)  all: {out['all_tok_s']}")
