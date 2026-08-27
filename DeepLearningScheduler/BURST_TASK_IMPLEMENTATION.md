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
  "release_horizon_seconds": 1.96,
  "gpu_threshold": 90.0,
  "queue_threshold": 8,
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
and RED five times each, and validates identical offered-stream hashes across
methods.

```bash
eval "$(/Users/rentao/miniconda3/bin/conda shell.zsh hook)"
conda activate schedule

python experiments/burst_study.py plan
python experiments/burst_study.py run --keep-going
python experiments/burst_study.py summarize
```

The formal M3 Max protocol uses a fixed pseudo-random permutation of all 75
runs and a two-second cooldown. Raw artifacts retain full precision. The
paper-facing summarizer selects one complete latency-median run from each group
and truncates all three values from that same run to three decimal places
without rounding.

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
