## TP4 head-to-head, matched config: DeepSeek V4 Flash Vision vs GLM-5.3-Flash NVFP4

Each model alone on all four Sparks (TP4), max-num-seqs 64, CUDA graphs on, k=5 DSpark with Patch 4 for DeepSeek, DFlash2 k=7 for GLM, 1M context, same battery, same isolation, run back to back on 2026-09-02. Lower is better only where the row says so.

### Headline: prose and code decode from real prompts (tok/s, median), then fresh-prompt first token

| | DeepSeek | GLM |
|---|---|---|
| prose decode, C1 | 42.0 | 31.2 |
| code decode, C1 | 98.3 | 75.1 |
| prose decode under mixed C16 | 20.7 | 13.3 |
| code decode under mixed C16 | 27.5 | 23.5 |
| mixed real-prompt aggregate C16 | 123.9 | 100.0 |
| first token, fresh 1.6K prompt, C1 / C16 | 0.94 / 9.99 s | 0.91 / 11.06 s |
| cold prefill, fresh 211K prompt | 4,865 tok/s | 4,840 tok/s |

Counting-prompt numbers below are the speculative-decode ceiling (the drafter's easiest sequence), kept for comparability with earlier runs, not the headline.

### Aggregate tok/s vs concurrency (counting prompt = speculative-decode ceiling, ~300-token answers, median of 2 rounds)

| C | DeepSeek | GLM | GLM vs DeepSeek |
|---|---|---|---|
| 1 | 95.2 | 100.3 | +5% |
| 2 | 171.0 | 121.3 | -29% |
| 3 | 214.9 | 193.1 | -10% |
| 4 | 290.2 | 246.2 | -15% |
| 5 | 266.3 | 289.9 | +9% |
| 6 | 367.9 | 307.8 | -16% |
| 8 | 465.8 | 364.6 | -22% |
| 16 | 586.3 | 391.7 | -33% |
| 32 | 854.5 | 594.9 | -30% |
| 48 | 1,073.2 | 816.8 | -24% |

### Per-stream tok/s vs concurrency

| C | DeepSeek | GLM |
|---|---|---|
| 1 | 95.2 | 100.3 |
| 2 | 85.5 | 60.6 |
| 3 | 73.7 | 64.8 |
| 4 | 74.0 | 63.6 |
| 5 | 54.2 | 58.6 |
| 6 | 62.5 | 52.8 |
| 8 | 59.2 | 46.3 |
| 16 | 37.3 | 25.0 |
| 32 | 27.9 | 19.1 |
| 48 | 23.7 | 17.3 |

### Time to first token, fresh 1.6K prompts (s, median)

| C | DeepSeek | GLM |
|---|---|---|
| 1 | 0.94 | 0.91 |
| 8 | 7.30 | 5.38 |
| 16 | 9.99 | 11.06 |

### Real prompts, 40 across 8 categories, C1 (auto score / decode tok/s / TTFT s)

| category | DeepSeek | GLM |
|---|---|---|
| coding | 100% / 98.3 / 0.19 | 80% / 75.1 / 0.30 |
| reasoning | 80% / 88.3 / 0.24 | 100% / 72.5 / 0.32 |
| json | 100% / 85.4 / 0.41 | 100% / 79.9 / 0.31 |
| html | 89% / 103.4 / 0.19 | 100% / 94.4 / 0.29 |
| prose | 60% / 42.0 / 0.17 | 35% / 31.2 / 0.30 |
| narrative | 90% / 44.8 / 0.29 | 76% / 32.4 / 0.27 |
| summary | 80% / 61.3 / 0.98 | 60% / 60.4 / 1.11 |
| format | 100% / 50.3 / 0.18 | 96% / 35.8 / 0.24 |

| real prompts overall | DeepSeek | GLM |
|---|---|---|
| auto score C1 | 87% | 81% |
| median decode C1 | 74.2 | 63.8 |
| mixed C4 aggregate / TTFT | 94.2 / 0.34 s | 73.5 / 0.94 s |
| mixed C16 aggregate / TTFT | 123.9 / 0.90 s | 100.0 / 2.18 s |
| auto score C16 | 89% | 90% |

### Cold prefill vs prompt length (tok/s)

| prompt tokens | DeepSeek | GLM |
|---|---|---|
| 6,890 | 2,412 | 1,974 |
| 13,763 | 4,566 | 2,470 |
| 27,509 | 4,638 | 3,023 |
| 55,088 | 4,620 | 3,586 |
| 110,246 | 4,290 | 3,796 |
| 181,760 | 4,865 | 4,840 |

### Power at C16 (GPU, four nodes, 60 s)

| | DeepSeek | GLM |
|---|---|---|
| throughput under load | 544.9 tok/s | 465.9 tok/s |
| four-node GPU power | 177.9 W | 156.0 W |
| tokens per joule | 3.06 | 2.99 |

### Verdict (computed from the rows above)

- Single stream (counting, n=5): DeepSeek 97.4 vs GLM 99.9 tok/s (+3% for GLM).
- Peak aggregate: DeepSeek 1,073.2 at C48; GLM 816.8 at C48. First level where the next step gains under 5%: DeepSeek C4, GLM none through C48 (the DeepSeek C5 dip is a two-round median artifact; C6 and up climb again).
- C48 aggregate: DeepSeek 1,073.2 vs GLM 816.8 (-24% for GLM).
- Real prompts C1 decode: DeepSeek 74.2 vs GLM 63.8 tok/s; prose: DeepSeek 42.0 vs GLM 31.2; coding: 98.3 vs 75.1.
- Quality on the 40 prompts (same noise band as always, ±4 pts run to run): DeepSeek 87% vs GLM 81%.
