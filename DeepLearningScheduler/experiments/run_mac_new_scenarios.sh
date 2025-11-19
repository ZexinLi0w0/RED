#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler"
PROJECT_ENTRY="${ROOT}/main.py"
CONFIG_FILE="${ROOT}/handler-config.json"
TASK_DIR="${ROOT}/TaskConfigs/simo/new_scenarios"
LOG_FILE="${ROOT}/mac_new_scenarios.log"
DEVICE_ID="mac"
DEVICE_LABEL="Mac"
DEADLINE_PROFILE="loose"

SCENARIOS=("urban_navigation" "emergency_obstacle_avoidance" "night_driving")
SCENARIO_LABELS=("Urban navigation" "Emergency obstacle avoidance" "Night driving")
APPROACHES=("baseline" "feedback" "fine-grained" "feedback-fine-grained")
APPROACH_LABELS=("Baseline" "RED-IDA" "RED-FG" "RED")

cd "${ROOT}"
: > "${LOG_FILE}"
echo "Writing Mac experiment outputs to ${LOG_FILE}"

run_case() {
  local scenario="$1"
  local scenario_label="$2"
  local approach="$3"
  local approach_label="$4"
  local task_file="${TASK_DIR}/${DEVICE_ID}_${DEADLINE_PROFILE}_${scenario}.json"

  echo "# ${DEVICE_LABEL}, ${scenario_label}, ${approach_label}" >> "${LOG_FILE}"
  python3 "${PROJECT_ENTRY}" \
    --config "${CONFIG_FILE}" \
    --task "${task_file}" \
    --approach "${approach}" >> "${LOG_FILE}" 2>&1
  echo >> "${LOG_FILE}"
}

for idx in "${!SCENARIOS[@]}"; do
  scenario="${SCENARIOS[$idx]}"
  scenario_label="${SCENARIO_LABELS[$idx]}"
  for jdx in "${!APPROACHES[@]}"; do
    approach="${APPROACHES[$jdx]}"
    approach_label="${APPROACH_LABELS[$jdx]}"
    run_case "${scenario}" "${scenario_label}" "${approach}" "${approach_label}"
  done
done

