# Tweet copy (final, same-state run 2026-09-01)

Attach: results/poster_nvfp4_vs_exl3.png (lead image), results/chart_agg.png, results/chart_ttft.png, results/chart_w2w.png.
Link goes through Hootsuite (Post Bridge strips links on X). Article: https://claude.ai/code/artifact/bdcc64b1-44f0-49e7-b3dc-f189d5674f7a

## Main post

NVFP4 vs EXL3. Same model, same boxes, same minute.

GLM-5.3-Flash on 2× DGX Spark per lane, TP2 each, both lanes benched simultaneously at c1 to c6, nothing else touching either.

NVFP4 wins decode: 64.0 vs 61.5 tok/s single stream, +14 to 30% per stream at c2 to c5, faster wall-to-wall through c5.

EXL3 wins the first token: 1.0 s vs 4.6 s TTFT at c6, prefill 2.9× (3,099 vs 1,055 tok/s), 1M context and 4.7× the KV pool on the same two boxes, boots in 13 min vs 23.

Quality battery, 12 items, thinking off and on: 11/12 vs 11/12, then 12/12 vs 12/12. Same miss, same fix. The quant did not change how smart it is.

Our first pass said EXL3 won everything. Two of the four Sparks were clock-capped at ~700 MHz after a reboot. We caught it, restarted, and ran the whole thing again. Numbers here are the second run.

Full method, isolation proof, every number and the reasoning traces side by side: [link]

## Short version

Two 4-bit quants of GLM-5.3-Flash, two 2-node DGX Spark lanes, benched at the same time.
NVFP4: +4% decode, +14 to 30% per stream under load.
EXL3: first token 4.5× sooner at c6, 2.9× prefill, 1M context, 4.7× KV pool.
Quality: tie, 11/12 and 12/12 on both.
Details: [link]

## Reply (thread)

Both recipes are public: the NVFP4 2-Spark launcher (github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark) and the EXL3 kit from Reederey87 with brandonmusic's tr3-4bpw weights and turboderp's exllamav3 built for sm_121a. Credits in the article.

## Opening post (thread starter, with results/card_nvfp4_vs_exl3.png)

Everyone kept saying EXL3 beats NVFP4. So we ran both on the same model, the same DGX Sparks, at the same minute.

GLM-5.3-Flash, two 4-bit quants, two 2-node TP2 lanes, c1 to c6, nothing else touching either lane.

NVFP4 decodes faster: 64.0 vs 61.5 tok/s single stream, +14 to 30% per stream under load.

EXL3 gets you the first token 4.5x sooner at c6 (1.0 s vs 4.6 s), prefills 2.9x faster, holds 1M context and 4.7x the KV pool on the same two boxes, and boots in 13 min instead of 23.

Quality: a tie. 12-item reasoning battery, 11/12 vs 11/12 thinking off, 12/12 vs 12/12 thinking on.

Our first run said EXL3 won everything. Two Sparks were clock-capped at ~700 MHz after a reboot. We caught it, restarted, ran it all again. These are the second-run numbers.

Full write-up, method, isolation proof and the reasoning traces side by side in the thread.

Reply 1: article link (via Hootsuite). Reply 2: both recipes are public (NVFP4 launcher repo + the EXL3 kit: Reederey87, brandonmusic tr3-4bpw, turboderp exllamav3 for sm_121a). Credits in the article.

Cards: results/card_nvfp4_vs_exl3.png (icons, pick) · results/card_nvfp4_vs_exl3_alt.png (plain). gpt-image-2, numbers verified against results/*.json.
