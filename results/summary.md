## Headline (isolated, both lanes benched simultaneously, 2026-09-01 17:34:23)
| | NVFP4 (Reddie + Spark4) | EXL3 (Bluey + Asusi) | EXL3 ÷ NVFP4 |
|---|---|---|---|
| c1 single-stream tok/s | 64.3 | 61.8 | 1.0× |
| peak aggregate tok/s (at c) | 138.6 (c3) | 149.7 (c4) | 1.1× |
| c6 aggregate tok/s | 136.3 | 125.2 | 0.9× |
| c6 per-stream tok/s | 35.0 | 35.8 | 1.0× |
| prefill tok/s (~1.5K prompt) (warm, median of last 3 of 6 sequential 1.5K prompts; first-after-boot cold sample: EXL3 2685 tok/s / NVFP4 1214 tok/s) | 1055 | 3099 | 2.9× |
| TTFT c1 / c6 | 1.54 s / 4.6 s | 0.52 s / 1.02 s | 3.0× / 4.5× lower |
| wall-to-wall c1 / c6 (300-tok answer) | 4.98 s / 10.09 s | 5.18 s / 8.95 s | 1.0× / 1.1× lower |
| c1 spread (detailed, n=5) | 62.8–64.7 (±1.5%) | 59.8–61.9 (±1.7%) | |
| max context | 262,144 | 1,048,576 | 4× |
| KV pool (tokens) | 295,230 | 1,396,551 | 4.7× |
| quality probe | correct | correct | tie |
| boot: launch → /health 200 | 23 min (worker loads over NFS from head (Reddie page cache warm), TileLang cache partly warm) | 13 min (local weights both nodes, warm trellis JIT cache) | |

## Sweep c1–c6 (3 rounds per level)
| c | NVFP4 agg | per-stream | wall-to-wall | TTFT | EXL3 agg | per-stream | wall-to-wall | TTFT |
|---|---|---|---|---|---|---|---|---|
| 1 | 64.3 | 64.3 | 4.98 s | 1.54 s | **61.8** | **61.8** | **5.18 s** | **0.52 s** |
| 2 | 111.1 | 55.5 | 5.76 s | 2.19 s | **92.5** | **46.5** | **6.88 s** | **0.76 s** |
| 3 | 138.6 | 47.0 | 6.81 s | 3.36 s | **120.2** | **41.2** | **7.76 s** | **0.83 s** |
| 4 | 111.2 | 48.5 | 6.61 s | 3.05 s | **149.7** | **37.4** | **8.55 s** | **0.88 s** |
| 5 | 131.3 | 47.0 | 6.81 s | 3.11 s | **116.9** | **36.2** | **8.85 s** | **1.06 s** |
| 6 | 136.3 | 35.0 | 10.09 s | 4.6 s | **125.2** | **35.8** | **8.95 s** | **1.02 s** |
