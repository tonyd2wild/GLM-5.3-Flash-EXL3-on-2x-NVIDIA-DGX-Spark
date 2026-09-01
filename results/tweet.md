# Tweet copy — NVFP4 vs EXL3 (draft for Tony; no em dashes, no hashtags)

## Main post (attach: poster_nvfp4_vs_exl3.png)

Same model. Same hardware. Two 4-bit quants.

GLM-5.3-Flash, NVFP4 vs EXL3, each on its own pair of DGX Sparks, benched at the same time, isolated, c1 to c6.

EXL3 won every line:
- 1.7x single-stream decode (61 vs 38 tok/s)
- 5.7x prefill (3,217 vs 565 tok/s)
- TTFT 0.5s vs 2.9s
- 4.7x the KV pool, 1M context vs 256K
- quality tie

Full write-up, methodology, and the whole c1-c6 curve below.

## Reply 1 (attach: chart_agg.png)

Aggregate throughput vs concurrency. EXL3 climbs to 150 tok/s at c4 and flattens only because that kit ships with max-num-seqs 4 (a config cap, not the quant). NVFP4 peaks at 95 at c3.

## Reply 2 (attach: chart_ttft.png)

Time to first token is where agents feel it. EXL3 holds 0.5 to 1.0s across c1-c6. NVFP4 climbs from 2.9s to 9.8s.

## Reply 3 (attach: chart_w2w.png)

Wall-to-wall for a 300-token answer at c6: EXL3 8.9s, NVFP4 16.9s. Same two boxes each.

## Reply 4 (no image)

Method matters. Relay parked, latency monitor paused, supervisors moved off, then each head's access log checked so only the bench touched the lane. NVFP4 swept twice, agents off the second time: within 3% both times.

Article + repos: [ARTICLE LINK] · github.com/tonyd2wild/glm53-flash-exl3-2x-dgx-spark · github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark

Credits: Reederey87, MiaAI-Lab, brandonmusic, turboderp, IncoAI, RedHatAI, zai-org.
