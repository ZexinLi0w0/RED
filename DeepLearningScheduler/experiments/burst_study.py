#!/usr/bin/env python3
"""Run and summarize the paper's transient/sustained Burst study."""

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import platform
import random
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from burst_task_manager import (  # noqa: E402
    BurstTaskManager,
    burst_workload_config_from_mapping,
)
from experiments.result_presentation import (  # noqa: E402
    format_truncated,
    select_representative,
)
from runtime_device import torch_runtime_info  # noqa: E402
from task_generator import (  # noqa: E402
    generate_tasks_from_dag,
    load_dag_experiment_config,
    task_stream_sha256,
)


DEFAULT_BASE_TASK_CONFIG = (
    REPOSITORY_ROOT / "TaskConfigs" / "simo" / "mac_loose_burst.json"
)
DEFAULT_HANDLER_CONFIG = REPOSITORY_ROOT / "simo-handler_config.json"
DEFAULT_OUTPUT_ROOT = (
    REPOSITORY_ROOT / "taskdata" / "major_revision_burst_mac_mps_v2"
)
DEFAULT_SEEDS = (101, 202, 303, 404, 505)
DEFAULT_DEADLINE_FACTOR = 0.2
DEFAULT_ARRIVAL_SCALE = 0.2
DEFAULT_BURST_START_SECONDS = 0.36
DEFAULT_TRANSIENT_DURATION_SECONDS = 0.6
DEFAULT_RELEASE_HORIZON_SECONDS = 1.96
DEFAULT_RUN_ORDER_SEED = 20260827
METHODS = ("baseline", "llf-dag", "feedback-fine-grained")
METHOD_LABELS = {
    "baseline": "EDF",
    "llf-dag": "LLF-DAG",
    "feedback-fine-grained": "RED",
}
METRICS = (
    "end_to_end_latency_seconds",
    "deadline_missing_rate",
    "qoe_score",
)


@dataclass(frozen=True)
class BurstCondition:
    slug: str
    regime: str
    ratio_percent: int
    transient_duration_seconds: float | None = None


# The zero-Burst control is executed once and reused in both table regimes.
CONDITIONS = (
    BurstCondition("control-000", "sustained", 0),
    BurstCondition(
        "transient-050", "transient", 50,
        DEFAULT_TRANSIENT_DURATION_SECONDS,
    ),
    BurstCondition(
        "transient-100", "transient", 100,
        DEFAULT_TRANSIENT_DURATION_SECONDS,
    ),
    BurstCondition("sustained-050", "sustained", 50),
    BurstCondition("sustained-100", "sustained", 100),
)


def _load_json(path):
    with open(path, encoding="utf-8") as input_file:
        return json.load(input_file)


def _write_json_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    with open(temporary, "w", encoding="utf-8") as output_file:
        json.dump(value, output_file, indent=2, sort_keys=True)
        output_file.write("\n")
    os.replace(temporary, path)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _burst_config(
    condition,
    burst_start_seconds=DEFAULT_BURST_START_SECONDS,
    release_horizon_seconds=DEFAULT_RELEASE_HORIZON_SECONDS,
):
    config = {
        "burst_enabled": True,
        "burst_regime": condition.regime,
        "burst_start_seconds": burst_start_seconds,
        "release_horizon_seconds": release_horizon_seconds,
        "gpu_threshold": 90.0,
        "queue_threshold": 8,
        "persistence_window": 3,
        "drop_threshold": 0.5,
        "monitoring_interval": 0.05,
        "scheduler_tick_seconds": 0.005,
    }
    if condition.transient_duration_seconds is not None:
        config["transient_duration_seconds"] = (
            condition.transient_duration_seconds
        )
    return config


def _offered_stream(task_config_path, burst_config_path, seed):
    dag, timing, non_partitionable_percentage, non_partitionable_config, ratio = (
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
    manager = BurstTaskManager(
        gpu_threshold=burst_config["gpu_threshold"],
        queue_threshold=burst_config["queue_threshold"],
        persistence_window=burst_config["persistence_window"],
        default_drop_threshold=burst_config["drop_threshold"],
        monitoring_interval=burst_config["monitoring_interval"],
        workload_config=burst_workload_config_from_mapping(burst_config),
        management_enabled=False,
    )
    tasks = tasks + manager.generate_burst_tasks(tasks, ratio)
    return {
        "offered_task_count": len(tasks),
        "offered_task_stream_sha256": task_stream_sha256(tasks),
        "workload": manager.get_burst_statistics()["workload"],
    }


def generate_study_plan(
    base_task_config=DEFAULT_BASE_TASK_CONFIG,
    output_root=DEFAULT_OUTPUT_ROOT,
    seeds=DEFAULT_SEEDS,
    deadline_factor=DEFAULT_DEADLINE_FACTOR,
    arrival_scale=DEFAULT_ARRIVAL_SCALE,
    burst_start_seconds=DEFAULT_BURST_START_SECONDS,
    release_horizon_seconds=DEFAULT_RELEASE_HORIZON_SECONDS,
):
    base_task_config = Path(base_task_config).resolve()
    output_root = Path(output_root).resolve()
    template = _load_json(base_task_config)
    if not template.get("dag_list"):
        raise ValueError("base task config must contain a non-empty dag_list")
    generated_root = output_root / "generated_configs"
    condition_records = []
    for condition in CONDITIONS:
        task_config = json.loads(json.dumps(template))
        task_config.pop("RunningTimeFactor", None)
        task_config.update(
            {
                "DeadlineFactor": deadline_factor,
                "ArrivalScale": arrival_scale,
                "BurstTaskRatio": condition.ratio_percent,
                "ReleaseTimeSkewThresholdMs": 100.0,
                "MovingAverageWindow": 8,
                "QoELambda": 0.05,
            }
        )
        burst_config = _burst_config(
            condition,
            burst_start_seconds=burst_start_seconds,
            release_horizon_seconds=release_horizon_seconds,
        )
        task_path = generated_root / condition.slug / "task.json"
        burst_path = generated_root / condition.slug / "burst.json"
        _write_json_atomic(task_path, task_config)
        _write_json_atomic(burst_path, burst_config)
        offered = _offered_stream(task_path, burst_path, seeds[0])
        condition_records.append(
            {
                **asdict(condition),
                "task_config_path": str(task_path),
                "task_config_sha256": _sha256(task_path),
                "burst_config_path": str(burst_path),
                "burst_config_sha256": _sha256(burst_path),
                "expected_workload": offered["workload"],
                "expected_offered_task_count": offered["offered_task_count"],
            }
        )

    plan = {
        "schema_version": 1,
        "study": "transient-sustained-burst",
        "device": "mac",
        "platform_label": "M3 Max",
        "power_mode": "AC power; default macOS policy",
        "torch_device": "mps",
        "methods": list(METHODS),
        "method_labels": METHOD_LABELS,
        "seeds": list(seeds),
        "repetitions_per_cell": len(seeds),
        "base_task_config": str(base_task_config),
        "base_task_config_sha256": _sha256(base_task_config),
        "deadline_factor": deadline_factor,
        "arrival_scale": arrival_scale,
        "burst_start_seconds": burst_start_seconds,
        "release_horizon_seconds": release_horizon_seconds,
        "conditions": condition_records,
        "planned_run_count": len(condition_records) * len(METHODS) * len(seeds),
        "run_order": "fixed pseudo-random permutation of all cases",
        "run_order_seed": DEFAULT_RUN_ORDER_SEED,
        "zero_burst_control_reused_between_regimes": True,
    }
    _write_json_atomic(output_root / "study_plan.json", plan)
    return plan


def _run_id(condition, method, seed, task_hash, burst_hash):
    return (
        f"burst-mac-{condition['slug']}-{method}-seed{seed}-"
        f"task{task_hash[:8]}-burst{burst_hash[:8]}"
    )


def _validate_summary(manifest, summary):
    problems = []
    for field in ("run_id", "method", "offered_task_count", "offered_task_stream_sha256"):
        if summary.get(field) != manifest.get(field):
            problems.append(f"{field} mismatch")
    for metric in METRICS:
        value = summary.get(metric)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            problems.append(f"invalid metric {metric}")
    if summary.get("outcome_counts", {}).get("execution_error", 0):
        problems.append("execution_error outcomes present")
    burst = summary.get("burst_statistics") or {}
    expected_management = manifest["method"] == "feedback-fine-grained"
    if burst.get("management_enabled") is not expected_management:
        problems.append("burst management enablement mismatch")
    workload = burst.get("workload") or {}
    for field, expected in manifest["expected_workload"].items():
        if workload.get(field) != expected:
            problems.append(f"workload field mismatch: {field}")
    return problems


def run_study(
    plan,
    handler_config=DEFAULT_HANDLER_CONFIG,
    output_root=DEFAULT_OUTPUT_ROOT,
    python_executable=sys.executable,
    cooldown_seconds=2.0,
    dry_run=False,
    resume=False,
    keep_going=False,
):
    output_root = Path(output_root).resolve()
    handler_config = Path(handler_config).resolve()
    runtime = (
        {"requested": "mps", "resolved": "mps", "probe": "dry-run"}
        if dry_run
        else torch_runtime_info("mps")
    )
    git_commit = _git_output("rev-parse", "HEAD")
    git_status = _git_output("status", "--porcelain", "--", ".")
    failures = 0
    cases = [
        (condition, seed, method)
        for condition in plan["conditions"]
        for seed in plan["seeds"]
        for method in plan["methods"]
    ]
    random.Random(plan["run_order_seed"]).shuffle(cases)
    for run_order_index, (condition, seed, method) in enumerate(cases, start=1):
                task_path = Path(condition["task_config_path"])
                burst_path = Path(condition["burst_config_path"])
                offered = _offered_stream(task_path, burst_path, seed)
                run_id = _run_id(
                    condition,
                    method,
                    seed,
                    condition["task_config_sha256"],
                    condition["burst_config_sha256"],
                )
                run_dir = output_root / "runs" / run_id
                manifest_path = run_dir / "manifest.json"
                command = [
                    python_executable,
                    str(REPOSITORY_ROOT / "main.py"),
                    "--config", str(handler_config),
                    "--task", str(task_path),
                    "--approach", method,
                    "--seed", str(seed),
                    "--output-dir", str(run_dir),
                    "--run-id", run_id,
                    "--torch-device", runtime["resolved"],
                    "--burst-config", str(burst_path),
                ]
                manifest = {
                    "schema_version": 1,
                    "study": plan["study"],
                    "run_id": run_id,
                    "status": "planned" if dry_run else "running",
                    "device": plan["device"],
                    "platform_label": plan["platform_label"],
                    "power_mode": plan["power_mode"],
                    "condition_slug": condition["slug"],
                    "regime": condition["regime"],
                    "ratio_percent": condition["ratio_percent"],
                    "method": method,
                    "seed": seed,
                    "run_order_index": run_order_index,
                    "run_order_seed": plan["run_order_seed"],
                    "task_config_path": str(task_path),
                    "task_config_sha256": condition["task_config_sha256"],
                    "burst_config_path": str(burst_path),
                    "burst_config_sha256": condition["burst_config_sha256"],
                    **offered,
                    "expected_workload": condition["expected_workload"],
                    "git_commit": git_commit,
                    "git_status_porcelain": git_status,
                    "python": python_executable,
                    "torch_runtime": runtime,
                    "host": socket.gethostname(),
                    "platform": platform.platform(),
                    "command": command,
                }
                # Avoid duplicating workload metadata under two names.
                manifest.pop("workload", None)
                if dry_run:
                    print(json.dumps(manifest, sort_keys=True))
                    continue
                if run_dir.exists():
                    if resume and manifest_path.is_file():
                        existing = _load_json(manifest_path)
                        if existing.get("status") == "complete":
                            print(f"SKIP complete {run_id}", flush=True)
                            continue
                    raise FileExistsError(
                        f"refusing to overwrite existing run directory: {run_dir}"
                    )
                run_dir.mkdir(parents=True)
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
                    manifest["validation_problems"] = _validate_summary(
                        manifest, summary
                    )
                    manifest["status"] = (
                        "complete"
                        if not manifest["validation_problems"]
                        else "failed-validation"
                    )
                    manifest["summary_sha256"] = _sha256(summary_path)
                else:
                    manifest["status"] = "failed"
                _write_json_atomic(manifest_path, manifest)
                if manifest["status"] != "complete":
                    failures += 1
                    print(f"FAIL {run_id}: {manifest['status']}", flush=True)
                    if not keep_going:
                        return 1
                else:
                    print(f"DONE {run_id}", flush=True)
                if cooldown_seconds:
                    time.sleep(cooldown_seconds)
    return 1 if failures else 0


def _paper_record(run):
    summary = run["summary"]
    return {
        "run_id": run["manifest"]["run_id"],
        "seed": run["manifest"]["seed"],
        **{metric: summary[metric] for metric in METRICS},
    }


def _drop_composition(summary):
    burst = summary["burst_statistics"]
    records = burst.get("drop_records", [])
    band_counts = {"low": 0, "medium": 0, "high": 0}
    for record in records:
        score = float(record["criticality_score"])
        band = "low" if score < 1 / 3 else "medium" if score < 2 / 3 else "high"
        weight = len(record.get("constituent_task_ids", [])) or 1
        band_counts[band] += weight
    dropped = summary.get("outcome_counts", {}).get("burst_drop", 0)
    if sum(band_counts.values()) != dropped:
        raise ValueError("drop-record composition does not match offered-node outcomes")
    offered = summary["offered_task_count"]
    return {
        "dropped_offered_nodes": dropped,
        "offered_nodes": offered,
        "dropped_fraction": dropped / offered,
        "criticality_score_bands": {
            "low": "[0, 1/3)",
            "medium": "[1/3, 2/3)",
            "high": "[2/3, 1]",
        },
        "band_counts": band_counts,
        "band_shares": {
            band: (count / dropped if dropped else 0.0)
            for band, count in band_counts.items()
        },
    }


def summarize_study(output_root=DEFAULT_OUTPUT_ROOT):
    output_root = Path(output_root).resolve()
    plan = _load_json(output_root / "study_plan.json")
    runs_by_group = {}
    problems = []
    for manifest_path in sorted((output_root / "runs").glob("*/manifest.json")):
        manifest = _load_json(manifest_path)
        if manifest.get("status") != "complete":
            problems.append(f"{manifest_path.parent.name}: status={manifest.get('status')}")
            continue
        summary_path = manifest_path.parent / "summary.json"
        if not summary_path.is_file() or _sha256(summary_path) != manifest.get(
            "summary_sha256"
        ):
            problems.append(f"{manifest_path.parent.name}: invalid summary artifact")
            continue
        summary = _load_json(summary_path)
        for problem in _validate_summary(manifest, summary):
            problems.append(f"{manifest_path.parent.name}: {problem}")
        key = (manifest["condition_slug"], manifest["method"])
        runs_by_group.setdefault(key, []).append(
            {"manifest": manifest, "summary": summary}
        )

    expected_seeds = set(plan["seeds"])
    representatives = {}
    for condition in plan["conditions"]:
        condition_hashes = {}
        for method in plan["methods"]:
            key = (condition["slug"], method)
            runs = runs_by_group.get(key, [])
            seeds = [run["manifest"]["seed"] for run in runs]
            if set(seeds) != expected_seeds or len(seeds) != len(expected_seeds):
                problems.append(f"{key}: incomplete or duplicate seeds {seeds}")
                continue
            for run in runs:
                seed = run["manifest"]["seed"]
                condition_hashes.setdefault(seed, set()).add(
                    run["manifest"]["offered_task_stream_sha256"]
                )
            records = [_paper_record(run) for run in runs]
            selected = select_representative(records, key)
            selected_run = next(
                run for run in runs if run["manifest"]["run_id"] == selected["run_id"]
            )
            representatives[key] = {
                "run_id": selected["run_id"],
                "seed": selected["seed"],
                "raw_metrics": {metric: selected[metric] for metric in METRICS},
                "display_metrics": {
                    metric: format_truncated(selected[metric]) for metric in METRICS
                },
                "summary": selected_run["summary"],
            }
        for seed, hashes in condition_hashes.items():
            if len(hashes) != 1:
                problems.append(
                    f"{condition['slug']} seed {seed}: methods received different workloads"
                )
    if problems:
        raise ValueError("Burst artifact validation failed:\n" + "\n".join(problems))

    table_rows = []
    for regime in ("transient", "sustained"):
        for ratio in (0, 50, 100):
            slug = "control-000" if ratio == 0 else f"{regime}-{ratio:03d}"
            row = {"regime": regime, "ratio_percent": ratio}
            for method in plan["methods"]:
                presentation = representatives[(slug, method)]
                label = plan["method_labels"][method]
                row[label] = presentation["display_metrics"]
                row[f"{label}_run_id"] = presentation["run_id"]
                row[f"{label}_seed"] = presentation["seed"]
            table_rows.append(row)

    drop_composition = {}
    for regime in ("transient", "sustained"):
        representative = representatives[
            (f"{regime}-100", "feedback-fine-grained")
        ]
        drop_composition[regime] = {
            "run_id": representative["run_id"],
            "seed": representative["seed"],
            **_drop_composition(representative["summary"]),
        }

    report = {
        "schema_version": 1,
        "study": plan["study"],
        "selection_rule": (
            "one complete median run by end-to-end latency from five repetitions; "
            "all paper metrics come from that same run"
        ),
        "precision_rule": "truncate to three decimal places without rounding",
        "table_rows": table_rows,
        "drop_composition": drop_composition,
    }
    report_root = output_root / "report"
    _write_json_atomic(report_root / "burst_report.json", report)
    report_root.mkdir(parents=True, exist_ok=True)
    with open(report_root / "burst_table.csv", "w", newline="", encoding="utf-8") as output_file:
        fieldnames = ["regime", "ratio_percent"] + [
            f"{label}_{metric}"
            for label in ("EDF", "LLF-DAG", "RED")
            for metric in METRICS
        ]
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in table_rows:
            flat = {"regime": row["regime"], "ratio_percent": row["ratio_percent"]}
            for label in ("EDF", "LLF-DAG", "RED"):
                for metric in METRICS:
                    flat[f"{label}_{metric}"] = row[label][metric]
            writer.writerow(flat)
    return report


def _csv_ints(value):
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--base-task-config", type=Path, default=DEFAULT_BASE_TASK_CONFIG)
    plan_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    plan_parser.add_argument("--seeds", type=_csv_ints, default=DEFAULT_SEEDS)
    plan_parser.add_argument(
        "--deadline-factor", type=float, default=DEFAULT_DEADLINE_FACTOR
    )
    plan_parser.add_argument(
        "--arrival-scale", type=float, default=DEFAULT_ARRIVAL_SCALE
    )
    plan_parser.add_argument(
        "--burst-start-seconds",
        type=float,
        default=DEFAULT_BURST_START_SECONDS,
    )
    plan_parser.add_argument(
        "--release-horizon-seconds",
        type=float,
        default=DEFAULT_RELEASE_HORIZON_SECONDS,
    )
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    run_parser.add_argument("--handler-config", type=Path, default=DEFAULT_HANDLER_CONFIG)
    run_parser.add_argument("--python", default=sys.executable)
    run_parser.add_argument("--cooldown-seconds", type=float, default=2.0)
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--resume", action="store_true")
    run_parser.add_argument("--keep-going", action="store_true")
    summarize_parser = subparsers.add_parser("summarize")
    summarize_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser


def main():
    args = _build_parser().parse_args()
    if args.command == "plan":
        plan = generate_study_plan(
            args.base_task_config,
            args.output_root,
            args.seeds,
            args.deadline_factor,
            args.arrival_scale,
            args.burst_start_seconds,
            args.release_horizon_seconds,
        )
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if args.command == "run":
        plan = _load_json(args.output_root.resolve() / "study_plan.json")
        return run_study(
            plan,
            args.handler_config,
            args.output_root,
            args.python,
            args.cooldown_seconds,
            args.dry_run,
            args.resume,
            args.keep_going,
        )
    report = summarize_study(args.output_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
