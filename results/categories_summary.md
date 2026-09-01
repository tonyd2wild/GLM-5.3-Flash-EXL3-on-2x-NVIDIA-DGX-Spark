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
