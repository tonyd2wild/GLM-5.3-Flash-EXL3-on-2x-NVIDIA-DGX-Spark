#!/usr/bin/env python3
# EXL3 (Bluey :8000) vs NVFP4 (Reddie :8000) — throughput bench. Run on the fabric.
import urllib.request, json, time, concurrent.futures

ENDPOINTS = {
    "EXL3 (Bluey)":  ("http://100.92.77.51:8000/v1/chat/completions", "GLM-5.3-Flash-EXL3"),
    "NVFP4 (Reddie)": ("http://100.113.138.96:8000/v1/chat/completions", "glm-5.3-flash"),
}
GEN_PROMPT = "List the numbers from 1 to 240 separated by commas. Output only the numbers, nothing else, no commentary."
# ~1.8k-token prompt for a prefill/TTFT proxy
LONG_PROMPT = ("Summarize the following in one sentence.\n\n" + ("The DGX Spark is a compact AI workstation built on the GB10 superchip. " * 90))

def call(url, model, prompt, max_tokens, think=False):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0, "max_tokens": max_tokens, "stream": False,
        "chat_template_kwargs": {"enable_thinking": think},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    t = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=180))
    dt = time.time() - t
    u = r.get("usage", {})
    return u.get("completion_tokens", 0), u.get("prompt_tokens", 0), dt

print(f"{'lane':<16} {'single tok/s':>13} {'c4 agg tok/s':>13} {'prefill tok/s':>14} {'ttft/prefill s':>15}")
print("-" * 76)
for name, (url, model) in ENDPOINTS.items():
    try:
        call(url, model, "hi", 8)  # warmup
        # single-stream: median of 3 x 240-token gens
        singles = []
        for _ in range(3):
            ct, _, dt = call(url, model, GEN_PROMPT, 256)
            if dt > 0 and ct > 0: singles.append(ct / dt)
        singles.sort()
        single = singles[len(singles)//2] if singles else 0
        # concurrent c4 aggregate
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futs = [ex.submit(call, url, model, GEN_PROMPT, 256) for _ in range(4)]
            res = [f.result() for f in futs]
        wall = time.time() - t0
        agg = sum(x[0] for x in res) / wall if wall > 0 else 0
        # prefill proxy: long prompt, 8 tokens out; total time ~ prefill + tiny decode
        pc, pp, pdt = call(url, model, LONG_PROMPT, 8)
        prefill_rate = pp / pdt if pdt > 0 else 0
        print(f"{name:<16} {single:>13.1f} {agg:>13.1f} {prefill_rate:>14.0f} {pdt:>15.2f}")
    except Exception as e:
        print(f"{name:<16}  ERROR: {e}")
