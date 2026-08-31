#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPOSITORY_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python}"
OUTPUT_ROOT="${BURST_OUTPUT_ROOT:-taskdata/major_revision_burst_agx_orin_cuda_v3}"
SEEDS="${BURST_SEEDS:-101,202,303,404,505}"

if [[ "$(basename "${CONDA_PREFIX:-missing}")" != "schedule" ]]; then
  printf '%s\n' \
    "AGX Orin formal experiments must run in the schedule Conda environment." >&2
  exit 1
fi

git pull --ff-only
"${PYTHON_BIN}" -c \
  'import torch; assert torch.cuda.is_available(), "CUDA is unavailable"'

git pull --ff-only
"${PYTHON_BIN}" experiments/burst_study.py plan \
  --base-task-config TaskConfigs/simo/burst/agx_orin_cuda_burst_v2.json \
  --output-root "${OUTPUT_ROOT}" \
  --seeds "${SEEDS}" \
  --burst-start-seconds 0 \
  --transient-duration-seconds 0.65 \
  --release-horizon-seconds 1.5 \
  --gpu-threshold 100 \
  --queue-threshold 8 \
  --queue-recovery-threshold 6 \
  --persistence-window 3 \
  --scheduler-tick-seconds 0.005 \
  --device agx_orin \
  --platform-label "AGX Orin" \
  --power-mode MAXN \
  --torch-device cuda

git pull --ff-only
"${PYTHON_BIN}" experiments/burst_study.py run \
  --output-root "${OUTPUT_ROOT}" \
  --python "${PYTHON_BIN}" \
  --cooldown-seconds 1 \
  --resume \
  --keep-going

git pull --ff-only
"${PYTHON_BIN}" experiments/burst_study.py summarize \
  --output-root "${OUTPUT_ROOT}"

git pull --ff-only
"${PYTHON_BIN}" experiments/agx_orin_burst.py \
  "${OUTPUT_ROOT}" \
  --seeds "${SEEDS}"
