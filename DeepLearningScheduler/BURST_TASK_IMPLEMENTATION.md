# Burst Workload and Management Implementation

## Semantics

The experiment code supports two distinct workload regimes:

- **Transient Burst** duplicates eligible complete DAG releases inside a finite
  interval `[burst_start_seconds, burst_start_seconds +
  transient_duration_seconds)`.
- **Sustained Burst** duplicates eligible complete DAG releases from
  `burst_start_seconds` through `release_horizon_seconds`.

`BurstTaskRatio` is an offered-work definition, not a utilization label. At
100%, the generator adds one complete DAG release for every eligible base DAG
release. At 50%, it adds one complete DAG for a deterministic, temporally
distributed half of the eligible releases. A clone preserves the source release
times, deadlines, priorities, dependencies, and task-level `DropThreshold`, but
receives a unique DAG-period identity so its dependency state is independent.

Every scheduling method receives the same augmented offered stream. EDF
(`baseline`) and LLF-DAG (`llf-dag`) do not use RED's active overload
management. Only RED (`feedback-fine-grained`) starts system monitoring and may
invoke `ProactiveDrop`.

## Overload and ProactiveDrop

The controller detects raw overload when either:

- GPU utilization exceeds `gpu_threshold`; or
- the number of already-released waiting tasks exceeds `queue_threshold`.

Future releases are not counted as active backlog and cannot be dropped before
their release time. Raw overload must persist for `persistence_window`
consecutive scheduler ticks before active management begins.

For an already-released task, RED computes

```text
C_i = 1 - S_i / D_i
```

where `D_i` is the relative intermediate-deadline duration and `S_i` is the
current slack. A task is dropped only when its score is below its task-level
`DropThreshold`, or below the global `drop_threshold` when no task-level value
is supplied. Retained tasks preserve the underlying scheduler order.

Run summaries record the full workload definition, added DAG/node counts,
overload activations, and one JSON-safe decision record per proactive drop.

## Burst Configuration

Transient example:

```json
{
  "burst_enabled": true,
  "burst_regime": "transient",
  "burst_start_seconds": 0.36,
  "transient_duration_seconds": 0.6,
  "release_horizon_seconds": 2.4,
  "gpu_threshold": 100.0,
  "queue_threshold": 10,
  "persistence_window": 3,
  "drop_threshold": 0.5,
  "monitoring_interval": 0.05,
  "scheduler_tick_seconds": 0.005
}
```

For a Sustained Burst, set `burst_regime` to `sustained` and omit
`transient_duration_seconds`.

The task configuration separately supplies `BurstTaskRatio` and may supply a
`DropThreshold` for each DAG node.

## Major-revision M3 Max Study

The reproducible runner is `experiments/burst_study.py`. It generates a common
0% control plus Transient and Sustained 50%/100% conditions, runs EDF, LLF-DAG,
and RED once per condition by default, and validates identical offered-stream
hashes across methods.

The default base workload is
`TaskConfigs/simo/burst/mac_mps_proactive_drop_v2.json`. It uses the measured
M3 Max/MPS timing profile and places five independent perception requests at
each base release. Three requests and the downstream control task are critical
and have `DropThreshold=0`; two perception requests are explicitly redundant
and have positive task-level drop thresholds. All nodes are non-partitionable,
so refinement cannot merge away the ready-queue pressure being studied.

For this Mac study, `gpu_threshold=100` disables utilization-based activation,
which is not deterministic on MPS. The formal trigger is instead the released
ready queue: `queue_threshold=10` with a three-tick persistence window. The base
0% workload stays below that threshold, while the injected 50% and 100% Burst
workloads cross it. Validation fails unless the 0% RED control has no overload
activation or proactive drop, and every 50%/100% RED cell has at least one
overload activation and a non-empty proactive-drop record.

Run the full local Mac/MPS study with:

```zsh
eval "$(/Users/rentao/miniconda3/bin/conda shell.zsh hook)"
conda activate schedule
cd "/Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler"
./experiments/run_burst_study.sh
```

The wrapper executes these three stages and resumes runs already marked
complete:

```bash
python experiments/burst_study.py plan
python experiments/burst_study.py run --resume --keep-going
python experiments/burst_study.py summarize
```

The default command executes 15 distinct condition/method cells once. To repeat
each cell, pass a positive integer:

```zsh
./experiments/run_burst_study.sh --repetitions 5
```

An explicit seed list, such as `--seeds 7,11,19`, overrides `--repetitions`.
Every execution uses a fixed pseudo-random permutation of its planned runs and a
two-second cooldown. Raw artifacts retain full precision. With one repetition,
the paper-facing summarizer uses that run directly. With multiple repetitions,
it selects one complete latency-median run from each group. It always truncates
all three values from the selected run to three decimal places without rounding.

The tracked `burst_mac_mps_v2` result files were generated earlier with five
repetitions per cell and the historical lighter workload. They remain available
as historical artifacts, but they do not demonstrate ProactiveDrop activation.
New default runs use the dedicated workload and are written under
`taskdata/major_revision_burst_mac_mps_v3/`.

Compact validated results are stored in:

- `experiments/results/burst_mac_mps_v2_summary.json`
- `experiments/results/burst_mac_mps_v2_table.csv`

Large per-run logs remain under
`taskdata/major_revision_burst_mac_mps_v2/` and are intentionally ignored by
Git.

## Tests

```bash
python -m pytest -q
```

The test suite covers workload-window semantics, complete-DAG cloning,
temporally distributed 50% selection, independent DAG identities, method
fairness, released-queue accounting, task-level drop-threshold propagation,
artifact validation, representative-run selection, and precision formatting.
