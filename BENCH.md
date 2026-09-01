# Bench — EXL3 vs NVFP4 (GLM-5.3-Flash, same 4-Spark cluster)

Canonical results live in `results/` (sweep JSON per lane, detailed JSON, quality answers, boot.json) and are
rendered by `tools/make_article.py` into `REPORT.md`, `results/summary.md` and `docs/article.html`.
Method: 2Wild house rule — throughput = median tok/s, non-stream; isolate the lane, warm it, verify clocks under load.

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

