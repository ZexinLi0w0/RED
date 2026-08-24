#!/usr/bin/env python3
"""Run paired experiment matrices with immutable per-run provenance."""

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from task_generator import (  # noqa: E402
    generate_tasks_from_dag,
    load_dag_experiment_config,
    task_stream_sha256,
)
from runtime_device import torch_runtime_info  # noqa: E402


def _csv_values(raw_value):
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def _csv_ints(raw_value):
    try:
        return [int(value) for value in _csv_values(raw_value)]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seeds must be comma-separated integers") from exc


def _sha256_file(path):
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


def _write_json_atomic(path, value):
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    with open(temporary_path, "w", encoding="utf-8") as output_file:
        json.dump(value, output_file, indent=2, sort_keys=True)
        output_file.write("\n")
    os.replace(temporary_path, path)


def _offered_stream(config_path, seed):
    dag, timing, non_partitionable_percentage, non_partitionable_config, _ = (
        load_dag_experiment_config(config_path)
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
    return len(tasks), task_stream_sha256(tasks)


def _run_id(device, scenario, profile, method, seed, config_sha256):
    safe_method = method.replace("_", "-")
    return (
        f"{device}-{scenario}-{profile}-{safe_method}-seed{seed}-"
        f"cfg{config_sha256[:12]}"
    )


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True)
    parser.add_argument("--power-mode", required=True)
    parser.add_argument("--handler-config", type=Path, required=True)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--profiles", default="tight,loose")
    parser.add_argument(
        "--scenarios",
        default="urban_navigation,emergency_obstacle_avoidance,night_driving",
    )
    parser.add_argument(
        "--methods",
        default="baseline,llf-dag,feedback,fine-grained,feedback-fine-grained",
    )
    parser.add_argument("--seeds", type=_csv_ints, default=[101, 202, 303, 404, 505])
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--torch-device",
        default="auto",
        choices=("auto", "cpu", "mps", "cuda", "cuda:0"),
    )
    parser.add_argument("--cooldown-seconds", type=float, default=3.0)
    parser.add_argument("--burst-config", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-going", action="store_true")
    return parser


def main():
    args = _build_parser().parse_args()
    profiles = _csv_values(args.profiles)
    scenarios = _csv_values(args.scenarios)
    methods = _csv_values(args.methods)
    if not profiles or not scenarios or not methods or not args.seeds:
        raise ValueError("profiles, scenarios, methods, and seeds cannot be empty")
    if args.cooldown_seconds < 0:
        raise ValueError("cooldown-seconds cannot be negative")

    handler_config = args.handler_config.resolve()
    task_dir = args.task_dir.resolve()
    output_root = args.output_root.resolve()
    if not handler_config.is_file():
        raise FileNotFoundError(handler_config)

    runtime_info = torch_runtime_info(args.torch_device)

    git_commit = _git_output("rev-parse", "HEAD")
    git_status = _git_output("status", "--porcelain", "--", ".")
    failures = 0
    planned = 0

    for profile in profiles:
        for scenario in scenarios:
            config_path = task_dir / f"{args.device}_{profile}_{scenario}.json"
            if not config_path.is_file():
                raise FileNotFoundError(config_path)
            config_sha256 = _sha256_file(config_path)

            for seed in args.seeds:
                offered_task_count, offered_hash = _offered_stream(config_path, seed)
                for method in methods:
                    planned += 1
                    run_id = _run_id(
                        args.device,
                        scenario,
                        profile,
                        method,
                        seed,
                        config_sha256,
                    )
                    run_dir = output_root / run_id
                    manifest_path = run_dir / "manifest.json"
                    command = [
                        args.python,
                        str(REPOSITORY_ROOT / "main.py"),
                        "--config",
                        str(handler_config),
                        "--task",
                        str(config_path),
                        "--approach",
                        method,
                        "--seed",
                        str(seed),
                        "--output-dir",
                        str(run_dir),
                        "--run-id",
                        run_id,
                        "--torch-device",
                        runtime_info["resolved"],
                    ]
                    if args.burst_config:
                        command.extend(
                            ["--burst-config", str(args.burst_config.resolve())]
                        )

                    manifest = {
                        "schema_version": 1,
                        "run_id": run_id,
                        "status": "planned" if args.dry_run else "running",
                        "device": args.device,
                        "power_mode": args.power_mode,
                        "scenario": scenario,
                        "profile": profile,
                        "method": method,
                        "seed": seed,
                        "config_path": str(config_path),
                        "config_sha256": config_sha256,
                        "offered_task_count": offered_task_count,
                        "offered_task_stream_sha256": offered_hash,
                        "git_commit": git_commit,
                        "git_status_porcelain": git_status,
                        "python": args.python,
                        "torch_runtime": runtime_info,
                        "command": command,
                        "host": socket.gethostname(),
                        "platform": platform.platform(),
                    }

                    if args.dry_run:
                        print(json.dumps(manifest, sort_keys=True))
                        continue

                    if run_dir.exists():
                        if args.resume and manifest_path.is_file():
                            existing = json.loads(manifest_path.read_text())
                            if existing.get("status") == "complete":
                                print(f"SKIP complete {run_id}")
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
                        summary = json.loads(summary_path.read_text())
                        summary_matches = (
                            summary.get("run_id") == run_id
                            and summary.get("offered_task_count")
                            == offered_task_count
                            and summary.get("offered_task_stream_sha256")
                            == offered_hash
                        )
                        manifest["status"] = (
                            "complete" if summary_matches else "failed-validation"
                        )
                        manifest["summary_sha256"] = _sha256_file(summary_path)
                    else:
                        manifest["status"] = "failed"
                    _write_json_atomic(manifest_path, manifest)

                    if manifest["status"] != "complete":
                        failures += 1
                        print(f"FAIL {run_id}: {manifest['status']}", file=sys.stderr)
                        if not args.keep_going:
                            return 1
                    else:
                        print(f"DONE {run_id}")
                    if args.cooldown_seconds:
                        time.sleep(args.cooldown_seconds)

    if args.dry_run:
        print(f"Planned runs: {planned}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
