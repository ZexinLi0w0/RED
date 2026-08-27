#!/usr/bin/env python3
"""Apply a measured SIMONet runtime profile to platform task configs."""

import argparse
import hashlib
import json
import os
from pathlib import Path


RUN_ARGS_TO_CASE = {
    (1,): "lane_detection",
    (2,): "control_autopilot",
    (3,): "segmentation",
    (4,): "object_detection",
}


def _sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _profile_values(profile, run_args):
    key = tuple(int(value) for value in run_args)
    if key not in RUN_ARGS_TO_CASE:
        raise ValueError(f"no runtime-profile case for RunArgs={list(key)}")
    case_name = RUN_ARGS_TO_CASE[key]
    case = profile["cases"][case_name]
    return case_name, case["mean_ms"], case["profiled_execution_bound_ms"]


def apply_profile(profile_path, source_dir, device_prefix):
    profile_path = profile_path.resolve()
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    resolved_device = profile["torch_runtime"]["resolved"]
    profile_sha256 = _sha256_file(profile_path)
    source_paths = sorted(source_dir.glob(f"{device_prefix}_loose_*.json"))
    if not source_paths:
        raise FileNotFoundError(
            f"no {device_prefix}_loose_*.json files found in {source_dir}"
        )

    changed_paths = []
    for source_path in source_paths:
        config = json.loads(source_path.read_text(encoding="utf-8"))
        used_cases = set()
        for dag in config["dag_list"]:
            for stage in dag:
                tasks = stage if isinstance(stage, list) else [stage]
                for task in tasks:
                    case_name, mean_ms, bound_ms = _profile_values(
                        profile, task["RunArgs"]
                    )
                    used_cases.add(case_name)
                    task["RunningTime"] = round(mean_ms, 6)
                    task["WorstRunningTime"] = round(bound_ms, 6)

        config["RuntimeProfile"] = {
            "profile_file": profile_path.name,
            "profile_sha256": profile_sha256,
            "torch_device": resolved_device,
            "power_mode": profile["power_mode"],
            "bound_policy": profile["bound_policy"],
            "bound_margin_fraction": profile["bound_margin_fraction"],
            "cases": sorted(used_cases),
        }
        payload = json.dumps(config, indent=2, sort_keys=False) + "\n"
        if source_path.read_text(encoding="utf-8") == payload:
            continue
        temporary_path = source_path.with_suffix(".json.tmp")
        temporary_path.write_text(payload, encoding="utf-8")
        os.replace(temporary_path, source_path)
        changed_paths.append(source_path)
    return changed_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--device-prefix", required=True)
    args = parser.parse_args()
    changed_paths = apply_profile(
        args.profile, args.source_dir.resolve(), args.device_prefix
    )
    print(f"Updated {len(changed_paths)} task configs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
