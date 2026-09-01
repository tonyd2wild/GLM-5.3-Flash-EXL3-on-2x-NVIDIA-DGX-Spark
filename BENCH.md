# Bench — EXL3 vs NVFP4 (GLM-5.3-Flash, same 4-Spark cluster)

> **⚠️ SUPERSEDED — DO NOT CITE (2026-09-01 21:00 ET).** All NVFP4 numbers on this page were taken while
> Reddie and Spark4 were pinned at ~611–728 MHz SM clock post-reboot (EXL3's nodes ran ~2,500 MHz). The
> NVFP4 config was correct (DFlash2 k=7, 92–100 % draft acceptance); the silicon was capped. Both lanes
> are being re-tested from scratch after a full restart; this page will be regenerated from those runs.

Both lanes are the *same* base model (GLM-5.3-Flash), same fabric, same DFlash2 drafter,
so this is a clean quant-vs-quant comparison.

- **NVFP4 lane:** Reddie head, TP2 (Reddie + Spark4), marlin, fp8 KV, served `glm-5.3-flash` :8000.
- **EXL3 lane:** Bluey head, TP2 (Bluey + Asusi), `--quantization exl3`, fp8 KV, served `GLM-5.3-Flash-EXL3` :8000.

## Method
Throughput = **median tokens/sec, non-streaming** (2Wild house rule — throughput, not "decode").
Warmed. Same prompts on both. Report single-stream and aggregate @ concurrency 4.

## Speed — isolated, parallel, detailed (2026-09-01, 20:18–20:23 ET)

Both lanes benched **simultaneously** (independent TP2 pairs, no shared GPUs) from the Mac over tailnet
with `tools/bench_detailed.py`. **Isolation:** spark-flash relay parked on the 3090 27B, latency monitor
paused; each head's access log shows chat POSTs from the bench client only — NVFP4 48, EXL3 43, exactly
the request counts issued. Non-stream, temp 0, thinking OFF, identical prompts, ~300-token gens.
Warm-up 2×c1 + 1×c6 before measuring (both engines JIT lazily per request shape).

| Metric | NVFP4 (Reddie+Spark4) | EXL3 (Bluey+Asusi) | winner |
|--------|-----------------------|--------------------|--------|
| c1 single-stream tok/s — median (min / max), n=5 | 35.9 (27.6 / 39.0) | **61.1** (60.9 / 61.5) | EXL3 1.7× |
| c6 aggregate tok/s — median (min / max), n=3 | 66.2 (64.3 / 83.2) | **122.0** (120.6 / 123.8) | EXL3 1.8× |
| c6 per-stream tok/s — median | 17.6 | **34.9** | EXL3 2.0× |
| prefill tok/s (~1.5K-token prompt) — median, n=3 | 564 | **3,233** | EXL3 5.7× |
| TTFT ≈ prefill wall (s) — median | 2.88 | **0.50** | EXL3 |
| run-to-run spread on c1 | ±16% | **±0.5%** | EXL3 |

Earlier same-day c4 runs (before isolation): EXL3 60.4 / 140.4 → 59.9 / 152.2; NVFP4 33.8 / 28.5 → 36.2 / 55.5.

**Caveats.** NVFP4 was still emitting `TileLang/Triton JIT compilation during inference` warnings during
and after the bench — it compiles lazily per request shape, so its figures may sit below fully-warm; its
own repo quotes 46.9 tok/s single (code, warm) and 47.7 c6 aggregate. Even against those, EXL3 is +30% on
c1 and ~2.5× on c6 aggregate. NVFP4's worker loaded its weights over NFS here (Spark4 had no local copy of
the RedHatAI base) — that lengthens boot (~40 min first boot), not decode. **Never bench a cold lane:**
EXL3's first-ever completion was ~30 tok/s and its first long prefill 136 tok/s; both settle after one
warm request. NVFP4's cold-first-request cost was 5.2 s → 3.3 s within three calls.

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
