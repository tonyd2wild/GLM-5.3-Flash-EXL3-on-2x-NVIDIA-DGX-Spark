## NVFP4 TP4 (4 Sparks, CUDA graphs) vs the TP2 lanes

Same night, same tools, same prompts, same isolation. TP4 = all four Sparks in one tensor-parallel group with CUDA graphs on (the validated 08-31 recipe), RedHat NVFP4 base weights, 1M context. The TP2 lanes are the two-node pairs benched earlier: NVFP4 TP2 (Reddie + Spark4, eager) and EXL3 TP2 (Bluey + Asusi, eager). The TP4 lane uses all four boxes, so per-box it is half a lane; read the per-box column for what the hardware is doing.

| metric | NVFP4 TP4 | NVFP4 TP2 | EXL3 TP2 | TP4 vs NVFP4 TP2 |
|---|---|---|---|---|
| c1 single-stream tok/s (sweep) | 101.1 | 64.3 | 61.8 | +57% |
| c1 single-stream tok/s (detailed, n=5) | 101.9 | 64.0 | 61.5 | +59% |
| c6 aggregate tok/s | 319.1 | 136.3 | 125.2 | +134% |
| c6 per-stream tok/s | 54.8 | 35.0 | 35.8 | +57% |
| peak aggregate tok/s | 319.1 | 138.6 | 149.7 | +130% |
| TTFT fresh 1.6K prompt, c1 (s) | 0.9 | 1.3 | 2.3 | -29% (lower is better) |
| TTFT fresh, c6 (s) | 4.2 | 4.5 | 9.8 | -7% (lower is better) |
| prefill fresh 1.6K tok/s | 1,736.0 | 1,225.0 | 684.0 | +42% |
| cold prefill at ~211K tok/s | 1,670.0 | 2,763.0 | 1,752.0 | -40% |
| wall-to-wall c1 / c6 (s) | 3.17 / 5.84 | 4.98 / 10.09 | 5.18 / 8.95 |  |
| real prompts auto score, thinking off | 83% | 86% | 85% | -3% |
| real prompts median decode tok/s | 61.0 | 41.9 | 38.4 | +46% |
| mixed c4 aggregate tok/s / TTFT s | 72.3 / 0.68 | 31.4 / 1.97 | 43.4 / 0.66 |  |
| thinking on auto score | 96% | 96% | 94% | +0% |
| agent loop 30K doc: TTFT med s / total s | 1.83 / 57.7 | 4.04 / 106.7 | 1.02 / 99.3 |  |
| 12-item battery off / on | 11/12 / 12/12 | 11/12 / 12/12 | 11/12 / 12/12 |  |
| load throughput tok/s (c4 counting, 60 s) | 242.8 | 123.0 | 138.6 | +97% |
| lane GPU power W (all nodes) | 101.9 | 50.7 | 68.1 | +101% (lower is better) |
| tokens per joule | 2.4 | 2.4 | 2.0 | -2% |
| boot launch → healthy (min) | 13.0 | 23.0 | 13.0 | -43% (lower is better) |

### Per category, thinking off (auto score / decode tok/s / TTFT s)

| category | NVFP4 TP4 | NVFP4 TP2 | EXL3 TP2 |
|---|---|---|---|
| coding | 80% / 58.4 / 0.30 | 100% / 48.3 / 0.32 | 80% / 41.9 / 0.34 |
| reasoning | 100% / 63.6 / 0.31 | 100% / 47.8 / 0.37 | 100% / 42.3 / 0.31 |
| json | 100% / 87.2 / 0.30 | 100% / 52.9 / 0.42 | 100% / 50.3 / 0.53 |
| html | 100% / 94.3 / 0.30 | 100% / 52.6 / 0.40 | 100% / 56.1 / 0.47 |
| prose | 40% / 26.0 / 0.26 | 75% / 18.8 / 0.34 | 55% / 19.5 / 0.30 |
| narrative | 76% / 23.3 / 0.32 | 89% / 18.7 / 0.34 | 76% / 17.9 / 0.29 |
| summary | 70% / 61.5 / 1.13 | 60% / 36.9 / 1.68 | 70% / 34.0 / 7.29 |
| format | 96% / 34.2 / 0.23 | 60% / 28.7 / 0.34 | 96% / 21.1 / 0.33 |

### Determinism (3 runs at temp 0)

| lane | identical outputs | auto score per run |
|---|---|---|
| NVFP4 TP4 | 10/40 | 83% / 87% / 83% |
| NVFP4 TP2 | 10/40 | 86% / 88% / 81% |
| EXL3 TP2 | 9/40 | 85% / 79% / 82% |

### Cold prefill vs length, tok/s

| prompt tokens | NVFP4 TP4 | NVFP4 TP2 | EXL3 TP2 |
|---|---|---|---|
| 6,899 | 1,398 | 1482 | 775 |
| 13,772 | 2,400 | 1559 | 1614 |
| 27,518 | 1,639 | 1876 | 1711 |
| 55,097 | 882 | 2384 | 1660 |
| 110,255 | 1,301 | 2684 | 1780 |
| 211,001 | 1,670 | 2763 | 1752 |
