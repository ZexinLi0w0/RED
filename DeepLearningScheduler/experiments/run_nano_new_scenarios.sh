#!/usr/bin/env bash
set -uo pipefail
# Note: We don't use 'set -e' because we want to continue even if individual experiments fail

ROOT="/home/zexin/ATC23/DeepLearningScheduler"
PROJECT_ENTRY="${ROOT}/main.py"
CONFIG_FILE="${ROOT}/handler-config.json"
TASK_DIR="${ROOT}/TaskConfigs/simo/new_scenarios"
LOG_FILE="${ROOT}/taskdata/new_scenarios/nano_new_scenarios.log"
DEVICE_ID="nano"
DEVICE_LABEL="Nano"
DEADLINE_PROFILES=("tight" "loose")
DEADLINE_LABELS=("Tight" "Loose")

SCENARIOS=("urban_navigation" "emergency_obstacle_avoidance" "night_driving")
SCENARIO_LABELS=("Urban navigation" "Emergency obstacle avoidance" "Night driving")
APPROACHES=("baseline" "feedback" "fine-grained" "feedback-fine-grained")
APPROACH_LABELS=("Baseline" "RED-IDA" "RED-FG" "RED")

cd "${ROOT}"
mkdir -p "$(dirname "${LOG_FILE}")"
: > "${LOG_FILE}"
echo "Writing Nano experiment outputs to ${LOG_FILE}"
echo "Total experiments to run: $((${#SCENARIOS[@]} * ${#DEADLINE_PROFILES[@]} * ${#APPROACHES[@]}))" >> "${LOG_FILE}"
echo "Scenarios: ${SCENARIOS[@]}" >> "${LOG_FILE}"
echo "Deadline profiles: ${DEADLINE_PROFILES[@]}" >> "${LOG_FILE}"
echo "Approaches: ${APPROACHES[@]}" >> "${LOG_FILE}"
echo >> "${LOG_FILE}"

run_case() {
  local scenario="$1"
  local scenario_label="$2"
  local deadline_profile="$3"
  local deadline_label="$4"
  local approach="$5"
  local approach_label="$6"
  local task_file="${TASK_DIR}/${DEVICE_ID}_${deadline_profile}_${scenario}.json"

  # Check if task file exists
  if [[ ! -f "${task_file}" ]]; then
    echo "ERROR: Task file not found: ${task_file}" >> "${LOG_FILE}"
    echo "Skipping experiment: ${scenario_label}, ${deadline_label}, ${approach_label}" >> "${LOG_FILE}"
    echo >> "${LOG_FILE}"
    return 1
  fi

  echo "# ${DEVICE_LABEL}, ${scenario_label}, ${deadline_label}, ${approach_label}" >> "${LOG_FILE}"
  echo "Running: ${task_file} with approach ${approach}" >> "${LOG_FILE}"
  python3 "${PROJECT_ENTRY}" \
    --config "${CONFIG_FILE}" \
    --task "${task_file}" \
    --approach "${approach}" >> "${LOG_FILE}" 2>&1
  local exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    echo "ERROR: Experiment failed with exit code ${exit_code}" >> "${LOG_FILE}"
  fi
  echo >> "${LOG_FILE}"
  return $exit_code
}

experiment_count=0
failed_count=0
for idx in "${!SCENARIOS[@]}"; do
  scenario="${SCENARIOS[$idx]}"
  scenario_label="${SCENARIO_LABELS[$idx]}"
  for kdx in "${!DEADLINE_PROFILES[@]}"; do
    deadline_profile="${DEADLINE_PROFILES[$kdx]}"
    deadline_label="${DEADLINE_LABELS[$kdx]}"
    for jdx in "${!APPROACHES[@]}"; do
      approach="${APPROACHES[$jdx]}"
      approach_label="${APPROACH_LABELS[$jdx]}"
      experiment_count=$((experiment_count + 1))
      echo "[${experiment_count}/24] Running: ${scenario_label}, ${deadline_label}, ${approach_label}" >> "${LOG_FILE}"
      # Continue even if run_case fails
      if ! run_case "${scenario}" "${scenario_label}" "${deadline_profile}" "${deadline_label}" "${approach}" "${approach_label}"; then
        failed_count=$((failed_count + 1))
        echo "WARNING: Experiment failed, continuing with next experiment..." >> "${LOG_FILE}"
      fi
    done
  done
done
echo "All experiments completed. Total: ${experiment_count}, Failed: ${failed_count}" >> "${LOG_FILE}"

