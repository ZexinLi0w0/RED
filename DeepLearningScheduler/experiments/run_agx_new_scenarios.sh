#!/usr/bin/env bash
set -euo pipefail

ROOT="/experiment/zexin/ATC23/DeepLearningScheduler"
PROJECT_ENTRY="${ROOT}/main.py"
CONFIG_FILE="${ROOT}/handler-config.json"
TASK_DIR="${ROOT}/TaskConfigs/simo/new_scenarios"
LOG_FILE="${ROOT}/taskdata/new_scenarios/agx_new_scenarios.log"
DEVICE_ID="agx"
DEVICE_LABEL="AGX"
DEADLINE_PROFILES=("loose")
DEADLINE_LABELS=("Loose")

SCENARIOS=("urban_navigation" "emergency_obstacle_avoidance" "night_driving")
SCENARIO_LABELS=("Urban navigation" "Emergency obstacle avoidance" "Night driving")
APPROACHES=("baseline" "feedback" "fine-grained" "feedback-fine-grained")
APPROACH_LABELS=("Baseline" "RED-IDA" "RED-FG" "RED")

cd "${ROOT}"
mkdir -p "$(dirname "${LOG_FILE}")"
: > "${LOG_FILE}"
echo "Writing AGX experiment outputs to ${LOG_FILE}"

run_case() {
  local scenario="$1"
  local scenario_label="$2"
  local deadline_profile="$3"
  local deadline_label="$4"
  local approach="$5"
  local approach_label="$6"
  local task_file="${TASK_DIR}/${DEVICE_ID}_${deadline_profile}_${scenario}.json"

  # Build the command string
  local cmd="python3 ${PROJECT_ENTRY} --config ${CONFIG_FILE} --task ${task_file} --approach ${approach}"
  
  # Output to terminal and log
  echo "# ${DEVICE_LABEL}, ${scenario_label}, ${deadline_label}, ${approach_label}" | tee -a "${LOG_FILE}"
  echo "Command: ${cmd}" | tee -a "${LOG_FILE}"
  
  # Execute the command
  python3 "${PROJECT_ENTRY}" \
    --config "${CONFIG_FILE}" \
    --task "${task_file}" \
    --approach "${approach}" >> "${LOG_FILE}" 2>&1
  echo >> "${LOG_FILE}"

  echo "Sleeping 3 seconds before next experiment..." | tee -a "${LOG_FILE}"
  sleep 3
}

for idx in "${!SCENARIOS[@]}"; do
  scenario="${SCENARIOS[$idx]}"
  scenario_label="${SCENARIO_LABELS[$idx]}"
  for kdx in "${!DEADLINE_PROFILES[@]}"; do
    deadline_profile="${DEADLINE_PROFILES[$kdx]}"
    deadline_label="${DEADLINE_LABELS[$kdx]}"
    for jdx in "${!APPROACHES[@]}"; do
      approach="${APPROACHES[$jdx]}"
      approach_label="${APPROACH_LABELS[$jdx]}"
      run_case "${scenario}" "${scenario_label}" "${deadline_profile}" "${deadline_label}" "${approach}" "${approach_label}"
    done
  done
done

