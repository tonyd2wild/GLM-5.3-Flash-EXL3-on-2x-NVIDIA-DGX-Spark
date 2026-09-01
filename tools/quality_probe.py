#!/usr/bin/env python3
"""quality_probe.py <base_url> <served_model> <outfile>

Fire the SAME hard prompt (code + a reasoning trap) at any OpenAI-compatible lane,
thinking OFF, temp 0, and save the answer. Run it against each quant, then diff the
outfiles — that is the actual EXL3-vs-NVFP4 question (quality per bit), not tok/s.

  python3 tools/quality_probe.py http://100.92.77.51:8000    GLM-5.3-Flash-EXL3 results/quality_exl3.txt
  python3 tools/quality_probe.py http://100.113.138.96:8000  glm-5.3-flash      results/quality_nvfp4.txt
  diff results/quality_exl3.txt results/quality_nvfp4.txt
"""
import sys, json, time, urllib.request

if len(sys.argv) != 4:
    sys.exit(__doc__)
base, model, out = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]

PROMPT = (
    "Two parts.\n"
    "1) Write a Python function top_k_frequent(nums, k) returning the k most frequent elements in "
    "O(n log k) time. Include a 2-3 sentence explanation of why it is O(n log k) and one edge case it handles.\n"
    "2) A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the "
    "ball cost? Show the algebra, then give the final answer on its own line as 'ANSWER: $X.XX'."
)

body = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": PROMPT}],
    "temperature": 0, "max_tokens": 700, "stream": False,
    "chat_template_kwargs": {"enable_thinking": False},
}).encode()
req = urllib.request.Request(base + "/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"})
t = time.time()
r = json.load(urllib.request.urlopen(req, timeout=180))
dt = time.time() - t
m = r["choices"][0]["message"]
txt = m.get("content") or ""
rc = m.get("reasoning_content") or ""
u = r.get("usage", {})
with open(out, "w") as f:
    f.write(txt)
print(f"{model}: completion_tokens={u.get('completion_tokens')} wall={dt:.1f}s "
      f"content_chars={len(txt)} reasoning_chars={len(rc)} -> {out}")
print("--- answer tail ---")
print(txt[-400:])
