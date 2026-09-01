# Deploy notes — our 2Wild bring-up (Bluey + Asusi)

## RoCE finding (the one that would have bitten us)
Upstream `.env.example` pins an **asymmetric** rail (head `enp1s0f1np1`/`rocep1s0f1`, worker
`f0`). On our Sparks that's backwards: **`rocep1s0f1` is DOWN on every node, `rocep1s0f0` is
ACTIVE**. So we pin **both head and worker to rail 0**:
- IF `enp1s0f0np0`, IB `rocep1s0f0`, `NCCL_IB_GID_INDEX=3`
- gid3 verified as `::ffff:192.168.192.1` (Bluey) / `::ffff:192.168.192.3` (Asusi)

This matches the fabric our NVFP4 TP4 lane already uses, so it's proven silicon.

## Image
Built locally on Bluey: `docker build -t glm53-flash-sm121:local .` → `IMAGE=glm53-flash-sm121:local`,
`SKIP_PULL=1`. Self-built so the sm_121a cubins match our driver exactly. (The kit's JIT-cache
wipe reads `IMAGE=` verbatim, so a self-built tag with no ghcr digest still wipes correctly.)

## Launch runbook (exact)
Weights land in `~/.cache/huggingface/hub/` on Bluey (head). Then, from Bluey:
```bash
# 1. free the page cache the 164G download parked (UMA box — MemFree gates the boot)
for n in "tonyspark1@192.168.192.1" "tonyspark3@192.168.192.3"; do
  ssh $n 'sync; echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null; free -g | awk "/^Mem/{print \"free \"\$4\"G\"}"'
done
# 2. launch (source .env so prod-start sees WORKER_SSH + fabric vars)
cd ~/glm53-flash-exl3-2x-dgx-spark
set -a; . ./.env; set +a
./local/prod-start.sh
# 3. poll (cold JIT is long — trellis kernels compile; READY_TIMEOUT=4800)
curl -s http://192.168.192.1:8000/v1/models   # -> GLM-5.3-Flash-EXL3
```

`prod-start.sh` does: `./start.sh stop` (idempotent) → wait for MemFree ≥ 90 GiB on **both**
nodes (worker checked over `WORKER_SSH`, timeout 600s, proceeds anyway after) → JIT-cache shape
guard (hashes DFLASH_TOKENS/IMAGE/EXTRA_ARGS/...; wipes Triton+TileLang on both nodes on change;
first boot always wipes) → `./start.sh start` (worker `--headless` over SSH, then head + API).

## Watch during boot
- All containers stay Up; **worker GPU > 0%** while compiling (0% + head looping = a mount/config
  fault, same failure class as the NVFP4 lane).
- First boot after a cache wipe = long cold JIT. Slow, not dead.

## Gotchas we hit + fixed (2026-09-01 first bring-up)
1. **`count_shards()` counts 0 on a symlinked HF cache (upstream bug).** `start.sh`'s
   `count_shards` uses `find "$repo/snapshots/$ref" -maxdepth 1 -type f -name '*.safetensors'`.
   A standard HF hub cache stores snapshot files as **symlinks** into `../../blobs/`, and
   `find -type f` does NOT match symlinks, so it returns 0 → the launch dies with
   `ERROR: download finished with 0 / 120 shards` even though all 120 shards are present and
   complete. **Fix: `find -L ...`** (follow symlinks; a symlink-to-regular-file then matches
   `-type f`, which also validates the blob exists). One-word change on the `find` in
   `count_shards`. Worth a PR back upstream — breaks on any normal HF cache.
2. **The worker needs the FULL model on disk (~164 GiB), not half.** vLLM TP reads slices out
   of every safetensors file, so `start.sh` rsyncs the whole cache to the worker. Asusi only had
   ~122 GiB free (a dead 182 GiB NVFP4-ablit copy from the retired GLM TP4 lane was squatting in
   `/var/tmp/models`). Cleared it → 303 GiB free. **Check worker free space >= model size before
   launch;** the kit only WARNs, it doesn't stop.
3. **`~/.cache/vllm-glm53-flash/` can be ROOT-OWNED — and it is NOT harmless.** A prior container
   wrote it as root. First symptom is the config-shape stamp failing with `Permission denied`
   (looks benign). The real bite: the launch then tries `mkdir ~/.cache/vllm-glm53-flash/tilelang`
   as the run user, fails, and **exits with NO containers** — a dead launch that looks like a
   silent no-op. **Fix on BOTH nodes before launching:**
   `sudo chown -R $USER:$USER ~/.cache/vllm-glm53-flash && mkdir -p ~/.cache/vllm-glm53-flash/{tilelang,triton}`.
4. **The kit binds the API to loopback only** — `start.sh` passes `--host 127.0.0.1` ("on purpose",
   security). It serves fine on-box (`curl 127.0.0.1:8000` works) but the fabric, the tailnet, the
   fleet, the coding monitor and any remote bench all get **connection refused**. On our private
   tailnet fleet every endpoint is `0.0.0.0`, so: `sed -i 's/--host 127.0.0.1/--host 0.0.0.0/g' start.sh`
   (two serve lines; the `http://127.0.0.1:${PORT}` health-check URLs are fine to leave). Needs a
   relaunch. Verify from OFF-box: `curl http://<tailnet-ip>:8000/v1/models`.
5. **It re-ships the image to the worker on EVERY launch.** `ensure_image()` compares an image key
   that never matches for a locally-built image (head = `tag@sha256:…`, worker after
   `docker save | ssh docker load` = RootFS layer list), so it always logs "will refresh worker"
   and pushes the ~21 GB image again. Harmless, ~1–2 min per launch. Fix later: key on `.Id` for
   local images, or skip when the worker already has the tag.
6. **UMA page cache starves the memory gate after big file moves.** Right after the 164 GiB rsync
   the worker showed **MemFree 1 GiB** (everything parked in page cache) and `prod-start` stalled at
   its ≥90 GiB gate. `sync; echo 3 | sudo tee /proc/sys/vm/drop_caches` on both nodes → 117 GiB
   free, gate passes on the next poll. Do this before every launch on these boxes.

Boot timing observed: cold first boot ≈ 12 min to serve (weights ~5 min + trellis JIT); a warm
relaunch is also ≈ 12 min (weight load dominates, JIT is cached). DFlash2 draft acceptance on the
EXL3 lane ≈ 40% (mean acceptance length ~3.8).

## Coexistence with the NVFP4 lane
NVFP4 GLM runs TP2 on **Reddie(.2 head)+Spark4(.4)**, master `192.168.192.2:29521`, serves
`glm-5.3-flash` on Reddie:8000. EXL3 runs TP2 on **Bluey(.1)+Asusi(.3)**, serves
`GLM-5.3-Flash-EXL3` on Bluey:8000. Different head nodes → the shared master port is fine.
Endpoint for the fleet is unchanged (still Reddie:8000).

## After serve — status (2026-09-01)
- [x] thinking off honored (`chat_template_kwargs {"enable_thinking": false}` → `reasoning_content` empty)
- [x] bench EXL3 vs NVFP4 → BENCH.md — isolated, parallel, c1×5 / c6×3 / prefill×3: **EXL3 wins every metric**
      (61.1 / 122 / 3,233 vs 35.9 / 66 / 564), ±0.5% spread vs ±16%
- [x] quality diff, probe 1 (top-k O(n log k) + bat-and-ball): **tie** — both correct, diff cosmetic
- [ ] harder quality probes still open: multi-file refactor, tool-call arg validity, long-ctx recall (200K+)
- [ ] vision red-probe / uncensored check (ABLIT not enabled on this lane)
- [ ] prod default = Tony's call (data: EXL3 faster on every axis, quality tied on probe 1)

**Bench isolation rule (learned the hard way):** Hermes supervisors `neo`, `oc-donnie`, `oc-draco` default
to `glm-5.3-flash` → Reddie:8000. Before benching: move them to the 27B, park the spark-flash relay on
`qwen27b`, pause the `:7900` latency monitor (real probe completions), then prove it from each head's
access log by request COUNT (the supervisors share the bench client's IP).

## Publishing checklist (before flipping this repo public)
Intent: this goes public eventually (deploy notes people can't find elsewhere). Keep it clean.
- [ ] No secrets anywhere in tree OR history (only `.env.example` ships; real `.env` gitignored).
- [ ] Genericize internal identifiers in `.env.example` to placeholders (node usernames, LAN IPs) —
      keep one concrete example in a comment so it's still copy-pasteable.
- [ ] Add a LICENSE for our own content; add a NOTICE / CREDITS honoring upstream terms
      (Reederey87 + MiaAI-Lab carry LICENSE/NOTICE; brandonmusic quant = ShapleyMCG; turboderp exllamav3; IncoAI DFlash2; zai-org GLM).
- [ ] We reference upstream repos + HF weights — we do NOT redistribute their weights or their
      Dockerfile/start.sh in our repo. If we ever vendor their scripts, comply with their license first.
- [ ] Final read-through of every committed file + `git log -p` for anything internal-only.
- [ ] Tony's explicit go before the private→public flip.
