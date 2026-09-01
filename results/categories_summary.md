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
Thinking on (coding + reasoning): auto score NVFP4 96% vs EXL3 94%; median TTFT 0.36 s vs 0.28 s.
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

### Thinking on, all 40 prompts

| category | auto NVFP4 | auto EXL3 | TTFT NVFP4 | TTFT EXL3 | decode NVFP4 | decode EXL3 | tokens (med) |
|---|---|---|---|---|---|---|---|
| coding | 100% | 100% | 0.31 s | 0.30 s | 42.3 | 42.0 | 1112 / 871 |
| reasoning | 100% | 100% | 0.37 s | 0.29 s | 51.4 | 51.3 | 211 / 236 |
| json | 100% | 100% | 0.38 s | 0.26 s | 49.7 | 49.5 | 142 / 158 |
| html | 100% | 100% | 0.41 s | 0.16 s | 46.2 | 42.6 | 623 / 744 |
| prose | 100% | 80% | 0.32 s | 0.28 s | 39.7 | 34.7 | 1261 / 1639 |
| narrative | 80% | 80% | 0.35 s | 0.31 s | 33.3 | 36.4 | 1936 / 2208 |
| summary | 90% | 90% | 1.42 s | 0.26 s | 45.1 | 34.3 | 918 / 953 |
| format | 100% | 100% | 0.34 s | 0.28 s | 49.0 | 39.4 | 189 / 317 |

Overall with thinking on: auto score NVFP4 96% vs EXL3 94%; median TTFT 0.36 s vs 0.28 s; median decode 45.4 vs 41.9 tok/s.

### Agent loop: the whole conversation re-sent every turn

Every turn re-sends the full history (system prompt, every earlier user turn, every earlier assistant reply) plus one new instruction; the assistant's real reply is appended for the next turn. Thinking off, 200-token replies. The long version carries a 30K-token document in the first turn, so every later turn re-sends it too.

| run | turns | final context (tok) | TTFT first turn | TTFT median | TTFT p90 | TTFT last turn | decode (med) | total |
|---|---|---|---|---|---|---|---|---|
| NVFP4 short | 20 | 3,206 | 0.36 s | 1.28 s | 2.01 s | 2.1 s | 21.1 tok/s | 158.1 s |
| EXL3 short | 20 | 3,222 | 0.53 s | 0.96 s | 1.08 s | 1.1 s | 20.1 tok/s | 161.5 s |
| NVFP4 long | 10 | 29,222 | 17.43 s | 4.04 s | 4.28 s | 4.28 s | 20.6 tok/s | 106.7 s |
| EXL3 long | 10 | 29,212 | 32.57 s | 1.02 s | 1.34 s | 1.02 s | 19.9 tok/s | 99.3 s |

### Determinism at temperature 0

The same 40 prompts three times per lane, temperature 0, same state.

| lane | outputs byte-identical across runs | auto score per run | items whose score changed | token-count spread, median / max |
|---|---|---|---|---|
| NVFP4 | 10/40 (25%) | 86% / 88% / 81% | 8 (prose1, prose4, story1, story2, story3, sum2, sum5, fmt5) | 12 / 465 |
| EXL3 | 9/40 (22%) | 85% / 79% / 82% | 6 (code1, prose1, prose2, story1, story4, fmt4) | 14 / 719 |

### Tokens per joule

GPU power from nvidia-smi on both nodes of each lane (1 Hz for 60 s) during a c4 counting load; tokens per joule = lane throughput divided by the sum of the two nodes' average GPU power. GPU power only, not wall power.

| lane | throughput under load | node GPU power (W) | lane GPU power (W) | tokens per joule |
|---|---|---|---|---|
| NVFP4 | 123.0 tok/s | 26.5 + 24.2 | 50.7 | 2.426 |
| EXL3 | 138.6 tok/s | 34.9 + 33.2 | 68.1 | 2.035 |

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
