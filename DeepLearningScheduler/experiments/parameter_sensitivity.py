#!/usr/bin/env python3
"""Run and summarize the paper's two-block parameter sensitivity study."""

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from burst_task_manager import (  # noqa: E402
    BurstTaskManager,
    burst_workload_config_from_mapping,
)
from runtime_device import torch_runtime_info  # noqa: E402
from task_generator import (  # noqa: E402
    generate_tasks_from_dag,
    load_dag_experiment_config,
    task_stream_sha256,
)


DEFAULT_TASK_CONFIG = (
    REPOSITORY_ROOT
    / "TaskConfigs"
    / "simo"
    / "parameter_sensitivity"
    / "agx_high_load.json"
)
DEFAULT_BURST_CONFIG = REPOSITORY_ROOT / "burst_config.json"
DEFAULT_HANDLER_CONFIG = REPOSITORY_ROOT / "handler-config.json"
DEFAULT_OUTPUT_ROOT = (
    REPOSITORY_ROOT / "taskdata" / "parameter_sensitivity" / "agx_high_load_v1"
)
DEFAULT_REPETITIONS = 1
DEFAULT_SEED_STEP = 101
DEFAULT_SEEDS = (DEFAULT_SEED_STEP,)
METRICS = (
    "end_to_end_latency_seconds",
    "deadline_missing_rate",
    "qoe_score",
)
EXECUTION_SOURCE_FILES = (
    "main.py",
    "task_scheduler.py",
    "task_generator.py",
    "burst_task_manager.py",
    "deadline_reassignment.py",
    "visual_scripts/visual_task.py",
)
PAPER_DEFAULTS = {
    "moving_average_window": 8,
    "release_time_skew_threshold_ms": 100.0,
    "gpu_threshold": 90.0,
    "queue_threshold": 8,
    "persistence_window": 3,
}


@dataclass(frozen=True)
class SensitivityPoint:
    block: str
    group: str
    parameter: str
    setting: str
    slug: str
    moving_average_window: int
    release_time_skew_threshold_ms: float
    gpu_threshold: float
    queue_threshold: int
    persistence_window: int
    burst_enabled: bool

    @property
    def executed_parameters(self):
        return {
            "moving_average_window": self.moving_average_window,
            "release_time_skew_threshold_ms": self.release_time_skew_threshold_ms,
            "gpu_threshold": self.gpu_threshold,
            "queue_threshold": self.queue_threshold,
            "persistence_window": self.persistence_window,
            "burst_enabled": self.burst_enabled,
        }


def _sensitivity_points():
    points = []
    for window in (1, 4, 8, 16):
        for skew_ms in (0.0, 50.0, 100.0, 150.0, 200.0):
            points.append(
                SensitivityPoint(
                    block="refinement",
                    group="Refinement sensitivity",
                    parameter="k x gamma",
                    setting=f"k={window}, gamma={skew_ms:g} ms",
                    slug=f"refinement-k{window:02d}-gamma{int(skew_ms):03d}ms",
                    moving_average_window=window,
                    release_time_skew_threshold_ms=skew_ms,
                    gpu_threshold=PAPER_DEFAULTS["gpu_threshold"],
                    queue_threshold=PAPER_DEFAULTS["queue_threshold"],
                    persistence_window=PAPER_DEFAULTS["persistence_window"],
                    burst_enabled=False,
                )
            )
    for gpu_threshold in (70.0, 80.0, 90.0):
        for queue_threshold in (4, 8, 16):
            for persistence_window in (1, 3, 5):
                points.append(
                    SensitivityPoint(
                        block="burst-management",
                        group="Burst Management sensitivity",
                        parameter="theta_u x Q_max x W",
                        setting=(
                            f"theta_u={gpu_threshold:g}%, Q_max={queue_threshold}, "
                            f"W={persistence_window} ticks"
                        ),
                        slug=(
                            f"burst-gpu{int(gpu_threshold):03d}pct-"
                            f"queue{queue_threshold:02d}-window{persistence_window}tick"
                        ),
                        moving_average_window=PAPER_DEFAULTS["moving_average_window"],
                        release_time_skew_threshold_ms=PAPER_DEFAULTS[
                            "release_time_skew_threshold_ms"
                        ],
                        gpu_threshold=gpu_threshold,
                        queue_threshold=queue_threshold,
                        persistence_window=persistence_window,
                        burst_enabled=True,
                    )
                )
    return tuple(points)


SENSITIVITY_POINTS = _sensitivity_points()


def _csv_ints(raw_value):
    try:
        values = tuple(int(item.strip()) for item in raw_value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "seeds must be comma-separated integers"
        ) from exc
    if not values or any(value < 0 for value in values):
        raise argparse.ArgumentTypeError("seeds must be non-negative integers")
    if len(values) != len(set(values)):
        raise argparse.ArgumentTypeError("seeds cannot contain duplicates")
    return values


def _positive_int(raw_value):
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        ) from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return value


def _seeds_for_repetitions(repetitions):
    return tuple(DEFAULT_SEED_STEP * index for index in range(1, repetitions + 1))


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _execution_source_hashes():
    return {
        relative_path: _sha256(REPOSITORY_ROOT / relative_path)
        for relative_path in EXECUTION_SOURCE_FILES
    }


def _write_json_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    with open(temporary_path, "w", encoding="utf-8") as output_file:
        json.dump(value, output_file, indent=2, sort_keys=True)
        output_file.write("\n")
    os.replace(temporary_path, path)


def _load_json(path):
    with open(path, encoding="utf-8") as input_file:
        return json.load(input_file)


def _git_output(*arguments):
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _validate_block_isolation(point):
    if point.block == "refinement":
        if point.burst_enabled:
            raise ValueError(f"{point.slug} must disable Burst Management")
    elif point.block == "burst-management":
        if not point.burst_enabled:
            raise ValueError(f"{point.slug} must enable Burst Management")
        if (
            point.moving_average_window != PAPER_DEFAULTS["moving_average_window"]
            or point.release_time_skew_threshold_ms
            != PAPER_DEFAULTS["release_time_skew_threshold_ms"]
        ):
            raise ValueError(f"{point.slug} must hold refinement parameters fixed")
    else:
        raise ValueError(f"unknown sensitivity block: {point.block}")


def generate_study_plan(
    base_task_config,
    base_burst_config,
    output_root,
    seeds=DEFAULT_SEEDS,
    method="feedback-fine-grained",
):
    base_task_config = Path(base_task_config).resolve()
    base_burst_config = Path(base_burst_config).resolve()
    output_root = Path(output_root).resolve()
    task_template = _load_json(base_task_config)
    burst_template = _load_json(base_burst_config)
    if not task_template.get("dag_list"):
        raise ValueError("base task config must contain a non-empty dag_list")
    if float(task_template.get("BurstTaskRatio", 0)) <= 0:
        raise ValueError(
            "base task config must set BurstTaskRatio above zero so burst "
            "parameters are exercised"
        )

    config_root = output_root / "generated_configs"
    plan_points = []
    for order, point in enumerate(SENSITIVITY_POINTS, start=1):
        _validate_block_isolation(point)
        task_config = json.loads(json.dumps(task_template))
        burst_config = json.loads(json.dumps(burst_template))
        task_config["MovingAverageWindow"] = point.moving_average_window
        task_config["ReleaseTimeSkewThresholdMs"] = (
            point.release_time_skew_threshold_ms
        )
        if not point.burst_enabled:
            task_config["BurstTaskRatio"] = 0
            task_config["NonPartitionablePercentage"] = 0
        else:
            # Keep burst backlog visible to Burst Management. If these nodes
            # were merged first, the queue would never cross the paper's
            # Q_max grid and the burst block would be degenerate.
            task_config["NonPartitionablePercentage"] = 100
        burst_config.update(
            {
                "burst_enabled": point.burst_enabled,
                "gpu_threshold": point.gpu_threshold,
                "queue_threshold": point.queue_threshold,
                "persistence_window": point.persistence_window,
            }
        )
        executed_parameters = point.executed_parameters
        metadata = {
            "study": "parameter-sensitivity",
            "protocol": "independent-block-full-factorial",
            "point_order": order,
            "point_slug": point.slug,
            "block": point.block,
            "group": point.group,
            "parameter": point.parameter,
            "setting": point.setting,
            "executed_parameters": executed_parameters,
        }
        task_config["ParameterSensitivityStudy"] = metadata
        burst_config["parameter_sensitivity_study"] = metadata

        point_root = config_root / f"{order:02d}-{point.slug}"
        task_path = point_root / "task.json"
        burst_path = point_root / "burst.json"
        _write_json_atomic(task_path, task_config)
        _write_json_atomic(burst_path, burst_config)
        plan_points.append(
            {
                **metadata,
                "task_config_path": str(task_path),
                "task_config_sha256": _sha256(task_path),
                "burst_config_path": str(burst_path),
                "burst_config_sha256": _sha256(burst_path),
            }
        )

    plan = {
        "schema_version": 1,
        "study": "parameter-sensitivity",
        "protocol": "independent-block-full-factorial",
        "representative_scenario": base_task_config.stem,
        "method": method,
        "repetitions_per_point": len(seeds),
        "seeds": list(seeds),
        "paper_defaults": PAPER_DEFAULTS,
        "base_task_config": str(base_task_config),
        "base_task_config_sha256": _sha256(base_task_config),
        "base_burst_config": str(base_burst_config),
        "base_burst_config_sha256": _sha256(base_burst_config),
        "points": plan_points,
        "point_counts": {"refinement": 20, "burst-management": 27},
        "planned_run_count": len(plan_points) * len(seeds),
    }
    _write_json_atomic(output_root / "study_plan.json", plan)
    return plan


def _offered_stream(task_config_path, burst_config_path, seed):
    dag, timing, non_partitionable_percentage, non_partitionable_config, burst_ratio = (
        load_dag_experiment_config(task_config_path)
    )
    tasks = generate_tasks_from_dag(
        dag,
        deadline_factor=timing.deadline_factor,
        arrival_scale=timing.arrival_scale,
        dag_repeated_times=timing.dag_repeated_times,
        parallel_stage_policy=timing.parallel_stage_policy,
        non_partitionable_percentage=non_partitionable_percentage,
        non_partitionable_config=non_partitionable_config,
        seed=seed,
    )
    burst_config = _load_json(burst_config_path)
    if burst_config.get("burst_enabled", False) and burst_ratio > 0:
        manager = BurstTaskManager(
            gpu_threshold=burst_config["gpu_threshold"],
            queue_threshold=burst_config["queue_threshold"],
            persistence_window=burst_config["persistence_window"],
            default_drop_threshold=burst_config.get("drop_threshold", 0.5),
            monitoring_interval=burst_config.get("monitoring_interval", 0.05),
            workload_config=burst_workload_config_from_mapping(burst_config),
        )
        tasks = tasks + manager.generate_burst_tasks(tasks, burst_ratio)
    return len(tasks), task_stream_sha256(tasks)


def _run_id(point, seed, task_hash, burst_hash):
    return (
        f"ps-{point['point_order']:02d}-{point['point_slug']}-seed{seed}-"
        f"task{task_hash[:8]}-burst{burst_hash[:8]}"
    )


def _archive_previous_attempt(run_dir, attempt):
    for name in (
        "manifest.json",
        "stdout.log",
        "summary.json",
        "task_statistics.pkl",
        "end2end_time.txt",
    ):
        path = run_dir / name
        if path.exists():
            archived = run_dir / f"{name}.attempt{attempt}"
            if archived.exists():
                raise FileExistsError(
                    f"refusing to overwrite archived attempt: {archived}"
                )
            os.replace(path, archived)


def _summary_parameters(summary):
    burst = summary.get("burst_statistics") or {}
    reassignment = summary.get("moving_average_reassignment") or {}
    return {
        "moving_average_window": reassignment.get("window"),
        "release_time_skew_threshold_ms": summary.get("release_time_skew_threshold_ms"),
        "gpu_threshold": burst.get("gpu_threshold"),
        "queue_threshold": burst.get("queue_threshold"),
        "persistence_window": burst.get("persistence_window"),
        "burst_enabled": summary.get("burst_statistics") is not None,
    }


def _validate_completed_run(manifest, summary):
    problems = []
    if summary.get("run_id") != manifest.get("run_id"):
        problems.append("run_id mismatch")
    if summary.get("offered_task_count") != manifest.get("offered_task_count"):
        problems.append("offered_task_count mismatch")
    if summary.get("offered_task_stream_sha256") != manifest.get(
        "offered_task_stream_sha256"
    ):
        problems.append("offered_task_stream_sha256 mismatch")
    actual_parameters = _summary_parameters(summary)
    expected_parameters = manifest.get("executed_parameters", {})
    compared_keys = (
        ("moving_average_window", "release_time_skew_threshold_ms", "burst_enabled")
        if not expected_parameters.get("burst_enabled")
        else tuple(expected_parameters)
    )
    actual_compared = {key: actual_parameters.get(key) for key in compared_keys}
    expected_compared = {key: expected_parameters.get(key) for key in compared_keys}
    if actual_compared != expected_compared:
        problems.append(
            "executed parameter mismatch: "
            f"expected={expected_compared}, actual={actual_compared}"
        )
    for metric in METRICS:
        value = summary.get(metric)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            problems.append(f"invalid metric {metric}")
    return problems


def run_study(
    plan,
    handler_config,
    output_root,
    device,
    power_mode,
    torch_device,
    python_executable,
    cooldown_seconds,
    dry_run=False,
    resume=False,
    keep_going=False,
):
    output_root = Path(output_root).resolve()
    handler_config = Path(handler_config).resolve()
    if not handler_config.is_file():
        raise FileNotFoundError(handler_config)
    if cooldown_seconds < 0:
        raise ValueError("cooldown_seconds cannot be negative")
    runtime_info = (
        {
            "requested": torch_device,
            "resolved": torch_device,
            "probe": "skipped for dry-run",
        }
        if dry_run
        else torch_runtime_info(torch_device)
    )
    git_commit = _git_output("rev-parse", "HEAD")
    git_status = _git_output("status", "--porcelain", "--", ".")
    execution_source_hashes = _execution_source_hashes()
    runs_root = output_root / "runs"
    failures = 0

    for point in plan["points"]:
        task_path = Path(point["task_config_path"])
        burst_path = Path(point["burst_config_path"])
        for seed in plan["seeds"]:
            if _git_output("rev-parse", "HEAD") != git_commit:
                raise RuntimeError(
                    "git HEAD changed during the study; refusing to mix "
                    "provenance in one parameter-sensitivity batch"
                )
            if _git_output("status", "--porcelain", "--", ".") != git_status:
                raise RuntimeError(
                    "source-tree status changed during the study; refusing to "
                    "mix workspace states in one parameter-sensitivity batch"
                )
            current_source_hashes = _execution_source_hashes()
            if current_source_hashes != execution_source_hashes:
                raise RuntimeError(
                    "execution source changed during the study; refusing to "
                    "mix code versions in one parameter-sensitivity batch"
                )
            offered_count, offered_hash = _offered_stream(task_path, burst_path, seed)
            run_id = _run_id(
                point,
                seed,
                point["task_config_sha256"],
                point["burst_config_sha256"],
            )
            run_dir = runs_root / run_id
            manifest_path = run_dir / "manifest.json"
            command = [
                python_executable,
                str(REPOSITORY_ROOT / "main.py"),
                "--config", str(handler_config),
                "--task", str(task_path),
                "--approach", plan["method"],
                "--seed", str(seed),
                "--output-dir", str(run_dir),
                "--run-id", run_id,
                "--torch-device", runtime_info["resolved"],
                "--burst-config", str(burst_path),
            ]
            manifest = {
                "schema_version": 1,
                "study": plan["study"],
                "protocol": plan["protocol"],
                "run_id": run_id,
                "status": "planned" if dry_run else "running",
                "device": device,
                "power_mode": power_mode,
                "scenario": plan["representative_scenario"],
                "profile": "sensitivity",
                "method": plan["method"],
                "seed": seed,
                "point_order": point["point_order"],
                "point_slug": point["point_slug"],
                "sensitivity_block": point["block"],
                "sensitivity_group": point["group"],
                "parameter": point["parameter"],
                "setting": point["setting"],
                "executed_parameters": point["executed_parameters"],
                "task_config_path": str(task_path),
                "task_config_sha256": point["task_config_sha256"],
                "burst_config_path": str(burst_path),
                "burst_config_sha256": point["burst_config_sha256"],
                "offered_task_count": offered_count,
                "offered_task_stream_sha256": offered_hash,
                "git_commit": git_commit,
                "git_status_porcelain": git_status,
                "execution_source_hashes": execution_source_hashes,
                "python": python_executable,
                "torch_runtime": runtime_info,
                "command": command,
                "host": socket.gethostname(),
                "platform": platform.platform(),
            }

            if dry_run:
                print(json.dumps(manifest, sort_keys=True))
                continue
            if run_dir.exists():
                if resume and manifest_path.is_file():
                    existing = _load_json(manifest_path)
                    if existing.get("status") == "complete":
                        print(f"SKIP complete {run_id}")
                        continue
                    previous_attempt = int(existing.get("attempt", 1))
                    _archive_previous_attempt(run_dir, previous_attempt)
                    manifest["attempt"] = previous_attempt + 1
                    manifest["resumed_from_status"] = existing.get("status")
                else:
                    raise FileExistsError(
                        f"refusing to overwrite existing run directory: {run_dir}"
                    )
            else:
                run_dir.mkdir(parents=True)
                manifest["attempt"] = 1
            manifest["started_at"] = _utc_now()
            _write_json_atomic(manifest_path, manifest)
            started = time.monotonic()
            with open(run_dir / "stdout.log", "w", encoding="utf-8") as log:
                completed = subprocess.run(
                    command,
                    cwd=REPOSITORY_ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            manifest["return_code"] = completed.returncode
            manifest["finished_at"] = _utc_now()
            manifest["duration_seconds"] = time.monotonic() - started
            summary_path = run_dir / "summary.json"
            if completed.returncode == 0 and summary_path.is_file():
                summary = _load_json(summary_path)
                validation_problems = _validate_completed_run(manifest, summary)
                manifest["validation_problems"] = validation_problems
                manifest["status"] = (
                    "complete" if not validation_problems else "failed-validation"
                )
                manifest["summary_sha256"] = _sha256(summary_path)
            else:
                manifest["status"] = "failed"
            _write_json_atomic(manifest_path, manifest)

            if manifest["status"] != "complete":
                failures += 1
                print(f"FAIL {run_id}: {manifest['status']}", file=sys.stderr)
                if not keep_going:
                    return 1
            else:
                print(f"DONE {run_id}")
            if cooldown_seconds:
                time.sleep(cooldown_seconds)

    if dry_run:
        print(f"Planned runs: {plan['planned_run_count']}", file=sys.stderr)
    return 1 if failures else 0


def _sample_summary(values):
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("metric samples must be non-empty and finite")
    mean = statistics.mean(values)
    sample_sd = statistics.stdev(values) if len(values) > 1 else 0.0
    # Two-sided 95% Student-t critical values for configurable small samples.
    # The normal approximation is sufficient above 30 degrees of freedom.
    t_critical_95 = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        11: 2.201,
        12: 2.179,
        13: 2.160,
        14: 2.145,
        15: 2.131,
        16: 2.120,
        17: 2.110,
        18: 2.101,
        19: 2.093,
        20: 2.086,
        21: 2.080,
        22: 2.074,
        23: 2.069,
        24: 2.064,
        25: 2.060,
        26: 2.056,
        27: 2.052,
        28: 2.048,
        29: 2.045,
        30: 2.042,
    }
    critical = t_critical_95.get(len(values) - 1, 1.960)
    half_width = critical * sample_sd / math.sqrt(len(values)) if len(values) > 1 else 0.0
    return {
        "mean": mean,
        "sample_sd": sample_sd,
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
        "minimum": min(values),
        "maximum": max(values),
    }


def summarize_study(output_root):
    output_root = Path(output_root).resolve()
    plan = _load_json(output_root / "study_plan.json")
    expected_seeds = set(plan["seeds"])
    expected_points = {point["point_slug"]: point for point in plan["points"]}
    grouped_runs = {slug: [] for slug in expected_points}
    problems = []

    for manifest_path in sorted((output_root / "runs").glob("*/manifest.json")):
        manifest = _load_json(manifest_path)
        run_name = manifest_path.parent.name
        if manifest.get("status") != "complete":
            problems.append(f"{run_name}: status={manifest.get('status')}")
            continue
        point = expected_points.get(manifest.get("point_slug"))
        if point is None:
            problems.append(f"{run_name}: unknown point_slug")
            continue
        summary_path = manifest_path.parent / "summary.json"
        if not summary_path.is_file():
            problems.append(f"{run_name}: missing summary.json")
            continue
        if _sha256(summary_path) != manifest.get("summary_sha256"):
            problems.append(f"{run_name}: summary hash mismatch")
            continue
        summary = _load_json(summary_path)
        run_problems = _validate_completed_run(manifest, summary)
        if run_problems:
            problems.extend(f"{run_name}: {problem}" for problem in run_problems)
            continue
        if manifest.get("executed_parameters") != point["executed_parameters"]:
            problems.append(f"{run_name}: parameters differ from study plan")
            continue
        grouped_runs[point["point_slug"]].append(
            {"manifest": manifest, "summary": summary}
        )

    raw_rows = []
    aggregate_rows = []
    report_points = []
    for point in plan["points"]:
        runs = grouped_runs[point["point_slug"]]
        seeds = [run["manifest"]["seed"] for run in runs]
        if len(seeds) != len(set(seeds)):
            problems.append(f"{point['point_slug']}: duplicate seeds")
        if set(seeds) != expected_seeds:
            problems.append(
                f"{point['point_slug']}: seeds={sorted(seeds)}, "
                f"expected={sorted(expected_seeds)}"
            )
            continue
        ordered = sorted(runs, key=lambda run: run["manifest"]["seed"])
        metric_samples = {
            metric: [float(run["summary"][metric]) for run in ordered]
            for metric in METRICS
        }
        metric_summaries = {
            metric: _sample_summary(values)
            for metric, values in metric_samples.items()
        }
        for run in ordered:
            raw_rows.append(
                {
                    "point_order": point["point_order"],
                    "sensitivity_block": point["block"],
                    "sensitivity_group": point["group"],
                    "parameter": point["parameter"],
                    "setting": point["setting"],
                    "seed": run["manifest"]["seed"],
                    "run_id": run["manifest"]["run_id"],
                    **{metric: run["summary"][metric] for metric in METRICS},
                }
            )
        aggregate_row = {
            "point_order": point["point_order"],
            "sensitivity_block": point["block"],
            "sensitivity_group": point["group"],
            "parameter": point["parameter"],
            "setting": point["setting"],
            "n": len(ordered),
            "end_to_end_latency_seconds": metric_summaries[
                "end_to_end_latency_seconds"
            ]["mean"],
            "deadline_missing_rate": metric_summaries[
                "deadline_missing_rate"
            ]["mean"],
            "qoe_score": metric_summaries["qoe_score"]["mean"],
        }
        aggregate_rows.append(aggregate_row)
        report_points.append(
            {
                **{key: point[key] for key in (
                    "point_order", "point_slug", "block", "group", "parameter",
                    "setting", "executed_parameters",
                )},
                "n": len(ordered),
                "seeds": sorted(seeds),
                "metrics": metric_summaries,
            }
        )

    if problems:
        raise ValueError("sensitivity artifact validation failed:\n" + "\n".join(problems))

    repetition_count = len(plan["seeds"])
    aggregation = (
        "single run per point"
        if repetition_count == 1
        else f"arithmetic mean across {repetition_count} configured repetitions"
    )
    report = {
        "schema_version": 1,
        "study": plan["study"],
        "aggregation": aggregation,
        "input_root": str(output_root),
        "complete_run_count": len(raw_rows),
        "points": report_points,
    }
    report_dir = output_root / "report"
    _write_json_atomic(report_dir / "parameter_sensitivity_report.json", report)
    _write_csv(
        report_dir / "parameter_sensitivity_runs.csv",
        raw_rows,
        (
            "point_order", "sensitivity_block", "sensitivity_group", "parameter", "setting",
            "seed", "run_id", *METRICS,
        ),
    )
    _write_csv(
        report_dir / "parameter_sensitivity_table.csv",
        aggregate_rows,
        (
            "point_order", "sensitivity_block", "sensitivity_group", "parameter", "setting", "n",
            *METRICS,
        ),
        decimal_digits=3,
    )
    _write_latex_rows(
        report_dir / "parameter_sensitivity_table_rows.tex",
        aggregate_rows,
        repetition_count,
    )
    return report


def _write_csv(path, rows, fieldnames, decimal_digits=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            if decimal_digits is not None:
                for metric in METRICS:
                    formatted[metric] = f"{float(formatted[metric]):.{decimal_digits}f}"
            writer.writerow(formatted)


def _latex_escape_setting(setting):
    return setting.replace("%", r"\%").replace(" (default)", r" \textbf{(default)}")


def _write_latex_rows(path, rows, repetition_count):
    parameter_labels = {
        "k x gamma": r"$k \times \gamma$",
        "theta_u x Q_max x W": r"$\theta_u \times Q_{\max} \times W$",
    }
    value_description = (
        "one run per point"
        if repetition_count == 1
        else f"means of {repetition_count} runs per point"
    )
    lines = [
        "% Generated by experiments/parameter_sensitivity.py; "
        f"values use {value_description}."
    ]
    previous_group = None
    for row in rows:
        if previous_group is not None and row["sensitivity_group"] != previous_group:
            lines.append(r"\midrule")
        previous_group = row["sensitivity_group"]
        lines.append(
            "{} & {} & {} & {:.3f} & {:.3f} & {:.3f} \\\\".format(
                row["sensitivity_group"],
                parameter_labels[row["parameter"]],
                _latex_escape_setting(row["setting"]),
                row["end_to_end_latency_seconds"],
                row["deadline_missing_rate"],
                row["qoe_score"],
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("generate", "run", "summarize"),
        help="generate configs, run the complete study, or summarize existing runs",
    )
    parser.add_argument("--base-task-config", type=Path, default=DEFAULT_TASK_CONFIG)
    parser.add_argument("--base-burst-config", type=Path, default=DEFAULT_BURST_CONFIG)
    parser.add_argument("--handler-config", type=Path, default=DEFAULT_HANDLER_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--method", default="feedback-fine-grained")
    parser.add_argument(
        "--repetitions",
        type=_positive_int,
        default=DEFAULT_REPETITIONS,
        help="runs per parameter point; defaults to 1",
    )
    parser.add_argument(
        "--seeds",
        type=_csv_ints,
        default=None,
        help=(
            "optional comma-separated seeds; when provided, overrides "
            "--repetitions"
        ),
    )
    parser.add_argument("--device", default="agx")
    parser.add_argument("--power-mode", default="MAXN")
    parser.add_argument(
        "--torch-device", default="cuda", choices=("auto", "cpu", "mps", "cuda", "cuda:0")
    )
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--cooldown-seconds", type=float, default=3.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument(
        "--allow-dirty", action="store_true",
        help="allow a dirty source tree; intended only for local validation",
    )
    return parser


def main():
    args = _build_parser().parse_args()
    if args.command == "summarize":
        report = summarize_study(args.output_root)
        print(
            f"Wrote table data for {len(report['points'])} points to "
            f"{Path(args.output_root).resolve() / 'report'}"
        )
        return 0

    source_status = _git_output("status", "--porcelain", "--", ".")
    if source_status and not args.allow_dirty:
        raise RuntimeError(
            "source tree is dirty; commit/stash changes or pass --allow-dirty "
            "for local validation:\n" + source_status
        )

    seeds = (
        args.seeds
        if args.seeds is not None
        else _seeds_for_repetitions(args.repetitions)
    )
    plan = generate_study_plan(
        args.base_task_config,
        args.base_burst_config,
        args.output_root,
        seeds=seeds,
        method=args.method,
    )
    print(
        f"Generated {len(plan['points'])} independent full-factorial points "
        f"({plan['planned_run_count']} runs)."
    )
    if args.command == "generate":
        return 0

    result = run_study(
        plan,
        args.handler_config,
        args.output_root,
        args.device,
        args.power_mode,
        args.torch_device,
        args.python,
        args.cooldown_seconds,
        dry_run=args.dry_run,
        resume=args.resume,
        keep_going=args.keep_going,
    )
    if result or args.dry_run:
        return result
    report = summarize_study(args.output_root)
    print(
        f"Study complete: {report['complete_run_count']} validated runs; "
        f"table files are in {Path(args.output_root).resolve() / 'report'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
