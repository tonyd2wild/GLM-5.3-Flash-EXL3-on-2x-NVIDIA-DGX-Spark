#!/usr/bin/env python3
"""bench_detailed.py <base_url> <served_model> <label> [--c1 5] [--c6 3] [--prefill 3]

Detailed, isolated throughput bench for one lane. Non-stream, temp 0, thinking OFF
(2Wild house rule: throughput = median tokens/sec, non-stream).

  warm   : 2x c1 + 1x c6 (lazy per-shape JIT compiles on first use — never bench cold)
  c1     : N runs, ~300-token gen  -> median / min / max tok/s
  c6     : M rounds of 6 concurrent -> aggregate tok/s (sum tokens / round wall) and
           per-stream tok/s (each request's tokens / its own wall), medians across rounds
  prefill: K runs, ~1.5K-token prompt, 8-token gen -> prompt_tokens / wall (median), wall ≈ TTFT

Isolate the lane first (point the relay elsewhere) and check the head's access log afterwards
so nothing but this bench hit it. Prints a table and one JSON line for BENCH.md.
"""
import sys, json, time, statistics, argparse, urllib.request, concurrent.futures

ap = argparse.ArgumentParser()
ap.add_argument("base"); ap.add_argument("model"); ap.add_argument("label")
ap.add_argument("--c1", type=int, default=5); ap.add_argument("--c6", type=int, default=3)
ap.add_argument("--prefill", type=int, default=3)
a = ap.parse_args()
URL = a.base.rstrip("/") + "/v1/chat/completions"

GEN = "List the numbers from 1 to 300 separated by commas. Output only the numbers, nothing else, no commentary."
LONG = ("Summarize the following in one sentence.\n\n" +
        ("The DGX Spark is a compact AI workstation built on the GB10 superchip with unified memory. " * 80))

def call(prompt, max_tokens):
    body = json.dumps({"model": a.model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0, "max_tokens": max_tokens, "stream": False,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t = time.time(); r = json.load(urllib.request.urlopen(req, timeout=600)); dt = time.time() - t
    u = r.get("usage", {})
    return u.get("completion_tokens", 0), u.get("prompt_tokens", 0), dt

def c1_run():
    ct, _, dt = call(GEN, 320); return ct / dt if dt else 0.0

def c6_round():
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        res = [f.result() for f in [ex.submit(call, GEN, 320) for _ in range(6)]]
    wall = time.time() - t0
    agg = sum(r[0] for r in res) / wall if wall else 0.0
    per = statistics.median([r[0] / r[2] for r in res if r[2]])
    return agg, per

def prefill_run():
    ct, pt, dt = call(LONG, 8); return (pt / dt if dt else 0.0), dt

print(f"[{a.label}] warm-up: 2x c1 + 1x c6 ...", flush=True)
for _ in range(2): c1_run()
c6_round()

c1 = [c1_run() for _ in range(a.c1)]
c6 = [c6_round() for _ in range(a.c6)]
pf = [prefill_run() for _ in range(a.prefill)]

c1_med, c1_min, c1_max = statistics.median(c1), min(c1), max(c1)
c6_agg_med = statistics.median([x[0] for x in c6]); c6_agg_min = min(x[0] for x in c6); c6_agg_max = max(x[0] for x in c6)
c6_per_med = statistics.median([x[1] for x in c6])
pf_med = statistics.median([x[0] for x in pf]); ttft_med = statistics.median([x[1] for x in pf])

print(f"\n=== {a.label} ({a.model} @ {a.base}) ===")
print(f"  c1  single-stream tok/s : median {c1_med:6.1f}   (min {c1_min:.1f} / max {c1_max:.1f}, n={a.c1})")
print(f"  c6  aggregate tok/s     : median {c6_agg_med:6.1f}   (min {c6_agg_min:.1f} / max {c6_agg_max:.1f}, n={a.c6})")
print(f"  c6  per-stream tok/s    : median {c6_per_med:6.1f}")
print(f"  prefill tok/s (~1.5K)   : median {pf_med:6.0f}     TTFT≈ {ttft_med:.2f}s  (n={a.prefill})")
print("JSON " + json.dumps({"label": a.label, "model": a.model, "c1_med": round(c1_med, 1), "c1_min": round(c1_min, 1),
      "c1_max": round(c1_max, 1), "c6_agg_med": round(c6_agg_med, 1), "c6_agg_min": round(c6_agg_min, 1),
      "c6_agg_max": round(c6_agg_max, 1), "c6_per_med": round(c6_per_med, 1), "prefill_med": round(pf_med),
      "ttft_med": round(ttft_med, 2)}))
