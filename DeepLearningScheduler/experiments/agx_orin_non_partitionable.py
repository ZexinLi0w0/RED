#!/usr/bin/env python3
"""Build and select AGX Orin Non-partitionable-task experiment configs."""

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path


DEFAULT_DEADLINE_FACTORS = (1.0, 2.0, 4.0, 8.0)
DEFAULT_ARRIVAL_SCALES = (0.75, 1.0, 1.25)
METHODS = ("baseline", "llf-dag", "feedback-fine-grained")
FORMAL_SEEDS = (101, 202, 303, 404, 505)
RUN_ARGS_TO_CASE = {
    (1,): "lane_detection",
    (2,): "control_autopilot",
    (3,): "segmentation",
    (4,): "object_detection",
}


def _factor_label(value):
    scaled = value * 100
    if not math.isclose(scaled, round(scaled)):
        raise ValueError("factor labels support at most two decimal places")
    return f"{round(scaled):03d}"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path, value):
    payload = json.dumps(value, indent=2, sort_keys=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != payload:
        raise FileExistsError(f"refusing to replace different config: {path}")
    path.write_text(payload, encoding="utf-8")


def build_source(template_path, profile_path, output_path):
    config = json.loads(template_path.read_text(encoding="utf-8"))
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile["torch_runtime"]["resolved"] not in {"cuda", "cuda:0"}:
        raise ValueError("AGX Orin runtime profile must use CUDA")

    used_cases = set()
    for dag in config["dag_list"]:
        for stage in dag:
            tasks = stage if isinstance(stage, list) else [stage]
            for task in tasks:
                run_args = tuple(int(value) for value in task["RunArgs"])
                try:
                    case_name = RUN_ARGS_TO_CASE[run_args]
                    case = profile["cases"][case_name]
                except KeyError as exc:
                    raise ValueError(
                        f"runtime profile has no case for RunArgs={list(run_args)}"
                    ) from exc
                task["RunningTime"] = round(case["mean_ms"], 6)
                task["WorstRunningTime"] = round(
                    case["profiled_execution_bound_ms"], 6
                )
                used_cases.add(case_name)

    config.pop("RunningTimeFactor", None)
    config.update(
        {
            "DeadlineFactor": 1.0,
            "ArrivalScale": 1.0,
            "DagRepeatedTimes": 10,
            "ParallelStagePolicy": "max",
            "TaskSeed": 0,
            "ReleaseTimeSkewThresholdMs": 20,
            "QoELambda": 0.05,
            "RuntimeProfile": {
                "profile_file": profile_path.name,
                "profile_sha256": _sha256(profile_path),
                "torch_device": profile["torch_runtime"]["resolved"],
                "power_mode": profile["power_mode"],
                "bound_policy": profile["bound_policy"],
                "bound_margin_fraction": profile["bound_margin_fraction"],
                "cases": sorted(used_cases),
            },
            "SourceExperiment": {
                "device": "agx_orin",
                "kind": "profiled-non-partitionable-source",
                "template_config": template_path.name,
                "runtime_profile": profile_path.name,
            },
        }
    )
    config.pop("MergeThresholdMs", None)
    _write_json(output_path, config)
    return config


def _base_config(source_path):
    config = json.loads(source_path.read_text(encoding="utf-8"))
    required = {
        "DeadlineFactor",
        "ArrivalScale",
        "dag_list",
        "RuntimeProfile",
    }
    missing = required.difference(config)
    if missing:
        raise ValueError(f"source config is missing {sorted(missing)}")
    config["QoELambda"] = 0.05
    config["TaskSeed"] = 0
    return config


def _positive_factors(values, name):
    values = tuple(float(value) for value in values)
    if not values or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError(f"{name} must contain positive finite values")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} cannot contain duplicates")
    return values


def _csv_factors(raw_value):
    try:
        return _positive_factors(raw_value.split(","), "timing factors")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_calibration(
    source_path,
    output_dir,
    deadline_factors=DEFAULT_DEADLINE_FACTORS,
    arrival_scales=DEFAULT_ARRIVAL_SCALES,
):
    deadline_factors = _positive_factors(deadline_factors, "deadline factors")
    arrival_scales = _positive_factors(arrival_scales, "arrival scales")
    entries = []
    for deadline_factor in deadline_factors:
        for arrival_scale in arrival_scales:
            config = _base_config(source_path)
            config.update(
                {
                    "DeadlineFactor": deadline_factor,
                    "ArrivalScale": arrival_scale,
                    "DagRepeatedTimes": 10,
                    "NonPartitionablePercentage": 50,
                    "Calibration": {
                        "device": "agx_orin",
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
            output_path = output_dir / f"agx_orin_cal_{scenario}.json"
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
        "device": "agx_orin",
        "phase": "calibration",
        "methods": list(METHODS),
        "selection_rule": (
            "prefer interior Deadline Missing Rate across all methods, "
            "non-saturated QoE, and method separation; freeze before formal runs"
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
    dag_repeated_times,
    selection_report_path=None,
):
    calibration_selection = None
    if selection_report_path is not None:
        report = json.loads(selection_report_path.read_text(encoding="utf-8"))
        selected = report["selected"]
        if not selected["quality_gate"]["accepted"]:
            raise ValueError("selected calibration candidate did not pass quality gate")
        if not math.isclose(selected["deadline_factor"], deadline_factor):
            raise ValueError("deadline factor does not match selection report")
        if not math.isclose(selected["arrival_scale"], arrival_scale):
            raise ValueError("arrival scale does not match selection report")
        minimum_samples = min(
            selected["metrics"][method]["sample_count"] for method in METHODS
        )
        if minimum_samples < 3:
            raise ValueError("selection report requires at least three paired seeds")
        calibration_selection = {
            "selection_report": selection_report_path.name,
            "selection_report_sha256": _sha256(selection_report_path),
            "scenario": selected["scenario"],
            "quality_gate": selected["quality_gate"],
            "metrics": selected["metrics"],
            "minimum_paired_seed_count": minimum_samples,
        }

    entries = []
    for percentage in (0, 50, 100):
        config = _base_config(source_path)
        config.update(
            {
                "DeadlineFactor": deadline_factor,
                "ArrivalScale": arrival_scale,
                "DagRepeatedTimes": dag_repeated_times,
                "NonPartitionablePercentage": percentage,
                "FormalExperiment": {
                    "device": "agx_orin",
                    "kind": "non-partitionable-task",
                    "source_config": source_path.name,
                    "deadline_factor": deadline_factor,
                    "arrival_scale": arrival_scale,
                    "non_partitionable_percentage": percentage,
                    "calibration_frozen_before_formal_runs": True,
                    "calibration_selection": calibration_selection,
                },
            }
        )
        scenario = f"nonpartition_{percentage:03d}"
        output_path = output_dir / f"agx_orin_balanced_{scenario}.json"
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
        "device": "agx_orin",
        "phase": "formal",
        "methods": list(METHODS),
        "seeds": list(FORMAL_SEEDS),
        "deadline_factor": deadline_factor,
        "arrival_scale": arrival_scale,
        "dag_repeated_times": dag_repeated_times,
        "calibration_selection": calibration_selection,
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


def _candidate_metrics(records):
    if set(records) != set(METHODS):
        return None
    return {
        method: {
            "sample_count": len(records[method]),
            "deadline_missing_rate": statistics.mean(
                _metric(summary, "deadline_missing_rate")
                for summary in records[method]
            ),
            "deadline_missing_rate_range": [
                min(
                    _metric(summary, "deadline_missing_rate")
                    for summary in records[method]
                ),
                max(
                    _metric(summary, "deadline_missing_rate")
                    for summary in records[method]
                ),
            ],
            "qoe_score": statistics.mean(
                _metric(summary, "qoe_score") for summary in records[method]
            ),
            "qoe_score_range": [
                min(_metric(summary, "qoe_score") for summary in records[method]),
                max(_metric(summary, "qoe_score") for summary in records[method]),
            ],
            "end_to_end_latency_seconds": statistics.mean(
                _metric(summary, "end_to_end_latency_seconds")
                for summary in records[method]
            ),
        }
        for method in METHODS
    }


def _quality_gate(metrics):
    deadline_rates = [metrics[method]["deadline_missing_rate"] for method in METHODS]
    qoe_scores = [metrics[method]["qoe_score"] for method in METHODS]
    checks = {
        "all_deadline_missing_rates_are_interior": all(
            0.05 <= value <= 0.95 for value in deadline_rates
        ),
        "deadline_missing_rate_spread_at_least_0_10": (
            max(deadline_rates) - min(deadline_rates) >= 0.10
        ),
        "qoe_not_all_saturated_high": not all(value >= 0.995 for value in qoe_scores),
        "qoe_not_all_saturated_low": not all(value <= 0.005 for value in qoe_scores),
        "qoe_spread_at_least_0_02": max(qoe_scores) - min(qoe_scores) >= 0.02,
    }
    return {"accepted": all(checks.values()), "checks": checks}


def _candidate_score(metrics):
    targets = {
        "baseline": 0.65,
        "llf-dag": 0.50,
        "feedback-fine-grained": 0.35,
    }
    deadline_rates = [metrics[method]["deadline_missing_rate"] for method in METHODS]
    qoe_scores = [metrics[method]["qoe_score"] for method in METHODS]
    score = sum(
        abs(metrics[method]["deadline_missing_rate"] - targets[method])
        for method in METHODS
    )
    score += 2.0 * sum(
        max(0.0, 0.05 - value) + max(0.0, value - 0.95)
        for value in deadline_rates
    )
    if all(value >= 0.995 for value in qoe_scores):
        score += 4.0
    if all(value <= 0.005 for value in qoe_scores):
        score += 4.0
    score += 2.0 * max(0.0, 0.02 - (max(qoe_scores) - min(qoe_scores)))
    score += 2.0 * max(
        0.0, 0.10 - (max(deadline_rates) - min(deadline_rates))
    )
    return score


def _parse_scenario(scenario):
    parts = scenario.split("_")
    if len(parts) != 3 or not parts[0].startswith("d") or not parts[1].startswith("a"):
        raise ValueError(f"invalid calibration scenario: {scenario}")
    return int(parts[0][1:]) / 100, int(parts[1][1:]) / 100


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
        grouped.setdefault(scenario, {}).setdefault(method, []).append(
            json.loads(summary_path.read_text(encoding="utf-8"))
        )

    ranked = []
    for scenario, records in grouped.items():
        metrics = _candidate_metrics(records)
        if metrics is None:
            continue
        deadline_factor, arrival_scale = _parse_scenario(scenario)
        ranked.append(
            {
                "scenario": scenario,
                "deadline_factor": deadline_factor,
                "arrival_scale": arrival_scale,
                "score": _candidate_score(metrics),
                "quality_gate": _quality_gate(metrics),
                "metrics": metrics,
            }
        )
    ranked.sort(
        key=lambda item: (
            not item["quality_gate"]["accepted"],
            item["score"],
            item["scenario"],
        )
    )
    if not ranked:
        raise ValueError(f"no complete paired calibration results in {runs_root}")
    return {"selected": ranked[0], "ranked": ranked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    source = subparsers.add_parser("build-source")
    source.add_argument("--template", type=Path, required=True)
    source.add_argument("--profile", type=Path, required=True)
    source.add_argument("--output", type=Path, required=True)

    calibration = subparsers.add_parser("build-calibration")
    calibration.add_argument("--source", type=Path, required=True)
    calibration.add_argument("--output-dir", type=Path, required=True)
    calibration.add_argument(
        "--deadline-factors",
        type=_csv_factors,
        default=DEFAULT_DEADLINE_FACTORS,
    )
    calibration.add_argument(
        "--arrival-scales",
        type=_csv_factors,
        default=DEFAULT_ARRIVAL_SCALES,
    )

    formal = subparsers.add_parser("build-formal")
    formal.add_argument("--source", type=Path, required=True)
    formal.add_argument("--output-dir", type=Path, required=True)
    formal.add_argument("--deadline-factor", type=float, required=True)
    formal.add_argument("--arrival-scale", type=float, required=True)
    formal.add_argument("--dag-repeated-times", type=int, default=10)
    formal.add_argument("--selection-report", type=Path, required=True)

    select = subparsers.add_parser("select")
    select.add_argument("--runs-root", type=Path, required=True)
    select.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "build-source":
        result = build_source(
            args.template.resolve(), args.profile.resolve(), args.output.resolve()
        )
    elif args.command == "build-calibration":
        result = build_calibration(
            args.source.resolve(),
            args.output_dir.resolve(),
            args.deadline_factors,
            args.arrival_scales,
        )
    elif args.command == "build-formal":
        if args.deadline_factor <= 0 or args.arrival_scale <= 0:
            parser.error("timing factors must be positive")
        if args.dag_repeated_times <= 0:
            parser.error("dag-repeated-times must be positive")
        result = build_formal(
            args.source.resolve(),
            args.output_dir.resolve(),
            args.deadline_factor,
            args.arrival_scale,
            args.dag_repeated_times,
            args.selection_report.resolve(),
        )
    else:
        result = select_calibration(args.runs_root.resolve())
        if args.output:
            _write_json(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
