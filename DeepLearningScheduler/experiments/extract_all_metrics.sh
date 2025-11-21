#!/usr/bin/env bash
# Extract metrics from all new scenarios log files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXTRACT_SCRIPT="${SCRIPT_DIR}/extract_new_scenarios_metrics.py"

# Default log files location
LOG_DIR="${ROOT_DIR}"
OUTPUT_DIR="${ROOT_DIR}"

# Process all log files
for device in mac nano agx; do
    log_file="${LOG_DIR}/${device}_new_scenarios.log"
    
    if [[ ! -f "${log_file}" ]]; then
        echo "Warning: Log file not found: ${log_file}" >&2
        continue
    fi
    
    echo "Processing ${device} log file..."
    python3 "${EXTRACT_SCRIPT}" "${log_file}" --format csv --output "${OUTPUT_DIR}/${device}_new_scenarios_metrics.csv"
    echo "  -> Generated ${device}_new_scenarios_metrics.csv"
done

echo ""
echo "All metrics extracted successfully!"
echo "CSV files saved in: ${OUTPUT_DIR}"

