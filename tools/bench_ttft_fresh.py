#!/usr/bin/env python3
"""bench_ttft_fresh.py <base_url> <served_model> <lane> [--max-c 6] [--rounds 3] [--tokens 1600]

TTFT and prefill at c1..cN with FRESH prompts: every request carries different text of the same length, so no request
can hit the prefix cache (the earlier sweep repeated one prompt, which EXL3 served from cache). Two distinct warm-up
requests pay any per-shape JIT first (their times are recorded as `jit_first_s`). Non-stream, 8-token answer, thinking
off, temp 0; TTFT ~= wall. Writes results/ttft_fresh_<lane>.json.
"""
import sys, json, time, statistics, argparse, urllib.request, concurrent.futures, random
ap = argparse.ArgumentParser(); ap.add_argument("base"); ap.add_argument("model"); ap.add_argument("lane")
ap.add_argument("--max-c", type=int, default=6); ap.add_argument("--rounds", type=int, default=3); ap.add_argument("--tokens", type=int, default=1600)
a = ap.parse_args(); URL = a.base.rstrip("/") + "/v1/chat/completions"
WORDS = ("spark memory fabric tensor kernel cache latency decode prefill batch token weight shard rail switch clock thermal driver socket buffer "
         "queue stream layer expert router gate norm bias scale block page pool lease probe trace sample median spread round warm cold").split()
rng = random.Random(20260901); _n = [0]
def fresh_prompt():
    _n[0] += 1; rng2 = random.Random(_n[0] * 7919)
    body = " ".join(rng2.choice(WORDS) for _ in range(int(a.tokens * 0.95)))   # ~1 token per word, unique sequence every call
    return f"Document {_n[0]}: {body}\n\nReply with the single word OK."
def call(p):
    body = json.dumps({"model": a.model, "messages": [{"role": "user", "content": p}], "temperature": 0, "max_tokens": 8, "stream": False,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t = time.time(); r = json.load(urllib.request.urlopen(req, timeout=600)); dt = time.time() - t
    return r.get("usage", {}).get("prompt_tokens", 0), dt
jit = [call(fresh_prompt())[1] for _ in range(2)]
print(f"  [{a.lane}] warm-up (fresh prompts): {jit[0]:.2f}s, {jit[1]:.2f}s", flush=True)
rows = []
for c in range(1, a.max_c + 1):
    meds = []; pts = []
    for _ in range(a.rounds):
        ps = [fresh_prompt() for _ in range(c)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=c) as ex: res = list(ex.map(call, ps))
        meds.append(statistics.median(d for _, d in res)); pts.append(res[0][0])
    row = {"c": c, "ttft_med_s": round(statistics.median(meds), 2), "prompt_tokens": pts[0]}
    if c == 1: row["prefill_tok_s"] = round(pts[0] / statistics.median(meds))
    rows.append(row); print(f"  [{a.lane}] c{c}: TTFT median {row['ttft_med_s']}s ({pts[0]} tok)" + (f"  prefill {row['prefill_tok_s']} tok/s" if c == 1 else ""), flush=True)
out = {"lane": a.lane, "model": a.model, "tokens": a.tokens, "rounds": a.rounds, "jit_first_s": [round(x, 2) for x in jit], "rows": rows, "ts": time.strftime("%Y-%m-%d %H:%M")}
json.dump(out, open(f"results/ttft_fresh_{a.lane}.json", "w"), indent=1); print(f"[{a.lane}] -> results/ttft_fresh_{a.lane}.json")
