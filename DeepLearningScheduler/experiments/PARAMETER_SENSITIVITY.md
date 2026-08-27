# Parameter-sensitivity study

This experiment implements the revision's one-factor-at-a-time study on one
representative high-load AGX Orin workload. It evaluates the complete RED method
(`feedback-fine-grained`) at 18 table settings with five predeclared repetitions
per setting:

- moving-average window: `1, 4, 8, 16`;
- release-time skew threshold: `0, 50, 100, 150, 200` milliseconds;
- GPU threshold: `70, 80, 90` percent;
- ready-queue threshold: `4, 8, 16`;
- sustained-overload persistence window: `1, 3, 5` scheduler ticks.

The fixed defaults are `8`, `100` milliseconds, `90` percent, `8`, and `3`
ticks. Every generated point starts from these defaults and changes only its
named parameter. The default frozen workload is
`TaskConfigs/simo/parameter_sensitivity/agx_high_load.json`. It uses AGX Orin
profiles, a 100 percent burst injection so burst-controller parameters are
observable, and fixed 0/50/100/150/200 millisecond predicted release skews among
compatible MIMONet requests so the release-time skew threshold changes the executed graph.
Override `--base-task-config` if a replacement frozen AGX workload is selected.

## One-command Jetson run

On the AGX Orin server:

```bash
cd /experiment/zexin/ATC23/DeepLearningScheduler
./experiments/run_parameter_sensitivity.sh
```

The wrapper runs `git pull --ff-only` before the experiment, refuses a dirty
source tree, generates all parameter configs, executes 90 isolated runs, resumes
already completed runs, and creates the paper-table data after validating every
artifact. A failed or interrupted run is retried on the next invocation; its old
manifest and logs are retained with an `.attemptN` suffix.

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

- `study_plan.json`: immutable grid, seeds, defaults, base-config hashes, and 90-run count;
- `generated_configs/`: explicit task and burst config for each table row;
- `runs/<run-id>/manifest.json`: commit, source status, host, power mode, seed,
  commands, hashes, and all five executed parameter values;
- `runs/<run-id>/stdout.log`: complete controller and handler log;
- `runs/<run-id>/summary.json`: validated latency, Deadline Missing Rate, QoE,
  moving-average trace, release-time skew threshold, and burst-controller statistics;
- `report/parameter_sensitivity_runs.csv`: one row per repetition;
- `report/parameter_sensitivity_report.json`: mean, sample standard deviation,
  range, and 95 percent confidence interval for every metric and table point;
- `report/parameter_sensitivity_table.csv`: the 18 mean values ready to paste
  into the revision table;
- `report/parameter_sensitivity_table_rows.tex`: generated LaTeX table rows.

The table CSV and LaTeX rows use the arithmetic mean of the five predeclared
repetitions. Summarization fails instead of silently producing a table if a run
is missing, duplicated, has an unexpected seed, uses the wrong parameter values,
contains a non-finite metric, or fails a hash/provenance check.

To regenerate the table files without rerunning inference:

```bash
python3 experiments/parameter_sensitivity.py summarize \
  --output-root taskdata/parameter_sensitivity/agx_high_load_v1
```
