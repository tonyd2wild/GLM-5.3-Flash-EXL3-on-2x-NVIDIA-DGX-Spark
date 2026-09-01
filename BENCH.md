# Bench — EXL3 vs NVFP4 (GLM-5.3-Flash, same 4-Spark cluster)

Both lanes are the *same* base model (GLM-5.3-Flash), same fabric, same DFlash2 drafter,
so this is a clean quant-vs-quant comparison.

- **NVFP4 lane:** Reddie head, TP2 (Reddie + Spark4), marlin, fp8 KV, served `glm-5.3-flash` :8000.
- **EXL3 lane:** Bluey head, TP2 (Bluey + Asusi), `--quantization exl3`, fp8 KV, served `GLM-5.3-Flash-EXL3` :8000.

## Method
Throughput = **median tokens/sec, non-streaming** (2Wild house rule — throughput, not "decode").
Warmed. Same prompts on both. Report single-stream and aggregate @ concurrency 4.

## Speed (TODO — fill after EXL3 serves)

| Metric | NVFP4 | EXL3 | winner |
|--------|-------|------|--------|
| single-stream tok/s | | | |
| agg tok/s @ c4 | | | |
| TTFT (9K prompt) | | | |
| prefill tok/s | | | |

## Quality (the point of EXL3)
Run the same hard prompts on both, diff the answers. Focus areas:
- multi-file code edit / refactor correctness
- multi-step math / logic
- tool-calling: does it pick the right tool + valid args
- long-context recall (needle deep in 200K+)

Published KLD figures (for reference, not ours): EXL3/TR3 4bpw ~0.025 (ties FP8), NVFP4 ~0.060.

## Notes
- (fill in surprises here)
