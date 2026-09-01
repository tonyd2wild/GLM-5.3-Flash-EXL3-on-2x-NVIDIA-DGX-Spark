#!/usr/bin/env bash
# run_full_test.sh <base_url> <served_model> <label-word>   e.g.  run_full_test.sh http://100.92.77.51:8000 GLM-5.3-Flash-EXL3 exl3
# The whole test for one lane, isolated: warm -> sweep c1..c6 -> detailed c1x5/c6x3/prefill x3 -> quality probe. Run both lanes in parallel.
set -uo pipefail
BASE="$1"; MODEL="$2"; L="$3"; cd "$(dirname "$0")/.."
echo "=== [$L] sweep c1-c6 ==="; python3 tools/bench_sweep.py "$BASE" "$MODEL" "$L" --rounds 3 --max-c 6 --out "results/sweep_${L}.json"
echo "=== [$L] detailed c1x5 / c6x3 / prefill x3 ==="; python3 tools/bench_detailed.py "$BASE" "$MODEL" "$L" --c1 5 --c6 3 --prefill 3 | tail -6
echo "=== [$L] quality probe ==="; python3 tools/quality_probe.py "$BASE" "$MODEL" "results/quality_${L}.txt" | head -2
echo "=== [$L] done $(date '+%H:%M:%S') ==="
