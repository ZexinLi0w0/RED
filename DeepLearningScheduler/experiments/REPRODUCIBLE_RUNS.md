# Reproducible experiment runner

`run_matrix.py` executes every experiment cell once by default, with each run
stored in an isolated directory. Each run contains:

- `manifest.json`: device, power mode, resolved PyTorch device/runtime, git
  commit/status, config SHA-256, seed, command, offered-task hash, timestamps,
  and final status;
- `stdout.log`: complete controller/handler output;
- `task_statistics.pkl`: original offered-node outcomes, even when execution
  nodes were merged;
- `end2end_time.txt` and `summary.json`: machine-readable headline metrics.

Always inspect the matrix before occupying a device:

```bash
python3 experiments/run_matrix.py \
  --device agx \
  --power-mode MAXN \
  --handler-config handler-config.json \
  --task-dir TaskConfigs/simo/new_scenarios \
  --output-root taskdata/reruns/agx \
  --profiles tight,loose \
  --torch-device cuda \
  --dry-run
```

Remove `--dry-run` to execute. A run directory is never overwritten. Passing
`--resume` skips only runs whose manifest already says `complete`; failed or
partial directories require investigation and a new run identity.

To repeat every cell, pass a positive count. Deterministic seeds are generated
automatically:

```bash
python3 experiments/run_matrix.py [other arguments] --repetitions 5
```

For advanced reproduction of specific runs, an explicit list such as
`--seeds 7,11,19` overrides `--repetitions`.

`--torch-device auto` prefers CUDA, then Apple MPS, then CPU. Formal runs
should request the intended backend explicitly (`cuda`, `mps`, or `cpu`), so
an unavailable accelerator fails rather than silently changing the evaluated
platform. CUDA/MPS completion is synchronized before the handler reports a
task end time.

Before calibrating a new platform/backend, profile synchronized SIMONet costs:

```bash
python experiments/profile_simo_runtime.py \
  --output taskdata/profiles/mac-mps.json \
  --torch-device mps \
  --power-mode mps-default-ac-power
```

The default bound policy uses 20 warmups, 200 retained samples, and the
observed maximum plus a predeclared 10% margin. Profile output is immutable and
contains every retained sample plus code/runtime provenance.

For EDF-only calibration, use calibration profile names/config files and only
the `baseline` method. Do not include or inspect the proposed method until the
selected Tight/Loose configurations have been committed and hashed.

The formal core matrix uses these method names:

- `baseline`: EDF on the unmerged offered DAG;
- `llf-dag`: least-laxity-first with
  `deadline - now - remaining critical-path profile cost`;
- `fine-grained`, `feedback`, and `feedback-fine-grained`: the two ablations
  and complete framework used by the current artifact.

LLF-DAG receives the same offered DAG and per-node profile as EDF. Its
remaining-cost calculation is confined to the currently admitted DAG instance;
it does not inspect completion times or arrivals from later DAG instances and
does not use MIMONet merging.

## AGX Orin Table 11 calibration

The AGX Orin replacement matrix is generated from the synchronized CUDA/MAXN
runtime profile rather than the historical embedded timing estimates. Build the
predeclared EDF-only coarse grid with:

```bash
python3 -m experiments.agx_orin_overall build-calibration \
  --template-dir TaskConfigs/simo/new_scenarios \
  --runtime-profile taskdata/runtime_profiles/agx_orin_maxn_20260828_v1.json \
  --output-dir TaskConfigs/simo/overall_agx_orin_cuda_v1
```

Run the eight calibration profiles with EDF and a calibration-only seed, then
select one timing pair per scenario without inspecting the proposed methods:

```bash
python3 experiments/run_matrix.py \
  --device agx --power-mode agx-orin-maxn \
  --handler-config handler-config.json \
  --task-dir TaskConfigs/simo/overall_agx_orin_cuda_v1/calibration \
  --output-root taskdata/major_revision_overall_agx_orin_calibration_v1 \
  --profiles cal_d0200_a0200,cal_d0400_a0200,cal_d0400_a0400,cal_d0600_a0400,cal_d0800_a0400,cal_d0800_a0800,cal_d1200_a0800,cal_d1200_a1200 \
  --scenarios urban_navigation,emergency_obstacle_avoidance,night_driving \
  --methods baseline --seeds 11 --torch-device cuda:0 \
  --cooldown-seconds 2 --keep-going

python3 -m experiments.agx_orin_overall select-edf \
  --index TaskConfigs/simo/overall_agx_orin_cuda_v1/calibration_index.json \
  --runs-root taskdata/major_revision_overall_agx_orin_calibration_v1 \
  --output TaskConfigs/simo/overall_agx_orin_cuda_v1/selection_report.json
```

Freeze the selected configs as `pilot`, run all five methods with paired seeds
11/22/33, and validate the discrimination gate before any formal run. The gate
requires, independently for every scenario, at least three interior Deadline
Missing Rate means, a Deadline Missing Rate spread of at least 0.10, at least
three interior QoE means, and a QoE spread of at least 0.05. Once the pilot is
accepted, freeze the identical timing pairs as `tight` and run formal seeds
101/202/303/404/505. The resulting 75-run matrix is summarized with
`experiments/summarize_runs.py`; every displayed Table 11 metric tuple comes
from the same median-latency run.

## Timing utility reported as QoE

Revision runs use an XRBench-derived timing utility over the original offered
node population. A valid inference output receives
`1 / (1 + exp(k * (latency - request_to_deadline_window)))` with the XRBench
default `k=15 s^-1`; a skip, proactive drop, or execution error receives zero.
The summary also reports `valid_output_rate` separately. This aggregation is
equivalent to combining the processed-frame ratio with the mean per-inference
real-time score while preserving one denominator across methods. The
historical `QoEScore` helper remains available only to reproduce older plots;
it is not the revision headline metric.
