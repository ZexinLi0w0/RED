# RED: A Systematic Real-Time Scheduling Approach for Robotic Environmental Dynamics

> **RTSS 2023** · Research code and experiment artifacts

**RED** studies how to schedule deep learning workloads when a robot's environment changes and
perception and control tasks compete for limited compute. It represents workloads as task graphs,
tracks execution progress, and adjusts task release and execution granularity to improve timeliness.
The repository contains the scheduler, neural-network handlers, workload configurations, experiment
runners, and archived results.

The repository was previously named **ATC23**. The current branch also contains later extensions and
revision experiments, whose scripts and result labels use **MERIS**. Those experiments include LLF-DAG,
burst management, non-partitionable tasks, and calibrated CUDA/MPS workloads; they should not all be
interpreted as the original RTSS 2023 artifact. See [References and citation](#references-and-citation)
for both papers and BibTeX entries.

## What it does

- **Schedules dependent inference tasks.** A controller releases DAG nodes and communicates with handler
  processes through queues. Handlers run the selected neural-network work and report completion
  ([`main.py`](DeepLearningScheduler/main.py),
  [`controller_signaling.py`](DeepLearningScheduler/controller_signaling.py),
  [`handler_signaling.py`](DeepLearningScheduler/handler_signaling.py)).
- **Uses execution feedback.** The progress-tracking path adjusts subsequent task releases using observed
  execution, while the fine-grained path reconstructs and merges compatible work
  ([`task_scheduler.py`](DeepLearningScheduler/task_scheduler.py),
  [`task_generator.py`](DeepLearningScheduler/task_generator.py)).
- **Shares inference computation.** SIMONet uses a shared encoder and selectable decoder branches for
  robotic workloads, including perception and control
  ([`SIMONet.py`](DeepLearningScheduler/SIMO/SIMONet.py)).
- **Explores dynamic workload conditions.** Configurations and runners cover Urban Navigation, Emergency
  Obstacle Avoidance, Night Driving, burst arrivals, and non-partitionable nodes.
- **Records reproducible runs.** The matrix runner isolates each run and records the source revision,
  configuration hashes, task-stream hash, seed, runtime, raw outcomes, and summary metrics.

The default SIMO handler constructs a model without loading a trained checkpoint and uses random
`224 × 224` input tensors ([`handler5.py`](DeepLearningScheduler/handler/handler5.py)). This is a scheduling
and inference-timing workload; running it does not establish perception accuracy or closed-loop robot
performance. Other historical handlers have their own input and checkpoint requirements.

## Layout

| Path | Content |
|---|---|
| [`DeepLearningScheduler/`](DeepLearningScheduler) | scheduler, controller, handlers, and command-line entry point |
| [`DeepLearningScheduler/SIMO/`](DeepLearningScheduler/SIMO) | shared-encoder neural network and decoder backbones |
| [`DeepLearningScheduler/handler/`](DeepLearningScheduler/handler) | task implementations; handler 5 is the default SIMO workload |
| [`DeepLearningScheduler/TaskConfigs/`](DeepLearningScheduler/TaskConfigs) | workload descriptions, DAGs, platform profiles, and frozen experiment configurations |
| [`DeepLearningScheduler/experiments/`](DeepLearningScheduler/experiments) | experiment runners, calibration, validation, and result aggregation |
| [`DeepLearningScheduler/taskdata/`](DeepLearningScheduler/taskdata) | archived logs, runtime profiles, and per-run artifacts |
| [`DeepLearningScheduler/taskdata_figure/`](DeepLearningScheduler/taskdata_figure) | historical figure data |
| [`DeepLearningScheduler/visual_scripts/`](DeepLearningScheduler/visual_scripts) | historical plotting scripts and exported figures |
| [`DeepLearningScheduler/tests/`](DeepLearningScheduler/tests) | scheduler, task-generation, metrics, and experiment-runner tests |
| [`figures/`](figures) | paper figures, editable drawing sources, and archived experiment bundles |
| [`ROS RED Experienment Data.csv`](ROS%20RED%20Experienment%20Data.csv) | historical ROS experiment data |
| [`autoconfig_jetson.sh`](autoconfig_jetson.sh) | historical Jetson setup script; inspect its platform-specific settings before use |

Additional model code lives in [`Autopilot/`](DeepLearningScheduler/Autopilot),
[`Pytorch-UNet/`](DeepLearningScheduler/Pytorch-UNet),
[`lanenet-lane-detection-pytorch/`](DeepLearningScheduler/lanenet-lane-detection-pytorch), and
[`yolov5/`](DeepLearningScheduler/yolov5). These directories retain their upstream documentation and licenses.

## Scheduling methods

Use the following values with `main.py --approach` or the matrix runner's `--methods` option:

| Value | Behavior |
|---|---|
| `baseline` | EDF on the unmerged offered DAG |
| `llf-dag` | least laxity first using the remaining critical-path profile cost |
| `feedback` | execution-feedback adjustment |
| `fine-grained` | fine-grained DAG reconstruction and merging |
| `feedback-fine-grained` | combined framework; labeled MERIS in later experiments |

LLF-DAG receives the same offered DAG and per-node runtime profile as EDF. Its cost estimate is scoped
to the currently admitted DAG instance. See the
[reproducible-run protocol](DeepLearningScheduler/experiments/REPRODUCIBLE_RUNS.md) for comparison and
calibration rules.

## Reproduce

### Prepare the environment

Clone the renamed repository and run scheduler commands from `DeepLearningScheduler/`; several model
imports and data paths depend on this working directory.

```bash
git clone git@github.com:ZexinLi0w0/RED.git
cd RED/DeepLearningScheduler

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Install **PyTorch and torchvision separately**, using builds compatible with your operating system and
accelerator. They are not included in `requirements.txt`. On Jetson, match the installed JetPack/CUDA
runtime; on Apple Silicon, use an MPS-capable PyTorch build. The requirements pin NumPy to `1.25.2` and
OpenCV to `4.11.0.86`; Python 3.10 is a practical starting point for a new environment, rather than a
claim that every dependency/platform combination has been validated.

```bash
python -c 'import torch, torchvision; print("torch:", torch.__version__); print("CUDA:", torch.cuda.is_available()); print("MPS:", torch.backends.mps.is_available())'
python main.py --help
```

`--torch-device auto` prefers CUDA, then MPS, then CPU. Request `cuda`, `cuda:0`, `mps`, or `cpu`
explicitly for measured runs. CPU execution can check functionality, but timings from a frozen GPU
configuration are not calibrated CPU results.

### Run one workload

For an Apple Silicon/MPS machine, this example runs the frozen Night Driving workload with EDF:

```bash
python main.py \
  --config handler-config.json \
  --task TaskConfigs/simo/overall_mac_mps_v3/mac_tight_night_driving.json \
  --approach baseline \
  --torch-device mps \
  --seed 101 \
  --output-dir taskdata/local/night-driving-edf-101 \
  --run-id night-driving-edf-101
```

Choose the configuration and backend together. For another platform, use its matching workload and
runtime profile rather than simply changing the device flag. Use a fresh output directory for each
manual run; the matrix runner below manages run isolation and provenance.

### Preview and run a comparison

The following command previews 15 cells: three scenarios × five methods × one seed. It does not execute
the inference workloads while `--dry-run` is present.

```bash
python experiments/run_matrix.py \
  --device mac --power-mode mps-default-ac-power \
  --handler-config handler-config.json \
  --task-dir TaskConfigs/simo/overall_mac_mps_v3 \
  --output-root taskdata/local/overall-mac \
  --profiles tight \
  --scenarios urban_navigation,emergency_obstacle_avoidance,night_driving \
  --methods baseline,llf-dag,fine-grained,feedback,feedback-fine-grained \
  --seeds 101 --torch-device mps \
  --cooldown-seconds 2 --keep-going --dry-run
```

Remove `--dry-run` to execute on the intended machine. Use `--seeds 101,202,303,404,505` for the five-seed,
75-run campaign, or `--repetitions N` to generate deterministic repetition seeds automatically.
An explicit seed list overrides the repetition count. `--resume` skips runs marked complete; investigate
failed or partial directories before selecting a new run identity.

For a new platform, first measure synchronized SIMONet costs with
[`profile_simo_runtime.py`](DeepLearningScheduler/experiments/profile_simo_runtime.py), then calibrate
using EDF only and freeze the selected configurations before comparing methods. The
[protocol](DeepLearningScheduler/experiments/REPRODUCIBLE_RUNS.md) includes the AGX Orin CUDA/MAXN workflow.

## Experiments

| Study | Launcher or driver | Configurations / protocol |
|---|---|---|
| Overall performance and ablations | [`run_matrix.py`](DeepLearningScheduler/experiments/run_matrix.py) | [`overall_mac_mps_v3/`](DeepLearningScheduler/TaskConfigs/simo/overall_mac_mps_v3), [AGX Orin calibration](DeepLearningScheduler/experiments/REPRODUCIBLE_RUNS.md) |
| Burst arrivals and overload management | [`run_burst_study.sh`](DeepLearningScheduler/experiments/run_burst_study.sh), [`run_agx_orin_burst_study.sh`](DeepLearningScheduler/experiments/run_agx_orin_burst_study.sh), [`run_nano1_burst_study.sh`](DeepLearningScheduler/experiments/run_nano1_burst_study.sh) | [burst definitions and validation](DeepLearningScheduler/BURST_TASK_IMPLEMENTATION.md) |
| Non-partitionable nodes | [`run_matrix.py`](DeepLearningScheduler/experiments/run_matrix.py), [`agx_orin_non_partitionable.py`](DeepLearningScheduler/experiments/agx_orin_non_partitionable.py), [`nano1_non_partitionable.py`](DeepLearningScheduler/experiments/nano1_non_partitionable.py) | [`nonpartitionable_mac_mps_v2/`](DeepLearningScheduler/TaskConfigs/simo/nonpartitionable_mac_mps_v2), [feature details](DeepLearningScheduler/Non-partitionableTasksFeature.md) |
| Parameter sensitivity | [`run_parameter_sensitivity.sh`](DeepLearningScheduler/experiments/run_parameter_sensitivity.sh) | [parameter grid and artifact schema](DeepLearningScheduler/experiments/PARAMETER_SENSITIVITY.md) |
| Historical scenarios and figures | [`run_exp1.sh`](DeepLearningScheduler/run_exp1.sh), [`visual_scripts/`](DeepLearningScheduler/visual_scripts) | [`figures/`](figures), [`taskdata_figure/`](DeepLearningScheduler/taskdata_figure) |

The Mac burst wrapper runs 15 condition/method cells once by default. The current parameter-sensitivity
protocol contains 47 settings: 20 refinement combinations and 27 burst-management combinations. Both
support `--repetitions N`. The sensitivity wrapper performs `git pull --ff-only` and requires a clean
source tree. Consult each linked protocol for platform settings and output directories before launching
a full campaign; historical wrappers may contain machine-specific paths.

## Results and metrics

Each matrix-run directory contains:

| File | Content |
|---|---|
| `manifest.json` | device and power mode, runtime, Git revision/status, configuration hashes, seed, command, task-stream hash, timestamps, and status |
| `stdout.log` | controller and handler output |
| `task_statistics.pkl` | original offered-node outcomes, including nodes whose execution was merged |
| `end2end_time.txt` | end-to-end timing output |
| `summary.json` | machine-readable run metrics |

Aggregate an executed matrix from the scheduler directory:

```bash
python experiments/summarize_runs.py \
  --input-root taskdata/local/overall-mac \
  --output-json taskdata/local/overall-mac-summary.json \
  --output-csv taskdata/local/overall-mac-summary.csv
```

Later revision runs report latency, deadline missing rate, timing utility (QoE), and valid-output rate.
Their QoE uses the original offered-node population: valid inference outputs receive a latency-dependent
score, while skips, proactive drops, and execution errors receive zero. This is a timing metric, not a
perception-accuracy score. The historical `QoEScore` helper is retained for older plots and is not the
revision headline metric. Do not combine the two definitions in a comparison.

For repeated Table 11 cells, the protocol selects one complete median-latency run; latency, deadline
missing rate, and QoE must come from that same run rather than different seeds. Archived data and
plotting scripts are retained in place so their original paths and provenance remain readable.

## Configuration and development

[`handler-config.json`](DeepLearningScheduler/handler-config.json) selects handler 5. The current
`main.py` loads DAG workloads with a `dag_list`; older flat `task_list` examples in the detailed scheduler
notes describe an earlier configuration path. Start from a committed DAG configuration.

Important DAG settings include `DeadlineFactor`, `ArrivalScale`, `DagRepeatedTimes`, `TaskSeed`, and
`ParallelStagePolicy`. Runtime profiles and calibration metadata bind measured costs to a platform.
Non-partitionable and burst settings are described in the linked experiment protocols. Changing timing
or workload parameters creates a new experiment condition and should be recorded with its outputs.

Handlers implement [`AbstractHandler`](DeepLearningScheduler/AbstractHandler.py); the existing
[`handler5.py`](DeepLearningScheduler/handler/handler5.py) shows the current SIMO implementation.
Run the configured test suite from `DeepLearningScheduler/` after installing development dependencies
and the appropriate PyTorch/torchvision builds:

```bash
python -m pytest
```

Further documentation:

- [Scheduler and historical command examples](DeepLearningScheduler/README.md)
- [Chinese scheduler notes](DeepLearningScheduler/README-zh.md)
- [Reproducible runs and calibration](DeepLearningScheduler/experiments/REPRODUCIBLE_RUNS.md)
- [Burst task implementation](DeepLearningScheduler/BURST_TASK_IMPLEMENTATION.md)
- [Parameter sensitivity](DeepLearningScheduler/experiments/PARAMETER_SENSITIVITY.md)

## References and citation

If you use this repository in your research, please cite the paper corresponding to the methods and
experiments you use. RED is the original RTSS 2023 paper; MERIS is its extended work, available as a
2026 arXiv preprint. Please cite both when your work builds on both versions.

1. **RED.** Zexin Li, Tao Ren, Xiaoxi He, and Cong Liu.
   “RED: A Systematic Real-Time Scheduling Approach for Robotic Environmental Dynamics.”
   In *2023 IEEE Real-Time Systems Symposium (RTSS)*, pp. 210–223, 2023.
   [Published paper / DOI](https://doi.org/10.1109/RTSS59052.2023.00027) ·
   [arXiv](https://arxiv.org/abs/2308.15368).
2. **MERIS.** Zexin Li, Tao Ren, Johnathan Liu, Xiaoxi He, and Cong Liu.
   “MERIS: Adaptive Real-Time Scheduling of Refined Inference DAGs in Dynamic Robotic Environments.”
   *arXiv preprint arXiv:2605.24044*, 2026. Extension of the RTSS 2023 paper.
   [Paper](https://arxiv.org/abs/2605.24044) ·
   [DOI](https://doi.org/10.48550/arXiv.2605.24044).

```bibtex
@inproceedings{li2023red,
  author    = {Zexin Li and Tao Ren and Xiaoxi He and Cong Liu},
  title     = {{RED}: A Systematic Real-Time Scheduling Approach for Robotic Environmental Dynamics},
  booktitle = {2023 IEEE Real-Time Systems Symposium (RTSS)},
  year      = {2023},
  pages     = {210--223},
  publisher = {IEEE},
  doi       = {10.1109/RTSS59052.2023.00027},
  url       = {https://doi.org/10.1109/RTSS59052.2023.00027}
}

@misc{li2026meris,
  author        = {Zexin Li and Tao Ren and Johnathan Liu and Xiaoxi He and Cong Liu},
  title         = {{MERIS}: Adaptive Real-Time Scheduling of Refined Inference {DAGs} in Dynamic Robotic Environments},
  year          = {2026},
  eprint        = {2605.24044},
  archivePrefix = {arXiv},
  primaryClass  = {cs.RO},
  doi           = {10.48550/arXiv.2605.24044},
  url           = {https://arxiv.org/abs/2605.24044}
}
```
