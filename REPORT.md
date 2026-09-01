# NVFP4 vs EXL3 for GLM-5.3-Flash on DGX Spark

*2Wild fleet report · 2026-09-01 · tonyd2wild (deploy + bench with Kai) · published page: https://claude.ai/code/artifact/bdcc64b1-44f0-49e7-b3dc-f189d5674f7a*

## TL;DR
The same 320B MoE, GLM-5.3-Flash, in two 4-bit quantizations, on two independent 2-node DGX Spark pairs, benched
**at the same time in the same state** (all four nodes restarted together, clocks verified at ~2,170–2,190 MHz under
decode load), isolated from every other consumer. Single-stream decode: NVFP4 64.3 tok/s vs EXL3 61.8 tok/s (NVFP4 +4%). Peak aggregate: NVFP4 138.6 tok/s vs EXL3 149.7 tok/s (EXL3 +8%) (peaks at c3 / c4).
Per-stream at c6: NVFP4 35.0 tok/s vs EXL3 35.8 tok/s (EXL3 +2%). Warm prefill: NVFP4 1225 tok/s vs EXL3 684 tok/s (NVFP4 +79%); TTFT NVFP4 1.29 s vs EXL3 2.31 s (NVFP4 lower by 44%). Wall-to-wall at c6: NVFP4 10.09 s vs EXL3 8.95 s (EXL3 lower by 11%). EXL3 serves 4× the
context with 4.7× the KV pool; boot to serve EXL3 13 min (local weights both nodes, warm trellis JIT cache) vs NVFP4 23 min (worker loads over NFS from head (Reddie page cache warm), TileLang cache partly warm); quality
probe tie. An earlier run showing EXL3 ahead on every line was discarded: NVFP4's nodes were
clock-capped after a reboot (611–728 MHz); with clocks equal the picture is the one above.

## Headline (isolated, both lanes benched simultaneously, 2026-09-01 17:34:23)
| | NVFP4 (Reddie + Spark4) | EXL3 (Bluey + Asusi) | EXL3 ÷ NVFP4 |
|---|---|---|---|
| c1 single-stream tok/s | 64.3 | 61.8 | 1.0× |
| peak aggregate tok/s (at c) | 138.6 (c3) | 149.7 (c4) | 1.1× |
| c6 aggregate tok/s | 136.3 | 125.2 | 0.9× |
| c6 per-stream tok/s | 35.0 | 35.8 | 1.0× |
| prefill tok/s (~1.5K prompt) (fresh prompts, different text per request, ~1,582 tokens, median of 3 rounds) | 1225 | 684 | 0.6× |
| TTFT, fresh 1.6K prompts, c1 / c6 | 1.29 s / 4.53 s | 2.31 s / 9.82 s | 0.6× / 0.5× lower |
| identical prompt repeated (prefix cache), TTFT c1 / c6 | 1.54 s / 4.6 s | 0.52 s / 1.02 s | cache, not prefill |
| cold prefill on a fresh 211,001-token prompt, tok/s | 2,763 | 1,752 | |
| 211,001-token context replayed (prefix cache) | 9.2 s | 0.8 s | |
| mixed load c4 (four real prompts in flight): aggregate tok/s / TTFT | 31.4 / 1.97 s | 43.4 / 0.66 s | |
| wall-to-wall c1 / c6 (300-tok answer) | 4.98 s / 10.09 s | 5.18 s / 8.95 s | 1.0× / 1.1× lower |
| c1 spread (detailed, n=5) | 62.8–64.7 (±1.5%) | 59.8–61.9 (±1.7%) | |
| max context | 262,144 | 1,048,576 | 4× |
| KV pool (tokens) | 295,230 | 1,396,551 | 4.7× |
| quality probe | correct | correct | tie |
| boot: launch → /health 200 | 23 min (worker loads over NFS from head (Reddie page cache warm), TileLang cache partly warm) | 13 min (local weights both nodes, warm trellis JIT cache) | |

## Sweep c1–c6 (3 rounds per level)
| c | NVFP4 agg | per-stream | wall-to-wall | TTFT (fresh) | EXL3 agg | per-stream | wall-to-wall | TTFT (fresh) |
|---|---|---|---|---|---|---|---|---|
| 1 | 64.3 | 64.3 | 4.98 s | 1.29 s | 61.8 | 61.8 | 5.18 s | 2.31 s |
| 2 | 111.1 | 55.5 | 5.76 s | 2.14 s | 92.5 | 46.5 | 6.88 s | 4.13 s |
| 3 | 138.6 | 47.0 | 6.81 s | 3.01 s | 120.2 | 41.2 | 7.76 s | 5.85 s |
| 4 | 111.2 | 48.5 | 6.61 s | 3.0 s | 149.7 | 37.4 | 8.55 s | 7.47 s |
| 5 | 131.3 | 47.0 | 6.81 s | 2.98 s | 116.9 | 36.2 | 8.85 s | 8.96 s |
| 6 | 136.3 | 35.0 | 10.09 s | 4.53 s | 125.2 | 35.8 | 8.95 s | 9.82 s |

## Hardware and topology
Four NVIDIA DGX Spark (GB10, sm_121a, 128 GB unified memory, ~121 GB usable) on a ConnectX-7 RoCE v2 fabric,
192.168.192.0/24, rail 0 (`enp1s0f0np0` / `rocep1s0f0`, GID 3). Reddie (.2) heads NVFP4 with Spark4 (.4);
Bluey (.1) heads EXL3 with Asusi (.3). Both lanes TP=2 across two nodes (vLLM mp executor, NCCL over RoCE);
they share nothing but the switch. Bench client: a Mac mini on the same tailnet.

**Clock state matters on GB10.** An earlier run was thrown out: after a reboot, Reddie and Spark4 came up pinned at
611–728 MHz SM clock under load (EXL3's nodes ran ~2,500) and NVFP4 measured 36 tok/s with a perfect 92–100 % draft
acceptance. All four were restarted together and verified under real decode load before this run: healthy GB10s here
settle at ~2,170–2,180 MHz at ~96 % utilization. Check `nvidia-smi --query-gpu=clocks.sm` under load after any
Spark reboot before trusting a throughput number.

## The two lanes
**NVFP4 (reference).** The published 2-Spark recipe run verbatim: weights `RedHatAI/GLM-5.3-Flash-NVFP4`; image
`ghcr.io/tonyd2wild/vllm-glm53-flash:sm121-v11-dflash2`; `--max-model-len 262144 --gpu-memory-utilization 0.85
--kv-cache-memory 3 GiB --max-num-seqs 6 --max-num-batched-tokens 8192 --block-size 2304 --moe-backend marlin
--kv-cache-dtype fp8_e4m3 --enforce-eager`; DFlash2 drafter k=7 (92–100 % draft acceptance on structured output);
`vm.swappiness=0`; worker first, head 25 s later.

**EXL3 (challenger).** Reederey87's GB10 kit (MiaAI-Lab's sibling as cross-reference) built for our fabric: weights
`brandonmusic/GLM-5.3-Flash-tr3-4bpw` (EXL3/TR3, 4 bpw, 120 shards, ~164 GiB, ~91 GiB resident per node);
exllamav3 compiled for `12.1a`; `--quantization exl3 --max-model-len 1000000 --gpu-memory-utilization 0.85
--kv-cache-memory-bytes 15414698763 --max-num-seqs 4 --max-num-batched-tokens 3584 --kv-cache-dtype fp8
--no-async-scheduling`; same DFlash2 drafter k=7. Both lanes: fp8 KV, thinking off, multimodal chat template,
native `image_url` (a red square came back "Red" on both).

## Method
**Isolation.** Relay parked on the 3090 27B, latency dashboard paused (it sends real probe completions), the three
Hermes supervisors that default to `glm-5.3-flash` moved to the 27B; after each run the head's access log shows chat
POSTs from the bench client only, with counts matching the requests issued (the supervisors share the client's IP,
so only counts prove it). This run: NVFP4 head 128 chat POSTs, all from the bench client; EXL3 head 129 from the bench client, and the only other traffic in the 30-minute log window was the kit's own post-serve warm-up burst of 15 requests at 17:16 ET, fifteen minutes before the tests began. **Simultaneity.** Both lanes benched in parallel; no shared GPUs, memory or NCCL group.
**Warm-up.** 2× c1 + 1× c6 before measuring; both engines JIT-compile per request shape — never bench a cold lane.
**Metrics.** Median tokens/s, non-streaming. c1–c6: 3 rounds of c concurrent ~300-token generations; aggregate =
Σ tokens / round wall; per-stream = each request's tokens / its wall; wall-to-wall = end-to-end latency (median).
TTFT at level c: c concurrent ~1.5K-token prompts with an 8-token answer. Detailed run: c1 ×5 for the spread.
Temperature 0, `stream false`, thinking off, identical prompts. Tools in `tools/`.

## Reading the curve
EXL3 scales to 149.7 tok/s at c4 and flattens — the kit's `--max-num-seqs 4` (a config cap, not the quant).
NVFP4 (`--max-num-seqs 6`) admits all six but pays per stream: 64.3 → 35.0 tok/s,
TTFT 1.29 → 4.53 s, wall-to-wall 4.98 → 10.09 s.

## Quality: does the quant change how smart it is?
**Probe** (top-k in O(n log k) + bat-and-ball, thinking off): EXL3 correct, NVFP4 correct.
**Battery**: 12 auto-graded items (3 math word problems, 3 logic, 2 code, leap-year rule, bat-and-ball, 2 strict-format),
identical for both lanes, temp 0, thinking off and thinking on (`tools/quality_battery.py`, full items + answers in `results/quality_battery_*.json`):

| accuracy | NVFP4 · off | EXL3 · off | NVFP4 · on | EXL3 · on |
|---|---|---|---|---|
| **all 12** | 11/12 (92%) | 11/12 (92%) | 12/12 (100%) | 12/12 (100%) |
| math | 3/3 | 3/3 | 3/3 | 3/3 |
| logic | 3/3 | 3/3 | 3/3 | 3/3 |
| code | 2/2 | 2/2 | 2/2 | 2/2 |
| knowledge | 1/1 | 1/1 | 1/1 | 1/1 |
| reasoning | 1/1 | 1/1 | 1/1 | 1/1 |
| format | 1/2 | 1/2 | 2/2 | 2/2 |
| avg reasoning trace, on (chars) | | | 341 | 333 |

Disagreements, thinking off:
- none — identical pass/fail on every item
Disagreements, thinking on:
- none — identical pass/fail on every item
Traces, thinking on (same item, both lanes):
**the clock-hands angle at 3:15**
NVFP4 (306 chars, right):
> At 3:15, the minute hand is at 15 minutes, which is at the 3 position (90 degrees from 12).
> The hour hand: at 3:00 it's at 90 degrees. In 15 minutes, it moves 15 × 0.5 = 7.5 degrees. So hour hand is at 97.5 degrees.
> Minute hand at 15 minutes: 15 × 6 = 90 degrees.
> Angle between: 97.5 - 90 = 7.5 degrees.

EXL3 (370 chars, right):
> At 3:15, the minute hand is at 15 minutes, which is at the 3 position (90 degrees from 12).
> The hour hand at 3:15 has moved past 3. At 3:00 it's at 90 degrees. Each minute, the hour hand moves 0.5 degrees. So at 3:15, hour hand is at 90 + 15 × 0.5 = 90 + 7.5 = 97.5 degrees.
> Minute hand at 15 minutes: 15 × 6 = 90 degrees.
> Angle between them: 97.5 - 90 = 7.5 degrees.

**reverse the word 'benchmark' (the item both missed with thinking off)**
NVFP4 (245 chars, right):
> The word 'benchmark' spelled backwards.
> b-e-n-c-h-m-a-r-k
> Reversed: k-r-a-m-h-c-n-e-b
> kramhcneb
> Let me verify: benchmark has letters b, e, n, c, h, m, a, r, k (9 letters).
> Reversed: k, r, a, m, h, c, n, e, b → kramhcneb
> Yes, that's correct.

EXL3 (219 chars, right):
> The word "benchmark" spelled backwards.
> b-e-n-c-h-m-a-r-k
> Reversed: k-r-a-m-h-c-n-e-b
> So "kramhcneb"
> Let me verify: benchmark = b, e, n, c, h, m, a, r, k (9 letters)
> Reversed: k, r, a, m, h, c, n, e, b = "kramhcneb"

**predict the Python output**
NVFP4 (286 chars, right):
> Let me trace through this code.
> x = [1, 2, 3, 4, 5]
> y = x[1:-1] — this is elements from index 1 to index -2 (exclusive of -1), so y = [2, 3, 4]
> y.append(x[0] * x[-1]) — x[0] = 1, x[-1] = 5, so 1 * 5 = 5. y = [2, 3, 4, 5]
> sum(y) = 2 + 3 + 4 + 5 = 14
> len(x) = 5
> 14 - 5 = 9
> ANSWER: 9

EXL3 (282 chars, right):
> Let me trace through this Python code.
> x = [1, 2, 3, 4, 5]
> y = x[1:-1] — this slices from index 1 to index -1 (exclusive), so y = [2, 3, 4]
> y.append(x[0] * x[-1]) — x[0] = 1, x[-1] = 5, so 1 * 5 = 5. y = [2, 3, 4, 5]
> sum(y) = 2 + 3 + 4 + 5 = 14
> len(x) = 5
> 14 - 5 = 9
> ANSWER: 9

Published KLD: EXL3/TR3 4bpw ~0.025 (ties FP8), NVFP4 ~0.060. Twelve items is a probe, not a suite.

## What we got wrong, part two: the prefix cache
The first version said EXL3 "answers first" (0.52 vs 1.54 s at c1; prefill 3099 vs 1055 tok/s). Every request carried the same prompt; EXL3 replayed its prefix cache, NVFP4 (2,304-token cache blocks) recomputed. Fresh prompts: TTFT c1 NVFP4 1.29 s vs EXL3 2.31 s, c6 4.53 vs 9.82 s; fresh prefill 1,225 vs 684 tok/s; cold prefill at 211,001 tokens 2,763 vs 1,752 tok/s. EXL3 keeps: the cache (identical 1.6K prompt repeated: EXL3 0.52 s vs NVFP4 1.54 s at c1, 1.02 s vs 4.6 s at c6; a 211,001-token context replayed in 0.8 s vs 9.2 s), mixed real-prompt load (NVFP4 31.4 tok/s vs EXL3 43.4 tok/s aggregate, TTFT 1.97 s vs 0.66 s), 4× context, 4.7× KV, 13-min boot.


## Real prompts: 40 across 8 categories (thinking off, c1, streaming)

| category | auto score NVFP4 | auto score EXL3 | judge (NVFP4 / EXL3 / tie) | TTFT NVFP4 | TTFT EXL3 | decode NVFP4 | decode EXL3 | tokens (med) |
|---|---|---|---|---|---|---|---|---|
| coding | 100% | 80% | 3 / 1 / 1 | 0.32 s | 0.34 s | 48.3 | 41.9 | 110 / 295 |
| reasoning | 100% | 100% | — | 0.37 s | 0.31 s | 47.8 | 42.3 | 177 / 163 |
| json | 100% | 100% | — | 0.42 s | 0.53 s | 52.9 | 50.3 | 36 / 36 |
| html | 100% | 100% | 0 / 1 / 4 | 0.40 s | 0.47 s | 52.6 | 56.1 | 138 / 129 |
| prose | 75% | 55% | 1 / 2 / 2 | 0.34 s | 0.30 s | 18.8 | 19.5 | 200 / 199 |
| narrative | 89% | 76% | 3 / 2 / 0 | 0.34 s | 0.29 s | 18.7 | 17.9 | 307 / 335 |
| summary | 60% | 70% | 1 / 1 / 3 | 1.68 s | 7.29 s | 36.9 | 34.0 | 205 / 187 |
| format | 60% | 96% | 1 / 1 / 3 | 0.34 s | 0.33 s | 28.7 | 21.1 | 27 / 20 |

Overall auto score (checkable categories): NVFP4 86%, EXL3 85%. Median TTFT across all 40: NVFP4 0.37 s, EXL3 0.33 s. Median decode: NVFP4 41.9 tok/s, EXL3 38.4 tok/s.
Mixed load, c4 (four different prompt types in flight): aggregate NVFP4 31.4 tok/s vs EXL3 43.4 tok/s; median TTFT 1.97 s vs 0.66 s; auto score 86% vs 84%.
Thinking on (coding + reasoning): auto score NVFP4 100% vs EXL3 100%; median TTFT 0.36 s vs 0.32 s.
Blind pairwise judge (qwen3.8-27b), both orders, win only if consistent: NVFP4 9, EXL3 8, tie 13.

Items where the auto score differed:
- code4 (coding): NVFP4 100%  · EXL3 0% [0/6 tests · SyntaxError: invalid syntax]
- prose4 (prose): NVFP4 100%  · EXL3 0% [words 218 in 150-200]
- story2 (narrative): NVFP4 67% [words 231 in 120-200] · EXL3 100% 
- story3 (narrative): NVFP4 100%  · EXL3 50% [words 368 in 200-300]
- story5 (narrative): NVFP4 100%  · EXL3 50% [words 265 in 150-250]
- sum2 (summary): NVFP4 0% [words 112 in 20-80; paragraphs=1] · EXL3 50% [words 98 in 20-80]
- fmt2 (format): NVFP4 100%  · EXL3 80% [table rows=2+header]
- fmt4 (format): NVFP4 0% [words 22 in 1-20] · EXL3 100% 
- fmt5 (format): NVFP4 0% [lines=3] · EXL3 100% 

### Prefill vs prompt length

Cold = first request at that length, a new prompt: this is the real prefill compute. Repeat = the identical prompt sent again, which is a prefix-cache hit on both engines and measures the cache, not prefill.

| prompt tokens | NVFP4 cold tok/s (s) | EXL3 cold tok/s (s) | NVFP4 repeat | EXL3 repeat |
|---|---|---|---|---|
| 6,899 | 1,482 (4.7 s) | 775 (8.9 s) | 1,479 (4.7 s) | 17,252 (0.4 s) |
| 13,772 | 1,559 (8.8 s) | 1,614 (8.5 s) | 2,283 (6.0 s) | 35,919 (0.4 s) |
| 27,518 | 1,876 (14.7 s) | 1,711 (16.1 s) | 4,598 (6.0 s) | 55,387 (0.5 s) |
| 55,097 | 2,384 (23.1 s) | 1,660 (33.2 s) | 9,076 (6.1 s) | 101,681 (0.5 s) |
| 110,255 | 2,684 (41.1 s) | 1,780 (61.9 s) | 18,246 (6.0 s) | 176,340 (0.6 s) |
| 211,001 | 2,763 (76.4 s) | 1,752 (120.4 s) | 22,931 (9.2 s) | 261,333 (0.8 s) |


## Boot and load time
Launch command → first `/health` 200, this run: EXL3 13 min (local weights both nodes, warm trellis JIT cache); NVFP4 23 min (worker loads over NFS from head (Reddie page cache warm), TileLang cache partly warm). NVFP4's worker reads its
weights over NFS from the head on this cluster (no local copy of the base on Spark4). Both JIT-compile on first boot.

## What broke, and the fixes
- EXL3 kit: `count_shards()` uses `find -type f` (misses HF-cache symlinks) → "0 / 120 shards"; fix `find -L`.
- EXL3 kit: worker needs the full ~164 GiB; root-owned `~/.cache/vllm-glm53-flash` kills the launch silently (chown);
  binds `--host 127.0.0.1` (set `0.0.0.0`).
- NVFP4: run the published recipe verbatim (1M context starves the KV pool at TP2: three NVRM OOM reboots + a stall).
  `vm.swappiness=0` resets on reboot. Poll `/health`, not `/v1/models`.
- Both: verify SM clocks under load after any reboot; drop caches on every node before every launch.

## Reproduce
See `docs/article.html` §Reproduce, `tools/run_full_test.sh`, and the two repos below.

## Credits
Reederey87 · MiaAI-Lab · brandonmusic (EXL3 quant, ShapleyMCG) · turboderp (exllamav3) · IncoAI (DFlash2) ·
RedHatAI (NVFP4 weights) · zai-org (GLM-5.3-Flash) · malaiwah, drowzeys.
Repos: github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark · github.com/tonyd2wild/glm53-flash-exl3-2x-dgx-spark

## Caveats
One quality probe is not a quality study. Raise EXL3's `--max-num-seqs` and re-sweep c5–c8. Neither lane is the
abliterated variant. Two specific quants on one specific cluster.
