#!/usr/bin/env python3
"""Select Tight/Loose configs from completed EDF-only calibration runs."""

import argparse
import json
import os
import statistics
from collections import defaultdict
from pathlib import Path


TIGHT_TARGET = 0.50
TIGHT_INTERVAL = (0.30, 0.70)
LOOSE_TARGET = 0.10
LOOSE_INTERVAL = (0.05, 0.25)


def select_tight_loose(points):
    """Select an ordered alpha pair without consulting proposed-method data."""
    points = sorted(points, key=lambda point: point["deadline_alpha"])
    ordered_pairs = [
        (tight, loose)
        for tight in points
        for loose in points
        if tight["deadline_alpha"] < loose["deadline_alpha"]
    ]
    if not ordered_pairs:
        raise ValueError("at least two distinct deadline alphas are required")

    preferred_pairs = [
        pair
        for pair in ordered_pairs
        if TIGHT_INTERVAL[0] <= pair[0]["mean_deadline_missing_rate"] <= TIGHT_INTERVAL[1]
        and LOOSE_INTERVAL[0]
        <= pair[1]["mean_deadline_missing_rate"]
        <= LOOSE_INTERVAL[1]
    ]
    candidates = preferred_pairs or ordered_pairs

    def pair_distance(pair):
        tight, loose = pair
        return (
            abs(tight["mean_deadline_missing_rate"] - TIGHT_TARGET)
            + abs(loose["mean_deadline_missing_rate"] - LOOSE_TARGET),
            tight["deadline_alpha"],
            loose["deadline_alpha"],
        )

    tight, loose = min(candidates, key=pair_distance)
    return {
        "status": "ready" if preferred_pairs else "needs-grid-extension",
        "tight": tight,
        "loose": loose,
    }


def _load_index(index_path):
    index = json.loads(index_path.read_text(encoding="utf-8"))
    entries = {}
    for entry in index["configs"]:
        key = (entry["device"], entry["scenario"], entry["profile"])
        if key in entries:
            raise ValueError(f"duplicate calibration index entry: {key}")
        entries[key] = entry
    return index, entries


def _load_completed_edf_runs(runs_root, index_entries):
    grouped_runs = defaultdict(list)
    observed_commits = set()
    non_edf_runs = []

    for manifest_path in sorted(runs_root.rglob("manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("method") != "baseline":
            non_edf_runs.append(manifest.get("run_id", str(manifest_path)))
            continue
        if manifest.get("status") != "complete":
            continue

        key = (
            manifest["device"],
            manifest["scenario"],
            manifest["profile"],
        )
        if key not in index_entries:
            raise ValueError(f"completed run is not in calibration index: {key}")
        expected = index_entries[key]
        if manifest["config_sha256"] != expected["config_sha256"]:
            raise ValueError(f"config hash mismatch for {manifest['run_id']}")

        summary_path = manifest_path.parent / "summary.json"
        if not summary_path.is_file():
            raise FileNotFoundError(summary_path)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary["offered_task_stream_sha256"] != manifest[
            "offered_task_stream_sha256"
        ]:
            raise ValueError(f"offered-task hash mismatch for {manifest['run_id']}")
        grouped_runs[key].append(
            {
                "seed": manifest["seed"],
                "deadline_missing_rate": summary["deadline_missing_rate"],
                "run_id": manifest["run_id"],
                "power_mode": manifest["power_mode"],
            }
        )
        observed_commits.add(manifest["git_commit"])

    if non_edf_runs:
        raise ValueError(
            "calibration root contains non-EDF runs; blindness gate failed: "
            + ", ".join(non_edf_runs[:5])
        )
    if len(observed_commits) > 1:
        raise ValueError(
            f"calibration runs span multiple code commits: {sorted(observed_commits)}"
        )
    return grouped_runs, sorted(observed_commits)


def build_report(index_path, runs_root, minimum_repetitions=3):
    index, entries = _load_index(index_path)
    grouped_runs, commits = _load_completed_edf_runs(runs_root, entries)
    points_by_workload = defaultdict(list)
    missing_profiles = []

    for key, entry in sorted(entries.items()):
        runs = grouped_runs.get(key, [])
        seeds = [run["seed"] for run in runs]
        if len(seeds) != len(set(seeds)):
            raise ValueError(f"duplicate seed for calibration point {key}")
        if len(runs) < minimum_repetitions:
            missing_profiles.append(
                {
                    "device": key[0],
                    "scenario": key[1],
                    "profile": key[2],
                    "completed_repetitions": len(runs),
                }
            )
            continue
        power_modes = sorted({run["power_mode"] for run in runs})
        if len(power_modes) != 1:
            raise ValueError(f"multiple power modes for calibration point {key}")
        rates = [float(run["deadline_missing_rate"]) for run in runs]
        points_by_workload[(key[0], key[1])].append(
            {
                "profile": key[2],
                "deadline_alpha": entry["deadline_alpha"],
                "config_path": entry["config_path"],
                "config_sha256": entry["config_sha256"],
                "arrival_scale": entry["arrival_scale"],
                "repetitions": len(runs),
                "seeds": sorted(seeds),
                "power_mode": power_modes[0],
                "mean_deadline_missing_rate": statistics.fmean(rates),
                "stdev_deadline_missing_rate": (
                    statistics.stdev(rates) if len(rates) > 1 else 0.0
                ),
                "run_ids": sorted(run["run_id"] for run in runs),
            }
        )

    selections = []
    for workload, points in sorted(points_by_workload.items()):
        expected_count = sum(
            1 for key in entries if key[:2] == workload
        )
        if len(points) != expected_count:
            continue
        selection = select_tight_loose(points)
        sorted_points = sorted(points, key=lambda point: point["deadline_alpha"])
        inversions = [
            {
                "lower_alpha": previous["deadline_alpha"],
                "higher_alpha": current["deadline_alpha"],
                "increase": current["mean_deadline_missing_rate"]
                - previous["mean_deadline_missing_rate"],
            }
            for previous, current in zip(sorted_points, sorted_points[1:])
            if current["mean_deadline_missing_rate"]
            > previous["mean_deadline_missing_rate"] + 0.10
        ]
        if inversions:
            selection["status"] = "needs-monotonicity-review"
        selections.append(
            {
                "device": workload[0],
                "scenario": workload[1],
                "status": selection["status"],
                "tight": selection["tight"],
                "loose": selection["loose"],
                "monotonicity_inversions": inversions,
                "all_points": sorted_points,
            }
        )

    expected_workloads = len({key[:2] for key in entries})
    ready_to_freeze = (
        not missing_profiles
        and len(selections) == expected_workloads
        and all(selection["status"] == "ready" for selection in selections)
    )
    return {
        "schema_version": 1,
        "selection_source": "EDF-only completed runs",
        "calibration_index": str(index_path),
        "code_commits": commits,
        "minimum_repetitions": minimum_repetitions,
        "ready_to_freeze": ready_to_freeze,
        "missing_profiles": missing_profiles,
        "selections": selections,
        "targets": {
            "tight": {"center": TIGHT_TARGET, "interval": TIGHT_INTERVAL},
            "loose": {"center": LOOSE_TARGET, "interval": LOOSE_INTERVAL},
        },
        "index_selection_method": index["selection_method"],
    }


def _write_json_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary_path, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-index", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.minimum_repetitions <= 0:
        raise ValueError("minimum-repetitions must be positive")

    report = build_report(
        args.calibration_index.resolve(),
        args.runs_root.resolve(),
        args.minimum_repetitions,
    )
    _write_json_atomic(args.output.resolve(), report)
    print(json.dumps({"ready_to_freeze": report["ready_to_freeze"]}))
    return 0 if report["ready_to_freeze"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
