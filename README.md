# GLM-5.3-Flash EXL3 on 2x NVIDIA DGX Spark (GB10 / sm_121)

Private deploy notes + launch kit for running **GLM-5.3-Flash** as an **EXL3 / TR3 4bpw**
quant across **two DGX Spark (GB10, sm_121a)** boxes over a RoCE fabric, TP2, with a
DFlash2 speculative drafter and 1M context.

This repo documents *our* bring-up on the 2Wild Spark cluster (nodes **Bluey** + **Asusi**).
It stands on the shoulders of the people credited below — start with their repos; this is
the delta that made it run on our hardware.

> Status: private. Internal 2Wild infra notes. Do not distribute the credential-bearing
> `.env` (only `.env.example` is committed).

---

## Why EXL3 here

We already run GLM-5.3-Flash in **NVFP4** (marlin, fp8 KV) on the 4-Spark ring. EXL3
(turboderp's ExLlamaV3, trellis / QTIP quant) trades a bit of engine complexity for
**materially better quality per bit**:

| Quant | bits | KLD vs FP16 | Notes |
|-------|------|-------------|-------|
| FP8   | 8    | ~0.025      | reference-ish, 2x the bytes |
| **EXL3 / TR3** | **~4** | **~0.025** | ties FP8 quality at ~half the bytes |
| NVFP4 | ~4   | ~0.060      | faster kernels, more quant drift |

The difference is not casual chat — it shows up on hard code, multi-step reasoning,
tool-calling accuracy, and long-context coherence. Speed is roughly a wash single-stream on
GB10; EXL3 tends to edge ahead in aggregate throughput at concurrency. We keep both lanes and
bench head-to-head (see `BENCH.md`).

---

## Topology (our cluster)

```
Reddie  (192.168.192.2)  <- GLM-5.3-Flash NVFP4 TP2 head, serves :8000 (unchanged endpoint)
Spark4  (192.168.192.4)  <- NVFP4 TP2 worker
Bluey   (192.168.192.1)  <- EXL3 head  (this repo) serves :8000 on Bluey
Asusi   (192.168.192.3)  <- EXL3 worker (this repo)
```

RoCE: **rail 0** on both EXL3 nodes — `rocep1s0f0` / `enp1s0f0np0`, **GID index 3**
(carries `::ffff:192.168.192.x`). Symmetric on head + worker.

> ⚠️ The upstream kits default to an **asymmetric** rail (head `f1`, worker `f0`) for their
> hardware. On our Sparks `f1` is DOWN and `f0` is the active CX7 port on every node, so we
> pin **both** head and worker to `f0` / gid3. Verify your own NICs before copying our `.env`:
> ```bash
> cat /sys/class/infiniband/rocep1s0f0/ports/1/state          # want: ACTIVE
> cat /sys/class/infiniband/rocep1s0f0/ports/1/gids/3         # want: ...ffff:<your fabric ip>
> ```

---

## The model

- **Weights:** [`brandonmusic/GLM-5.3-Flash-tr3-4bpw`](https://huggingface.co/brandonmusic/GLM-5.3-Flash-tr3-4bpw)
  — GLM-5.3-Flash 320B MoE / 18B active, EXL3/TR3 4bpw, 120 shards (~164 GiB, ~82 GiB resident/node).
  Mirror: [`Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw`](https://huggingface.co/Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw).
- **Speculative drafter:** [`incoai/GLM-5.3-Flash-DFlash2`](https://huggingface.co/incoai/GLM-5.3-Flash-DFlash2)
  (rev `7d74cdd881ed7e32c31175984a67823127b66cfe`, ~2.3 GiB), k=7.
- **Base model:** GLM-5.3-Flash by zai-org.

`HF_HUB_DISABLE_XET=1` when pulling (Xet resolver flakes on these repos).

---

## The image

GB10 is `sm_121a`, arm64, CUDA 13. There is no stock EXL3 wheel for it, so the image builds
`exllamav3` from source with `TORCH_CUDA_ARCH_LIST=12.1a` on top of the arm64 vLLM base.

```bash
docker build -t glm53-flash-sm121:local .
```

We build locally (`IMAGE=glm53-flash-sm121:local`, `SKIP_PULL=1`) rather than pulling the
GHCR image, so the sm_121a cubins match our exact driver/toolkit.

---

## Launch

1. `cp .env.example .env` and set node IPs, `WORKER_SSH`, and the RoCE NIC/GID for **your** fabric.
2. Head node runs `local/prod-start.sh` — it gates on `MemFree >= 90 GiB`, starts the worker over
   SSH `--headless`, then the head + API server.
3. First boot after a cache wipe does a **long cold JIT** (trellis kernels compile). This is slow,
   not dead — `READY_TIMEOUT=4800`. Watch the head log; workers should be at >0% GPU while compiling.

```bash
./local/prod-start.sh          # head; brings up worker over SSH
curl -s http://192.168.192.1:8000/v1/models   # -> GLM-5.3-Flash-EXL3
```

### Non-negotiables (learned the hard way, ours + upstream)
- **KV cache MUST be `fp8`** (`fp8_ds_mla`). Never bf16/NVFP4 KV with EXL3 here.
- **Never `--moe-backend marlin`** — that's the NVFP4 path; it corrupts EXL3.
- `--quantization exl3`, `--max-model-len 1000000`, `gmu 0.85` (0.87 crash-loops under the KV pin),
  `--max-num-seqs 4`, MNBT 3584, `--kv-cache-memory-bytes` pinned, `--no-async-scheduling`.
- Need ~180 GiB free/node before boot.

---

## Uncensored (optional)

`ABLIT=1` opts into an abliterated variant (transplant from the drowzeys ablit lineage). Off by default.

---

## Credits

This deploy would not exist without:

- **[Reederey87](https://github.com/Reederey87/glm53-flash-exl3-2x-dgx-spark)** — the GB10-hardened
  2-Spark EXL3 repo we followed end to end (Dockerfile, prod-start gating, RoCE rail guidance).
- **[MiaAI-Lab](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks)** — parallel 2-Spark
  recipe + the GHCR image + the weights mirror.
- **brandonmusic** — the `GLM-5.3-Flash-tr3-4bpw` EXL3 quant (ShapleyMCG License).
- **[turboderp](https://github.com/turboderp/exllamav3)** — ExLlamaV3 / the EXL3 format itself.
- **IncoAI** — the `GLM-5.3-Flash-DFlash2` speculative drafter.
- **zai-org** — GLM-5.3-Flash base model.
- **malaiwah**, **drowzeys** — surrounding tooling / abliteration lineage.

Our contribution: the symmetric rail-0/gid3 pin for a fabric where `f1` is dead, the local
sm_121a image build, and running the EXL3 lane co-resident with an NVFP4 TP2 lane on the same
4-node ring (endpoint preserved on Reddie). See `NOTES.md` + `BENCH.md`.
