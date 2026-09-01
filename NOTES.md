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

## Coexistence with the NVFP4 lane
NVFP4 GLM runs TP2 on **Reddie(.2 head)+Spark4(.4)**, master `192.168.192.2:29521`, serves
`glm-5.3-flash` on Reddie:8000. EXL3 runs TP2 on **Bluey(.1)+Asusi(.3)**, serves
`GLM-5.3-Flash-EXL3` on Bluey:8000. Different head nodes → the shared master port is fine.
Endpoint for the fleet is unchanged (still Reddie:8000).

## TODO after serve
- [ ] smoke: red-probe vision (if applicable), thinking off, uncensored check
- [ ] bench EXL3 vs NVFP4 → BENCH.md (median tok/s non-stream, single + c4 agg)
- [ ] quality diff on hard prompts (code / reasoning / tool-call / long-ctx)
- [ ] decide prod default (quality vs speed) with Tony
