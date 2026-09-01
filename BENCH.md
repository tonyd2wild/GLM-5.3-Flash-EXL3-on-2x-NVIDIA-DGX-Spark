# Bench — EXL3 vs NVFP4 (GLM-5.3-Flash, same 4-Spark cluster)

Both lanes are the *same* base model (GLM-5.3-Flash), same fabric, same DFlash2 drafter,
so this is a clean quant-vs-quant comparison.

- **NVFP4 lane:** Reddie head, TP2 (Reddie + Spark4), marlin, fp8 KV, served `glm-5.3-flash` :8000.
- **EXL3 lane:** Bluey head, TP2 (Bluey + Asusi), `--quantization exl3`, fp8 KV, served `GLM-5.3-Flash-EXL3` :8000.

## Method
Throughput = **median tokens/sec, non-streaming** (2Wild house rule — throughput, not "decode").
Warmed. Same prompts on both. Report single-stream and aggregate @ concurrency 4.

## Speed (measured 2026-09-01 from the Mac over tailnet; warmed, temp 0, thinking OFF, 256-tok gens)

| Metric | NVFP4 (Reddie+Spark4) | EXL3 (Bluey+Asusi) | winner |
|--------|-----------------------|--------------------|--------|
| single-stream tok/s (median of 3) | TBD — lane rebooting | **60.4** (57.7 on run 1) | |
| aggregate tok/s @ c4 | TBD | **140.4** (140.7 on run 1) | |
| prefill tok/s (~1.5K-token prompt) | TBD | **3,233** warm (cold-JIT first prefill: 136) | |
| TTFT / prefill wall (s) | TBD | **0.48** | |

Two EXL3 runs ~10 min apart agree within 5% → stable. **Do not bench a cold lane:** the very first
completion after boot was ~30 tok/s single-stream (cold trellis JIT + thinking on) and the first long
prefill was 136 tok/s; both settle after one warm request.

## Quality (the point of EXL3)
Same prompt to both lanes, thinking OFF, temp 0. Probe 1 (2026-09-01):
`top_k_frequent(nums, k)` in O(n log k) + a 2-3 sentence complexity explanation + one edge case, AND
the bat-and-ball trap ($1.10 total, bat costs $1.00 more → ball = $0.05).

- **EXL3:** correct on both parts. Clean algebra with an explicit check line, `ANSWER: $0.05`, handles
  empty input / `k ≤ 0`. 506 tokens, 13.9 s. Saved as `quality_exl3.txt`.
- **NVFP4:** TBD (identical prompt once the lane is back), saved as `quality_nvfp4.txt`, then diff.
- `chat_template_kwargs: {"enable_thinking": false}` IS honored by the EXL3 lane (`reasoning_content` empty).

Further focus areas still to probe: multi-file refactor correctness, tool-calling arg validity,
long-context recall (needle deep in 200K+).

Published KLD figures (for reference, not ours): EXL3/TR3 4bpw ~0.025 (ties FP8), NVFP4 ~0.060.

## Notes
- (fill in surprises here)
