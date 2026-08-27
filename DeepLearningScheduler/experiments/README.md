# New Scenarios Metrics Extraction

## Burst experiment

The formal M3 Max/MPS Burst study has a one-command runner. From the repository
root, initialize Conda and run:

```zsh
eval "$(/Users/rentao/miniconda3/bin/conda shell.zsh hook)"
conda activate schedule
./experiments/run_burst_study.sh
```

The wrapper performs planning, execution, validation, and summarization. It runs
each of the 15 distinct Burst condition/method cells once by default and resumes
runs whose manifests are already complete. The default Mac/MPS TaskConfig is
`TaskConfigs/simo/burst/mac_mps_proactive_drop_v2.json`. Artifact validation
requires no ProactiveDrop activity in the 0% MERIS control and requires both an
overload activation and proactive-drop records in every 50%/100% MERIS cell. Use
`--repetitions N` to repeat each cell `N` times; for example:

```zsh
./experiments/run_burst_study.sh --repetitions 5
```

Raw artifacts are stored under `taskdata/major_revision_burst_mac_mps_v3/`.
Set `BURST_OUTPUT_ROOT` to override that path. The workload semantics and output
files are documented in
[`../BURST_TASK_IMPLEMENTATION.md`](../BURST_TASK_IMPLEMENTATION.md).

The revision's automated parameter-sensitivity experiment is documented in
[`PARAMETER_SENSITIVITY.md`](PARAMETER_SENSITIVITY.md). Its one-command runner
generates the complete 18-point AGX Orin matrix and writes CSV, JSON, and LaTeX
values for the paper table. Each point runs once by default.

On the Jetson server, run:

```bash
cd /experiment/zexin/ATC23/DeepLearningScheduler
conda activate schedule
./experiments/run_parameter_sensitivity.sh
```

Replace `schedule` with another environment name when needed. The wrapper uses
`python3` from the active environment, pulls the latest commit, resumes completed
runs, and creates the validated table artifacts automatically.

Use `./experiments/run_parameter_sensitivity.sh --repetitions N` to run every
parameter point `N` times. For example, `--repetitions 5` creates 90 runs.

This directory contains scripts for extracting and analyzing metrics from new scenarios experiment log files.

## Scripts

### 1. `extract_new_scenarios_metrics.py`

Extracts three key metrics from log files:
- **Missing deadline rate**: Percentage of tasks that missed their deadlines
- **Average finished time**: Average time taken to complete tasks
- **QoE score**: Quality of Experience score

**Usage:**
```bash
# Extract metrics and display as table
python3 extract_new_scenarios_metrics.py <log_file> --format table

# Extract metrics and save to CSV
python3 extract_new_scenarios_metrics.py <log_file> --format csv

# Extract metrics and do both
python3 extract_new_scenarios_metrics.py <log_file> --format both

# Specify custom output file
python3 extract_new_scenarios_metrics.py <log_file> --output custom_name.csv
```

**Examples:**
```bash
# Extract from Mac log
python3 extract_new_scenarios_metrics.py ../taskdata/new_scenarios/mac_new_scenarios.log --format both

# Extract from Nano log (on remote server)
python3 extract_new_scenarios_metrics.py ../taskdata/new_scenarios/nano_new_scenarios.log --format csv
```

### 2. `extract_all_metrics.sh`

Batch script to extract metrics from all device log files at once.

**Usage:**
```bash
./extract_all_metrics.sh
```

This will:
- Process `taskdata/new_scenarios/mac_new_scenarios.log`
- Process `taskdata/new_scenarios/nano_new_scenarios.log`
- Process `taskdata/new_scenarios/agx_new_scenarios.log`
- Generate corresponding `*_new_scenarios_metrics.csv` files in `taskdata/new_scenarios/`

### 3. `combine_metrics.py`

Combines metrics from multiple device CSV files into a single summary file.

**Usage:**
```bash
# Auto-detect and combine all metrics CSV files in current directory
python3 combine_metrics.py

# Combine specific CSV files
python3 combine_metrics.py --csv-files mac_metrics.csv nano_metrics.csv agx_metrics.csv

# Specify output file
python3 combine_metrics.py --output combined_results.csv

# Search in specific directory
python3 combine_metrics.py --dir /path/to/logs
```

## Workflow Example

1. **Run experiments** (on respective devices):
   ```bash
   # On Mac
   ./run_mac_new_scenarios.sh
   
   # On Nano (via SSH)
   ./run_nano_new_scenarios.sh
   
   # On AGX (via SSH)
   ./run_agx_new_scenarios.sh
   ```

2. **Extract metrics** (on each device or copy logs to one machine):
   ```bash
   # Option A: Extract individually
   python3 extract_new_scenarios_metrics.py taskdata/new_scenarios/mac_new_scenarios.log --format csv
   python3 extract_new_scenarios_metrics.py taskdata/new_scenarios/nano_new_scenarios.log --format csv
   python3 extract_new_scenarios_metrics.py taskdata/new_scenarios/agx_new_scenarios.log --format csv
   
   # Option B: Use batch script
   ./extract_all_metrics.sh
   ```

3. **Combine results**:
   ```bash
   python3 combine_metrics.py --output all_devices_metrics.csv
   ```

4. **Analyze**:
   - Open the CSV file in Excel, Google Sheets, or Python pandas
   - Compare metrics across devices, scenarios, deadlines, and approaches

## Output Format

The CSV files contain the following columns:

- `device`: Device name (Mac, Nano, AGX)
- `scenario`: Scenario name (Urban navigation, Emergency obstacle avoidance, Night driving)
- `deadline`: Deadline type (Tight, Loose)
- `approach`: Scheduling approach (Baseline, MERIS-IDA, MERIS-FG, MERIS)
- `missing_deadline_rate`: Missing deadline rate (0.0 to 1.0)
- `avg_finished_time`: Average finished time in seconds
- `qoe_score`: QoE score (typically 0.0 to 1.0)

## Notes

- The extraction script automatically handles ANSI color codes in log files
- Missing metrics are marked as 'N/A' in the output
- Each experiment run should produce 24 results (3 scenarios × 2 deadlines × 4 approaches)
