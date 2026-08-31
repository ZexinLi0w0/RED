#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${REPOSITORY_ROOT}"
PYTHON_BIN="${PYTHON_BIN:-python}"
OUTPUT_ROOT="${BURST_OUTPUT_ROOT:-taskdata/major_revision_burst_nano1_cuda_v3}"
REPETITIONS=1
EXPLICIT_SEEDS=""

usage() {
  printf '%s\n' \
    "Usage: $0 [--repetitions N] [--seeds S1,S2,...]" \
    "" \
    "Runs the profile-corrected Nano1 Burst matrix once per cell by default." \
    "--seeds overrides --repetitions for advanced reproducibility."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repetitions)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      REPETITIONS="$2"
      shift 2
      ;;
    --seeds)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      EXPLICIT_SEEDS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$(basename "${CONDA_PREFIX:-missing}")" != "schedule" ]]; then
  printf '%s\n' \
    "Nano1 formal experiments must run in the schedule Conda environment." >&2
  exit 1
fi

# The remote-execution pipeline requires a pull immediately before every run.
git pull --ff-only

"${PYTHON_BIN}" -c \
  'import torch; assert torch.cuda.is_available(), "CUDA is unavailable"'

PLAN_ARGUMENTS=(
  --base-task-config TaskConfigs/simo/burst/nano1_cuda_proactive_drop_v2.json
  --output-root "${OUTPUT_ROOT}"
  --repetitions "${REPETITIONS}"
  --burst-start-seconds 0
  --transient-duration-seconds 3
  --release-horizon-seconds 10
  --gpu-threshold 100
  --queue-threshold 6
  --persistence-window 1
  --device nano1
  --platform-label "Jetson Orin Nano"
  --power-mode "15W; jetson_clocks"
  --torch-device cuda
  --no-require-proactive-drop-for-meris-burst
)
if [[ -n "${EXPLICIT_SEEDS}" ]]; then
  PLAN_ARGUMENTS+=(--seeds "${EXPLICIT_SEEDS}")
fi

"${PYTHON_BIN}" experiments/burst_study.py plan \
  "${PLAN_ARGUMENTS[@]}"
"${PYTHON_BIN}" experiments/burst_study.py run \
  --output-root "${OUTPUT_ROOT}" \
  --python "${PYTHON_BIN}" \
  --resume \
  --keep-going
"${PYTHON_BIN}" experiments/burst_study.py summarize \
  --output-root "${OUTPUT_ROOT}"
