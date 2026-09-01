# EXL3 vs NVFP4 for GLM-5.3-Flash on DGX Spark: a head-to-head on the same 4-node cluster

*2Wild fleet report, 2026-09-01. Author: tonyd2wild (deploy + bench run with Kai).*

## TL;DR

We ran the same 320B-parameter MoE model, **GLM-5.3-Flash**, in two 4-bit quantizations on two
independent 2-node DGX Spark pairs at the same time, isolated from all other traffic, and measured
single-stream, 6-way concurrent, and prefill throughput with medians over repeated runs.

| | NVFP4 (Reddie + Spark4) | **EXL3 / TR3 (Bluey + Asusi)** | ratio |
|---|---|---|---|
| c1 single-stream, tok/s (median of 5) | 35.9 (27.6–39.0) | **61.1** (60.9–61.5) | **1.7×** |
| c6 aggregate, tok/s (median of 3) | 66.2 (64.3–83.2) | **122.0** (120.6–123.8) | **1.8×** |
| c6 per-stream, tok/s (median) | 17.6 | **34.9** | **2.0×** |
| prefill, tok/s (~1.5K-token prompt, median of 3) | 564 | **3,233** | **5.7×** |
| time to first token ≈ prefill wall, s | 2.88 | **0.50** | |
| run-to-run spread on c1 | ±16% | **±0.5%** | |
| max context | 262,144 | **1,048,576** | |
| quality probe (code + reasoning trap) | correct | correct | tie |

**EXL3 won every throughput line, was an order of magnitude more stable run-to-run, and offered
4× the context — with identical answers on the quality probe.** The one honest caveat: the NVFP4 lane
was still lazily JIT-compiling kernels during the run; its own published warm figure is 46.9 tok/s
single-stream, and EXL3 is still +30% against that.

---

## 1. Hardware and topology

Four NVIDIA DGX Spark boxes (GB10 superchip, sm_121a, 128 GB unified memory each, ~121 GB usable),
ring-connected over a ConnectX-7 RoCE v2 fabric on `192.168.192.0/24` (rail 0: `enp1s0f0np0` /
`rocep1s0f0`, GID index 3; rail 1 is unpopulated on our units). Nodes:

| node | fabric IP | role today |
|---|---|---|
| Reddie | 192.168.192.2 | NVFP4 head (rank 0), serves `:8000` |
| Spark4 | 192.168.192.4 | NVFP4 worker (rank 1) |
| Bluey | 192.168.192.1 | EXL3 head (rank 0), serves `:8000` |
| Asusi | 192.168.192.3 | EXL3 worker (rank 1) |

Both lanes are **tensor-parallel 2 across two nodes** (vLLM `mp` executor, `--nnodes 2`, NCCL over
IB/RoCE). They share nothing but the switch. The bench client was a Mac mini on the same tailnet.

## 2. The two lanes

### 2a. NVFP4 — the reference lane

The published 2-Spark recipe: [`tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark`](https://github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark).

- weights: `RedHatAI/GLM-5.3-Flash-NVFP4` (NVFP4 weights, compressed-tensors)
- image: `ghcr.io/tonyd2wild/vllm-glm53-flash:sm121-v11-dflash2` (vLLM + the sm121 `sparse_attn_indexer_kpool` patch)
- `--max-model-len 262144 --gpu-memory-utilization 0.85 --kv-cache-memory 3221225472 --max-num-seqs 6 --max-num-batched-tokens 8192 --block-size 2304 --moe-backend marlin --kv-cache-dtype fp8_e4m3 --enforce-eager`
- speculative decoding: DFlash2 drafter `incoai/GLM-5.3-Flash-DFlash2`, k = 7
- `vm.swappiness=0` on both nodes; worker launched first, head 25 s later
- expected (from the repo): ~15 min boot, 46.9 tok/s single-stream (code, warm), 47.7 tok/s c6 aggregate

### 2b. EXL3 — the challenger

The [Reederey87 GB10 kit](https://github.com/Reederey87/glm53-flash-exl3-2x-dgx-spark) (with the
[MiaAI-Lab](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks) sibling as cross-reference),
built and patched for our fabric. Our fork with every fix: [`tonyd2wild/glm53-flash-exl3-2x-dgx-spark`](https://github.com/tonyd2wild/glm53-flash-exl3-2x-dgx-spark).

- weights: `brandonmusic/GLM-5.3-Flash-tr3-4bpw` — EXL3 / TR3 (trellis) 4 bits per weight, 120 shards, ~164 GiB, ~91 GiB resident per node
- image: `glm53-flash-sm121:local`, built on the head from the kit's Dockerfile (exllamav3 compiled for `TORCH_CUDA_ARCH_LIST=12.1a` on top of the arm64 CUDA 13 vLLM base)
- `--quantization exl3 --max-model-len 1000000 --gpu-memory-utilization 0.85 --kv-cache-memory-bytes 15414698763 --max-num-seqs 4 --max-num-batched-tokens 3584 --kv-cache-dtype fp8 --no-async-scheduling`
- speculative decoding: same DFlash2 drafter, k = 7
- `local/prod-start.sh`: waits for ≥ 90 GiB MemFree on both nodes, wipes JIT caches on config change, ships the image and rsyncs the weights to the worker, launches worker then head
- observed: ~12 min to serve (weights ~5 min + trellis JIT); ~40% draft acceptance

Both lanes: fp8 KV cache, thinking disabled by default, `chat_template_mm.jinja` (vision-capable).

## 3. Method

**Isolation.** Before measuring, every other consumer of either lane was moved off it: the
spark-flash relay (the single endpoint our external agents use) was parked on the 3090's Qwen 27B,
the latency dashboard (which sends real probe completions, not just metric scrapes) was paused, and
the three Hermes supervisors whose default model is `glm-5.3-flash` were confirmed idle. After the run
we pulled each head's access log: **NVFP4 received 48 chat POSTs, EXL3 43 — exactly the request counts
the bench issued.** Because the supervisors run on the same Mac as the bench client, IP alone cannot
prove isolation; only the request counts can, and they match to the request.

**Simultaneity.** The two lanes were benched in parallel. They share no GPUs, no memory, and no NCCL
group, so parallel runs do not contend; this halves wall time and removes time-of-day drift.

**Warm-up.** Both engines JIT-compile kernels lazily per request shape (vLLM's `jit_monitor` logs
`TileLang/Triton JIT compilation during inference` on the first request of a new shape). Every lane
got 2× c1 + 1× c6 warm-up requests before any measurement. The first-ever completion on a fresh EXL3
boot was ~30 tok/s; its first long prefill 136 tok/s; both settle after one warm request. **Never
bench a cold lane.**

**Metrics** (2Wild house rule: throughput = median tokens/s, non-streaming, never "decode speed"):
- **c1**: 5 sequential requests, ~300-token generation, `completion_tokens / wall`; median, min, max
- **c6**: 3 rounds of 6 concurrent requests; aggregate = Σ tokens / round wall; per-stream = each
  request's tokens / its own wall (median)
- **prefill**: 3 requests with a ~1.5K-token prompt and an 8-token answer; `prompt_tokens / wall`;
  the wall is ≈ time-to-first-token
- all requests: `temperature 0`, `stream false`, `chat_template_kwargs {"enable_thinking": false}`,
  identical prompts to both lanes ("List the numbers from 1 to 300 separated by commas…")

Tool: [`tools/bench_detailed.py`](tools/bench_detailed.py) in the repo. Results 2026-09-01, 20:18–20:23 ET.

## 4. Results

| metric | NVFP4 | EXL3 |
|---|---|---|
| c1 tok/s — median (min / max), n = 5 | 35.9 (27.6 / 39.0) | 61.1 (60.9 / 61.5) |
| c6 aggregate tok/s — median (min / max), n = 3 | 66.2 (64.3 / 83.2) | 122.0 (120.6 / 123.8) |
| c6 per-stream tok/s — median | 17.6 | 34.9 |
| prefill tok/s — median, n = 3 | 564 | 3,233 |
| TTFT ≈ prefill wall (s) — median | 2.88 | 0.50 |

Earlier same-day c4 runs before isolation, for consistency: EXL3 60.4 / 140.4 then 59.9 / 152.2
(single / c4-aggregate); NVFP4 33.8 / 28.5 then 36.2 / 55.5.

**Stability.** EXL3's five c1 runs spanned 60.9–61.5 tok/s. NVFP4's spanned 27.6–39.0. That spread
is itself a finding: the NVFP4 lane was still compiling shapes and settling; the EXL3 lane was
finished settling after its warm-up.

### 4b. Full concurrency sweep, c1 → c6 (`tools/bench_sweep.py`, 3 rounds per level, isolated, parallel)

Wall-to-wall = end-to-end latency of one ~300-token request at that concurrency (median over all
requests at the level). TTFT at level c = c concurrent ~1.5K-token prompts with an 8-token answer.

| c | NVFP4 agg tok/s | NVFP4 per-stream | NVFP4 wall-to-wall | NVFP4 TTFT | EXL3 agg tok/s | EXL3 per-stream | EXL3 wall-to-wall | EXL3 TTFT |
|---|---|---|---|---|---|---|---|---|
| 1 | 38.3 | 38.3 | 8.36 s | 2.87 s | **61.2** | **61.2** | **5.23 s** | **0.50 s** |
| 2 | 68.5 | 34.3 | 9.34 s | 4.69 s | **92.0** | **46.4** | **6.89 s** | **0.77 s** |
| 3 | 94.6 | 31.5 | 10.15 s | 6.49 s | **120.3** | **40.1** | **7.98 s** | **0.83 s** |
| 4 | 66.0 | 28.6 | 11.19 s | 6.46 s | **149.6** | **37.4** | **8.55 s** | **0.93 s** |
| 5 | 80.7 | 29.0 | 11.03 s | 6.47 s | **113.6** | **36.2** | **8.84 s** | **1.03 s** |
| 6 | 85.7 | 21.0 | 16.86 s | 9.79 s | **124.1** | **35.9** | **8.92 s** | **1.02 s** |

Prefill at c1: NVFP4 565 tok/s, EXL3 3,217 tok/s. NVFP4 is the second of two full sweeps, run after
every agent had been moved off the lane (0 requests in the 3 minutes before it started); run 1
(38.6 / 67.8 / 87.6 / 67.1 / 80.4 / 86.4) agreed with run 2 within 3% at every level, so the earlier
result was not polluted and the numbers are reproducible. Isolation was checked from each head's
access log: every chat POST in the window came from the bench client, and the counts matched the
requests issued (92 per sweep). The results JSON for every run is in `results/`.

**Reading the curve.** EXL3 scales almost linearly to its peak of 149.6 tok/s at c4, then flattens to
~114–124 at c5–c6 — and the p90 wall-to-wall jumps from 8.9 s to 14–15 s there. That is the kit's
`--max-num-seqs 4`: the fifth and sixth requests queue behind a full batch. It is a configuration cap,
not the quantization, and raising it is the obvious next experiment. NVFP4 (`--max-num-seqs 6`) admits
all six but pays for it per stream: 38.6 → 21.9 tok/s, TTFT 2.9 → 9.7 s, wall-to-wall 8.3 → 16.2 s.
Its aggregate is also erratic (c4 67 < c3 88), consistent with kernels still being JIT-compiled during
the run.

**KV pool.** From each engine's own startup line: EXL3 `GPU KV cache size: 1,396,551 tokens, maximum
concurrency for 1,000,000-token requests: 1.40×`; NVFP4 `295,230 tokens, 1.13× at 262,144`. Same two
boxes per lane, 4.7× the pool.

## 5. Quality

Same prompt to both, thinking off, temperature 0 (`tools/quality_probe.py`):

1. `top_k_frequent(nums, k)` in O(n log k) with a complexity explanation and one edge case
2. the bat-and-ball trap: $1.10 total, the bat costs $1.00 more than the ball — how much is the ball?

**Both lanes answered both parts correctly** — correct heap-based top-k with the `k ≤ 0` / empty edge
case, and `ANSWER: $0.05` with the algebra written out and a check line. The diff between the two
answers is cosmetic (comment wording, spacing). Published KLD-vs-FP16 figures put EXL3/TR3 4bpw around
0.025 (tying FP8) and NVFP4 around 0.060, so a quality gap is *expected* to exist; on a probe of this
difficulty it did not surface. Harder probes (multi-file refactors, tool-call argument validity,
needle-in-200K-context) are the open items.

Vision check (64×64 solid red PNG, "what single color?"): EXL3 `Red`, NVFP4 `Red.` Both lanes serve
`chat_template_mm.jinja` and accept image inputs.

## 6. Discussion

**Where the speed comes from.** The largest gap is prefill: 5.7×. EXL3's fused trellis MoE kernels
(`fused_moe=exl3_moe`, no BF16 expert reconstruction at load) prefill a 1.5K prompt in half a second;
the NVFP4 marlin path took ~2.9 s. For agents, that is the difference users actually feel: time to
first token. Decode is 1.7–2× faster, and it holds at concurrency — c6 per-stream is 34.9 vs 17.6.

**On NVFP4's numbers.** They are below the repo's published warm figures (46.9 c1, 47.7 c6-agg). Three
contributors, in order of confidence: (1) the lane was still JIT-compiling shapes during the run — its
`jit_monitor` warnings never fully stopped; (2) the worker loaded its weights over NFS from the head
because Spark4 had no local copy of the RedHatAI base — this lengthened boot to ~40 min but should not
affect steady-state decode; (3) the count-to-300 prompt is not the repo's "code" prompt, and DFlash2
acceptance differs by prompt. None of these close a 1.7–1.8× gap; even at 46.9, EXL3 is +30% on c1.

**Context.** EXL3 serves 1,048,576 tokens of context on the same two boxes; the NVFP4 recipe serves
262,144. We learned the hard way that NVFP4 at TP2 cannot be launched at 1M ("not enough KV pool"): an
adapted launcher that set `--max-model-len 1048576` plus a pinned 8 GiB KV produced three NVRM
out-of-memory reboots of the worker at cudagraph capture and one 24-minute stall at the post-load
profiling pass, until we ran the published 256K recipe verbatim. Read the recipe first.

**Memory.** Each lane holds ~91 GiB of weights per 121 GiB node. Every failure we hit today was a
transient spike on top of that baseline — cudagraph capture, the profiling forward pass, page cache
inflated by a 164 GiB rsync (MemFree 1 GiB on the worker, which stalls vLLM's memory gate until
`echo 3 > drop_caches`). `free -g` under-reports on GB10; drop caches on every node before every
launch.

## 7. What broke on the EXL3 kit, and the fixes (all in `NOTES.md`)

1. `count_shards()` used `find -type f`, which does not match the symlinks a standard HF cache uses →
   "0 / 120 shards" → launch dies. Fix: `find -L`. (Upstream-worthy.)
2. The worker needs the **full** model on disk (~164 GiB); vLLM TP reads slices of every shard.
3. `~/.cache/vllm-glm53-flash` left root-owned by a prior container → `mkdir tilelang` fails → the
   launch exits with **no containers**. `chown` it on both nodes first.
4. The kit binds `--host 127.0.0.1`. Serves on-box, unreachable from the fabric, tailnet, fleet, and
   any remote bench. Set `0.0.0.0` on both serve lines.
5. `ensure_image()` re-ships the 21 GB image to the worker on every launch (local-image key mismatch).
   Harmless, ~2 min.
6. After a large file move the memory gate stalls on page cache: drop caches on both nodes.

And on the NVFP4 side: the single highest-value lesson of the day — **run the published recipe
verbatim before adapting anything.** `vm.swappiness=0` does not survive a reboot; the head prints
`No available shared memory broadcast block found in 60 seconds` every minute while a worker is
compiling, and that message is benign unless the worker is actually dead (check `docker ps` and a
fabric ping, not the message); poll `/health`, not `/v1/models`.

## 8. Reproduce

**NVFP4 (2 nodes):** clone the NVFP4 repo on both nodes, pull the image on both, weights at
`/var/tmp/glm-5.3-flash-nvfp4` on both (or NFS-export from the head), drafter at
`/var/tmp/models/GLM-5.3-Flash-DFlash2`, the sm121 patch at `~/patches/sparse_attn_indexer_kpool.py`,
`sysctl vm.swappiness=0` and `echo 3 > drop_caches` on both, then
`./launch-glm53-vllm-tp2-dflash2.sh 1` on the worker, wait 25 s, `./launch-glm53-vllm-tp2-dflash2.sh 0`
on the head. `until curl -sf http://<head>:8000/health; do sleep 20; done`.

**EXL3 (2 nodes):** clone our fork on the head, `docker build -t glm53-flash-sm121:local .`, copy
`.env.example` to `.env` and set your node IPs, `WORKER_SSH`, and RoCE NIC/GID (verify with
`cat /sys/class/infiniband/<hca>/ports/1/state` and `.../gids/3`), `chown -R $USER ~/.cache/vllm-glm53-flash`
on both nodes, drop caches on both, then `set -a; . ./.env; set +a; ./local/prod-start.sh`. The kit
downloads the weights, ships the image, rsyncs the worker, and launches. Poll `/health`.

**Bench:** `python3 tools/bench_detailed.py http://<head>:8000 <served-model> "<label>"` per lane,
with every other consumer moved off the lane first, then check the head's access log.

## 9. Credits

- **[Reederey87](https://github.com/Reederey87/glm53-flash-exl3-2x-dgx-spark)** — the GB10-hardened
  2-Spark EXL3 kit we followed end to end
- **[MiaAI-Lab](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks)** — parallel 2-Spark recipe, image, weights mirror
- **brandonmusic** — the `GLM-5.3-Flash-tr3-4bpw` EXL3 quant (ShapleyMCG License)
- **[turboderp](https://github.com/turboderp/exllamav3)** — ExLlamaV3 / the EXL3 format
- **IncoAI** — the `GLM-5.3-Flash-DFlash2` speculative drafter
- **RedHatAI** — the NVFP4 weights; **zai-org** — GLM-5.3-Flash
- **malaiwah**, **drowzeys** — surrounding tooling and the abliteration lineage

## 10. Caveats and what's next

- One quality probe is not a quality study. The open items are harder probes: multi-file refactor
  correctness, tool-call argument validity, long-context recall past 200K.
- NVFP4 should be re-benched after a long soak so its lazy JIT is fully warm, and with the repo's
  own "code" prompt, to reproduce 46.9 on this hardware.
- Neither lane here is the abliterated variant; both are the base model.
- These are two specific quants on one specific box. The KLD literature says EXL3 should win on
  quality-per-bit; what we measured on this cluster is that it also wins on speed, decisively.
