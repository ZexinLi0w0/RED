#!/usr/bin/env python3
"""Build and select Nano1 Non-partitionable-task experiment configs."""

import argparse
import json
import math
from pathlib import Path


DEFAULT_DEADLINE_FACTORS = (0.1, 0.25, 0.5, 1.0)
DEFAULT_ARRIVAL_SCALES = (0.25, 0.5, 1.0)
METHODS = ("baseline", "feedback-fine-grained")


def _factor_label(value):
    scaled = value * 100
    if not math.isclose(scaled, round(scaled)):
        raise ValueError("factor labels support at most two decimal places")
    return f"{round(scaled):03d}"


def _write_json(path, value):
    payload = json.dumps(value, indent=2, sort_keys=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != payload:
        raise FileExistsError(f"refusing to replace different config: {path}")
    path.write_text(payload, encoding="utf-8")


def _base_config(source_path):
    config = json.loads(source_path.read_text(encoding="utf-8"))
    required = {"DeadlineFactor", "ArrivalScale", "dag_list"}
    missing = required.difference(config)
    if missing:
        raise ValueError(f"source config is missing {sorted(missing)}")
    config.pop("RunningTimeFactor", None)
    config["QoELambda"] = 0.05
    config["TaskSeed"] = 0
    return config


def build_calibration(source_path, output_dir):
    entries = []
    for deadline_factor in DEFAULT_DEADLINE_FACTORS:
        for arrival_scale in DEFAULT_ARRIVAL_SCALES:
            config = _base_config(source_path)
            config.update(
                {
                    "DeadlineFactor": deadline_factor,
                    "ArrivalScale": arrival_scale,
                    "DagRepeatedTimes": 3,
                    "NonPartitionablePercentage": 50,
                    "Calibration": {
                        "device": "nano1",
                        "kind": "non-partitionable-load-grid",
                        "source_config": source_path.name,
                        "deadline_factor": deadline_factor,
                        "arrival_scale": arrival_scale,
                        "non_partitionable_percentage": 50,
                    },
                }
            )
            scenario = (
                f"d{_factor_label(deadline_factor)}_"
                f"a{_factor_label(arrival_scale)}_p050"
            )
            output_path = output_dir / f"nano1_cal_{scenario}.json"
            _write_json(output_path, config)
            entries.append(
                {
                    "profile": "cal",
                    "scenario": scenario,
                    "deadline_factor": deadline_factor,
                    "arrival_scale": arrival_scale,
                    "config_path": output_path.name,
                }
            )
    index = {
        "schema_version": 1,
        "device": "nano1",
        "phase": "calibration",
        "methods": list(METHODS),
        "selection_rule": (
            "prefer interior Deadline Missing Rate for both methods and "
            "non-saturated QoE"
        ),
        "configs": entries,
    }
    _write_json(output_dir / "calibration_index.json", index)
    return index


def build_formal(
    source_path,
    output_dir,
    deadline_factor,
    arrival_scale,
    repetitions,
):
    entries = []
    for percentage in (0, 50, 100):
        config = _base_config(source_path)
        config.update(
            {
                "DeadlineFactor": deadline_factor,
                "ArrivalScale": arrival_scale,
                "DagRepeatedTimes": repetitions,
                "NonPartitionablePercentage": percentage,
                "FormalExperiment": {
                    "device": "nano1",
                    "kind": "non-partitionable-task",
                    "source_config": source_path.name,
                    "deadline_factor": deadline_factor,
                    "arrival_scale": arrival_scale,
                    "non_partitionable_percentage": percentage,
                },
            }
        )
        scenario = f"nonpartition_{percentage:03d}"
        output_path = output_dir / f"nano1_balanced_{scenario}.json"
        _write_json(output_path, config)
        entries.append(
            {
                "profile": "balanced",
                "scenario": scenario,
                "non_partitionable_percentage": percentage,
                "config_path": output_path.name,
            }
        )
    index = {
        "schema_version": 1,
        "device": "nano1",
        "phase": "formal",
        "methods": list(METHODS),
        "deadline_factor": deadline_factor,
        "arrival_scale": arrival_scale,
        "dag_repeated_times": repetitions,
        "configs": entries,
    }
    _write_json(output_dir / "formal_index.json", index)
    return index


def _metric(summary, name):
    value = summary.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"summary has no numeric {name}")
    if not math.isfinite(value):
        raise ValueError(f"summary has non-finite {name}")
    return float(value)


def _candidate_score(records):
    if set(records) != set(METHODS):
        return math.inf
    deadline_rates = [
        _metric(records[method], "deadline_missing_rate") for method in METHODS
    ]
    qoe_scores = [_metric(records[method], "qoe_score") for method in METHODS]
    score = abs(deadline_rates[0] - 0.65) + abs(deadline_rates[1] - 0.35)
    score += 0.5 * sum(
        max(0.0, 0.05 - value) + max(0.0, value - 0.95)
        for value in deadline_rates
    )
    if all(value >= 0.995 for value in qoe_scores):
        score += 4.0
    if all(value <= 0.005 for value in qoe_scores):
        score += 4.0
    score += max(0.0, 0.05 - abs(qoe_scores[0] - qoe_scores[1]))
    return score


def select_calibration(runs_root):
    grouped = {}
    for manifest_path in sorted(runs_root.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "complete":
            continue
        scenario = manifest.get("scenario")
        method = manifest.get("method")
        if method not in METHODS or not isinstance(scenario, str):
            continue
        summary_path = manifest_path.with_name("summary.json")
        if not summary_path.is_file():
            continue
        grouped.setdefault(scenario, {})[method] = json.loads(
            summary_path.read_text(encoding="utf-8")
        )
    ranked = []
    for scenario, records in grouped.items():
        score = _candidate_score(records)
        if math.isfinite(score):
            parts = scenario.split("_")
            deadline_factor = int(parts[0][1:]) / 100
            arrival_scale = int(parts[1][1:]) / 100
            ranked.append(
                {
                    "scenario": scenario,
                    "deadline_factor": deadline_factor,
                    "arrival_scale": arrival_scale,
                    "score": score,
                    "metrics": {
                        method: {
                            "deadline_missing_rate": _metric(
                                records[method], "deadline_missing_rate"
                            ),
                            "qoe_score": _metric(records[method], "qoe_score"),
                            "end_to_end_latency_seconds": _metric(
                                records[method], "end_to_end_latency_seconds"
                            ),
                        }
                        for method in METHODS
                    },
                }
            )
    ranked.sort(key=lambda item: (item["score"], item["scenario"]))
    if not ranked:
        raise ValueError(f"no complete paired calibration results in {runs_root}")
    return {"selected": ranked[0], "ranked": ranked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    calibration = subparsers.add_parser("build-calibration")
    calibration.add_argument("--source", type=Path, required=True)
    calibration.add_argument("--output-dir", type=Path, required=True)

    formal = subparsers.add_parser("build-formal")
    formal.add_argument("--source", type=Path, required=True)
    formal.add_argument("--output-dir", type=Path, required=True)
    formal.add_argument("--deadline-factor", type=float, required=True)
    formal.add_argument("--arrival-scale", type=float, required=True)
    formal.add_argument("--repetitions", type=int, default=10)

    select = subparsers.add_parser("select")
    select.add_argument("--runs-root", type=Path, required=True)
    select.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "build-calibration":
        result = build_calibration(args.source.resolve(), args.output_dir.resolve())
    elif args.command == "build-formal":
        if args.deadline_factor <= 0 or args.arrival_scale <= 0:
            parser.error("timing factors must be positive")
        if args.repetitions <= 0:
            parser.error("repetitions must be positive")
        result = build_formal(
            args.source.resolve(),
            args.output_dir.resolve(),
            args.deadline_factor,
            args.arrival_scale,
            args.repetitions,
        )
    else:
        result = select_calibration(args.runs_root.resolve())
        if args.output:
            _write_json(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
