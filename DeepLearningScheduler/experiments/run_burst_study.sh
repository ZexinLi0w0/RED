#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${REPOSITORY_ROOT}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
OUTPUT_ROOT="${BURST_OUTPUT_ROOT:-taskdata/major_revision_burst_mac_mps_v3}"
REPETITIONS=1
EXPLICIT_SEEDS=""

usage() {
  printf '%s\n' \
    "Usage: $0 [--repetitions N] [--seeds S1,S2,...]" \
    "" \
    "Runs each Burst condition and method once by default." \
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

PLAN_ARGUMENTS=(--output-root "${OUTPUT_ROOT}" --repetitions "${REPETITIONS}")
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
