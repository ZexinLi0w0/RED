#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${REPOSITORY_ROOT}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ "${SKIP_GIT_PULL:-0}" != "1" ]]; then
  git pull --ff-only
fi
"${PYTHON_BIN}" experiments/parameter_sensitivity.py run \
  --resume \
  "$@"
