# Parameter-sensitivity study

This experiment implements the revision's two independent full-factorial
parameter blocks. It evaluates the complete MERIS method
(`feedback-fine-grained`) at 47 settings. Each setting runs once by default:

- moving-average window: `1, 4, 8, 16`;
- release-time skew threshold: `0, 50, 100, 150, 200` milliseconds;
- GPU threshold: `70, 80, 90` percent;
- ready-queue threshold: `4, 8, 16`;
- sustained-overload persistence window: `1, 3, 5` scheduler ticks.

The refinement block is the 4 x 5 Cartesian product of moving-average window
and release-time skew threshold (20 settings) with burst generation and Burst
Management disabled. The Burst Management block is the 3 x 3 x 3 Cartesian
product of GPU threshold, ready-queue threshold, and persistence window (27
settings), with the refinement parameters fixed at `8` and `100` milliseconds.

The default frozen workload is
`TaskConfigs/simo/parameter_sensitivity/agx_high_load.json`. It uses AGX Orin
profiles and fixed 0/50/100/150/200 millisecond predicted release skews among
compatible MIMONet requests. The runner sets `BurstTaskRatio=0` in refinement
configs. In Burst Management configs it retains the 100 percent burst and marks
the offered nodes non-partitionable so merging cannot hide queue backlog from
the `Q_max` grid.

Override `--base-task-config` if a replacement frozen AGX workload is selected.

## One-command Jetson run

On the AGX Orin server, activate the `schedule` environment and run:

```bash
cd /experiment/zexin/ATC23/DeepLearningScheduler
conda activate schedule
./experiments/run_parameter_sensitivity.sh
```

The wrapper runs `git pull --ff-only` before the experiment, refuses a dirty
source tree, generates all parameter configs, executes 47 isolated runs by
default, resumes already completed runs, and creates the paper-table data after
validating every artifact. To use another Conda environment, replace `schedule`
with its name; the wrapper resolves `python3` from the active environment. A
failed or interrupted run is retried on the next invocation; its old manifest
and logs are retained with an `.attemptN` suffix.

The default command executes 47 runs. To repeat every setting, pass a positive
integer:

```bash
./experiments/run_parameter_sensitivity.sh --repetitions 5
```

This example executes 235 runs. The runner generates deterministic seeds
automatically. Advanced use can provide explicit seeds with `--seeds 7,11,19`;
an explicit seed list overrides `--repetitions`.

Useful overrides:

```bash
# Select a frozen workload and a different output directory.
./experiments/run_parameter_sensitivity.sh \
  --base-task-config TaskConfigs/simo/parameter_sensitivity/agx_frozen.json \
  --output-root taskdata/parameter_sensitivity/agx_frozen_v2

# Continue all remaining points even if one run fails.
./experiments/run_parameter_sensitivity.sh --keep-going
```

For a local plan-only check without pulling or requiring PyTorch:

```bash
SKIP_GIT_PULL=1 PYTHON_BIN=.venv/bin/python \
  ./experiments/run_parameter_sensitivity.sh \
  --dry-run --allow-dirty --torch-device cpu
```

## Artifacts and table values

The default output directory is
`taskdata/parameter_sensitivity/agx_high_load_v1/`:

- `study_plan.json`: immutable grid, seeds, defaults, base-config hashes, and run count;
- `generated_configs/`: explicit task and burst config for each table row;
- `runs/<run-id>/manifest.json`: commit, source status, host, power mode, seed,
  commands, hashes, and all five executed sensitivity-parameter values;
- `runs/<run-id>/stdout.log`: complete controller and handler log;
- `runs/<run-id>/summary.json`: validated latency, Deadline Missing Rate, QoE,
  moving-average trace, release-time skew threshold, and burst-controller statistics;
- `report/parameter_sensitivity_runs.csv`: one row per repetition;
- `report/parameter_sensitivity_report.json`: mean, sample standard deviation,
  range, and 95 percent confidence interval for every metric and table point;
- `report/parameter_sensitivity_table.csv`: the 47 values ready to paste
  into the revision table;
- `report/parameter_sensitivity_table_rows.tex`: generated LaTeX table rows.

With the default single run, the table CSV and LaTeX rows use that run directly.
When `--repetitions N` or multiple explicit seeds are supplied, they use the
arithmetic mean of the `N` runs. Summarization fails instead of silently
producing a table if a run is missing, duplicated, has an unexpected seed, uses
the wrong parameter values, contains a non-finite metric, or fails a
hash/provenance check.

To regenerate the table files without rerunning inference:

```bash
python3 experiments/parameter_sensitivity.py summarize \
  --output-root taskdata/parameter_sensitivity/agx_high_load_v1
```
