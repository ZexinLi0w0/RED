#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${REPOSITORY_ROOT}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
OUTPUT_ROOT="${BURST_OUTPUT_ROOT:-taskdata/major_revision_burst_mac_mps_v2}"

"${PYTHON_BIN}" experiments/burst_study.py plan \
  --output-root "${OUTPUT_ROOT}"
"${PYTHON_BIN}" experiments/burst_study.py run \
  --output-root "${OUTPUT_ROOT}" \
  --python "${PYTHON_BIN}" \
  --resume \
  --keep-going
"${PYTHON_BIN}" experiments/burst_study.py summarize \
  --output-root "${OUTPUT_ROOT}"
