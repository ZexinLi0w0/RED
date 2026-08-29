#!/usr/bin/env python3
"""Build, select, freeze, and validate the AGX Orin Table 11 matrix."""

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from experiments.summarize_runs import summarize


SCENARIOS = (
    "urban_navigation",
    "emergency_obstacle_avoidance",
    "night_driving",
)
METHODS = (
    "baseline",
    "llf-dag",
    "fine-grained",
    "feedback",
    "feedback-fine-grained",
)
FORMAL_SEEDS = (101, 202, 303, 404, 505)
DEFAULT_TIMING_PAIRS = (
    (2.0, 2.0),
    (4.0, 2.0),
    (4.0, 4.0),
    (6.0, 4.0),
    (8.0, 4.0),
    (8.0, 8.0),
    (12.0, 8.0),
    (12.0, 12.0),
)
RUN_ARGS_TO_CASE = {
    (1,): "lane_detection",
    (2,): "control_autopilot",
    (3,): "segmentation",
    (4,): "object_detection",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path, value):
    payload = json.dumps(value, indent=2, sort_keys=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != payload:
        raise FileExistsError(f"refusing to replace different file: {path}")
    path.write_text(payload, encoding="utf-8")


def _factor_label(value):
    scaled = float(value) * 100
    if not math.isclose(scaled, round(scaled)):
        raise ValueError("timing factors support at most two decimal places")
    return f"{round(scaled):04d}"


def _parse_pairs(raw_value):
    pairs = []
    try:
        for item in raw_value.split(","):
            deadline_factor, arrival_scale = item.split(":", 1)
            pair = (float(deadline_factor), float(arrival_scale))
            if any(not math.isfinite(value) or value <= 0 for value in pair):
                raise ValueError
            pairs.append(pair)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "timing pairs must use positive deadline:arrival values"
        ) from exc
    if not pairs or len(pairs) != len(set(pairs)):
        raise argparse.ArgumentTypeError("timing pairs must be non-empty and unique")
    return tuple(pairs)


def _parse_ints(raw_value):
    try:
        values = tuple(int(value) for value in raw_value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seeds must be comma-separated integers") from exc
    if not values or len(values) != len(set(values)) or any(value < 0 for value in values):
        raise argparse.ArgumentTypeError("seeds must be unique non-negative integers")
    return values


def _profiled_source(template_path, profile_path, scenario):
    config = json.loads(template_path.read_text(encoding="utf-8"))
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile["torch_runtime"]["resolved"] not in {"cuda", "cuda:0"}:
        raise ValueError("AGX Orin runtime profile must resolve to CUDA")

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
    config.pop("MergeThresholdMs", None)
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
                "kind": "profiled-overall-performance-source",
                "scenario": scenario,
                "template_config": template_path.name,
                "runtime_profile": profile_path.name,
            },
        }
    )
    return config


def build_calibration(template_dir, profile_path, output_dir, timing_pairs):
    entries = []
    source_dir = output_dir / "source"
    calibration_dir = output_dir / "calibration"
    for scenario in SCENARIOS:
        template_path = template_dir / f"agx_loose_{scenario}.json"
        if not template_path.is_file():
            raise FileNotFoundError(template_path)
        source = _profiled_source(template_path, profile_path, scenario)
        source_path = source_dir / f"agx_profiled_{scenario}.json"
        _write_json(source_path, source)

        for deadline_factor, arrival_scale in timing_pairs:
            config = json.loads(json.dumps(source))
            profile_name = (
                f"cal_d{_factor_label(deadline_factor)}_"
                f"a{_factor_label(arrival_scale)}"
            )
            config.update(
                {
                    "DeadlineFactor": deadline_factor,
                    "ArrivalScale": arrival_scale,
                    "Calibration": {
                        "device": "agx_orin",
                        "kind": "overall-performance-load-grid",
                        "scenario": scenario,
                        "profile": profile_name,
                        "deadline_factor": deadline_factor,
                        "arrival_scale": arrival_scale,
                        "selection_stage": "EDF-only coarse calibration",
                    },
                }
            )
            config_path = calibration_dir / f"agx_{profile_name}_{scenario}.json"
            _write_json(config_path, config)
            entries.append(
                {
                    "scenario": scenario,
                    "profile": profile_name,
                    "deadline_factor": deadline_factor,
                    "arrival_scale": arrival_scale,
                    "config_path": str(config_path.relative_to(output_dir)),
                    "config_sha256": _sha256(config_path),
                }
            )

    index = {
        "schema_version": 1,
        "device": "agx",
        "phase": "EDF-only coarse calibration",
        "runtime_profile": profile_path.name,
        "selection_rule": (
            "select each scenario using only EDF; prefer interior Deadline "
            "Missing Rate and non-saturated QoE before the five-method pilot"
        ),
        "timing_pairs": [list(pair) for pair in timing_pairs],
        "configs": entries,
    }
    _write_json(output_dir / "calibration_index.json", index)
    return index


def _numeric_metric(summary, name):
    value = summary.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"summary has no numeric {name}")
    if not math.isfinite(value):
        raise ValueError(f"summary has non-finite {name}")
    return float(value)


def select_edf_calibration(index_path, runs_root):
    index = json.loads(index_path.read_text(encoding="utf-8"))
    entries = {
        (entry["scenario"], entry["profile"]): entry for entry in index["configs"]
    }
    grouped = defaultdict(list)
    commits = set()
    seeds = set()
    for manifest_path in sorted(runs_root.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("method") != "baseline" or manifest.get("status") != "complete":
            continue
        key = (manifest["scenario"], manifest["profile"])
        if key not in entries:
            raise ValueError(f"run is absent from calibration index: {key}")
        if manifest["config_sha256"] != entries[key]["config_sha256"]:
            raise ValueError(f"config hash mismatch for {manifest['run_id']}")
        summary_path = manifest_path.parent / "summary.json"
        grouped[key].append(json.loads(summary_path.read_text(encoding="utf-8")))
        commits.add(manifest["git_commit"])
        seeds.add(manifest["seed"])

    selected = {}
    ranked = {}
    for scenario in SCENARIOS:
        candidates = []
        for (candidate_scenario, profile_name), summaries in grouped.items():
            if candidate_scenario != scenario:
                continue
            entry = entries[(candidate_scenario, profile_name)]
            deadline_rate = statistics.fmean(
                _numeric_metric(summary, "deadline_missing_rate")
                for summary in summaries
            )
            qoe_score = statistics.fmean(
                _numeric_metric(summary, "qoe_score") for summary in summaries
            )
            latency = statistics.fmean(
                _numeric_metric(summary, "end_to_end_latency_seconds")
                for summary in summaries
            )
            quality_gate = {
                "deadline_missing_rate_is_interior": 0.15 <= deadline_rate <= 0.85,
                "qoe_is_not_saturated": 0.05 <= qoe_score <= 0.98,
            }
            score = abs(deadline_rate - 0.50) + 0.5 * abs(qoe_score - 0.60)
            candidates.append(
                {
                    **entry,
                    "sample_count": len(summaries),
                    "mean_deadline_missing_rate": deadline_rate,
                    "mean_qoe_score": qoe_score,
                    "mean_end_to_end_latency_seconds": latency,
                    "quality_gate": {
                        "accepted": all(quality_gate.values()),
                        "checks": quality_gate,
                    },
                    "score": score,
                }
            )
        candidates.sort(
            key=lambda item: (
                not item["quality_gate"]["accepted"],
                item["score"],
                item["profile"],
            )
        )
        if not candidates:
            raise ValueError(f"no complete EDF calibration runs for {scenario}")
        ranked[scenario] = candidates
        selected[scenario] = candidates[0]

    return {
        "schema_version": 1,
        "selection_stage": "EDF-only coarse calibration",
        "git_commits": sorted(commits),
        "seeds": sorted(seeds),
        "selected": selected,
        "ranked": ranked,
    }


def freeze_configs(index_path, selection_path, output_dir, profile_name, validation_path=None):
    index = json.loads(index_path.read_text(encoding="utf-8"))
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    entries = {
        (entry["scenario"], entry["profile"]): entry for entry in index["configs"]
    }
    validation = None
    if validation_path is not None:
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        if not validation["quality_gate"]["accepted"]:
            raise ValueError("pilot matrix did not pass its quality gate")

    frozen_entries = []
    for scenario in SCENARIOS:
        selected = selection["selected"][scenario]
        entry = entries[(scenario, selected["profile"])]
        source_path = index_path.parent / entry["config_path"]
        if _sha256(source_path) != entry["config_sha256"]:
            raise ValueError(f"calibration config hash mismatch: {source_path}")
        config = json.loads(source_path.read_text(encoding="utf-8"))
        config.pop("Calibration", None)
        config["FormalExperiment" if profile_name == "tight" else "PilotExperiment"] = {
            "device": "agx_orin",
            "kind": "overall-performance",
            "scenario": scenario,
            "profile": profile_name,
            "deadline_factor": selected["deadline_factor"],
            "arrival_scale": selected["arrival_scale"],
            "edf_selection_report": selection_path.name,
            "edf_selection_report_sha256": _sha256(selection_path),
            "pilot_validation_report": validation_path.name if validation_path else None,
            "pilot_validation_report_sha256": (
                _sha256(validation_path) if validation_path else None
            ),
            "calibration_frozen_before_formal_runs": profile_name == "tight",
        }
        output_path = output_dir / f"agx_{profile_name}_{scenario}.json"
        _write_json(output_path, config)
        frozen_entries.append(
            {
                "scenario": scenario,
                "profile": profile_name,
                "config_path": output_path.name,
                "config_sha256": _sha256(output_path),
                "deadline_factor": selected["deadline_factor"],
                "arrival_scale": selected["arrival_scale"],
            }
        )

    frozen_index = {
        "schema_version": 1,
        "device": "agx",
        "phase": profile_name,
        "methods": list(METHODS),
        "seeds": list(FORMAL_SEEDS) if profile_name == "tight" else [11, 22, 33],
        "configs": frozen_entries,
    }
    _write_json(output_dir / "frozen_index.json", frozen_index)
    return frozen_index


def validate_matrix(runs_root, expected_profile, expected_seeds):
    report = summarize(runs_root)
    expected_run_count = len(SCENARIOS) * len(METHODS) * len(expected_seeds)
    aggregates = {
        (row["scenario"], row["method"]): row for row in report["aggregates"]
    }
    scenario_checks = {}
    for scenario in SCENARIOS:
        rows = [aggregates.get((scenario, method)) for method in METHODS]
        complete = all(row is not None for row in rows)
        deadline_rates = (
            [row["metrics"]["deadline_missing_rate"]["mean"] for row in rows]
            if complete else []
        )
        qoe_scores = (
            [row["metrics"]["qoe_score"]["mean"] for row in rows]
            if complete else []
        )
        checks = {
            "all_methods_present": complete,
            "at_least_three_interior_deadline_missing_rates": (
                sum(0.02 < value < 0.98 for value in deadline_rates) >= 3
            ),
            "deadline_missing_rate_spread_at_least_0_10": (
                bool(deadline_rates) and max(deadline_rates) - min(deadline_rates) >= 0.10
            ),
            "at_least_three_interior_qoe_scores": (
                sum(0.02 < value < 0.98 for value in qoe_scores) >= 3
            ),
            "qoe_spread_at_least_0_05": (
                bool(qoe_scores) and max(qoe_scores) - min(qoe_scores) >= 0.05
            ),
            "qoe_not_all_saturated_high": not qoe_scores or not all(
                value >= 0.995 for value in qoe_scores
            ),
            "qoe_not_all_saturated_low": not qoe_scores or not all(
                value <= 0.005 for value in qoe_scores
            ),
        }
        scenario_checks[scenario] = {
            "accepted": all(checks.values()),
            "checks": checks,
            "deadline_missing_rate_means": deadline_rates,
            "qoe_score_means": qoe_scores,
        }

    global_checks = {
        "all_expected_runs_complete": (
            report["validation"]["complete_run_count"] == expected_run_count
        ),
        "all_methods_present": set(report["validation"]["methods"]) == set(METHODS),
        "single_git_commit": len(report["validation"]["git_commits"]) == 1,
        "cuda_only": set(report["validation"]["torch_devices"]) <= {"cuda", "cuda:0"},
        "expected_profile_only": all(
            row["profile"] == expected_profile for row in report["aggregates"]
        ),
        "expected_seeds_only": all(
            set(row["seeds"]) == set(expected_seeds) for row in report["aggregates"]
        ),
        "all_scenarios_discriminative": all(
            value["accepted"] for value in scenario_checks.values()
        ),
    }
    report["quality_gate"] = {
        "accepted": all(global_checks.values()),
        "checks": global_checks,
        "scenario_checks": scenario_checks,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build-calibration")
    build.add_argument("--template-dir", type=Path, required=True)
    build.add_argument("--runtime-profile", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument(
        "--timing-pairs",
        type=_parse_pairs,
        default=DEFAULT_TIMING_PAIRS,
    )

    select = subparsers.add_parser("select-edf")
    select.add_argument("--index", type=Path, required=True)
    select.add_argument("--runs-root", type=Path, required=True)
    select.add_argument("--output", type=Path, required=True)

    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--index", type=Path, required=True)
    freeze.add_argument("--selection", type=Path, required=True)
    freeze.add_argument("--output-dir", type=Path, required=True)
    freeze.add_argument("--profile-name", choices=("pilot", "tight"), required=True)
    freeze.add_argument("--validation", type=Path)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--runs-root", type=Path, required=True)
    validate.add_argument("--expected-profile", required=True)
    validate.add_argument("--expected-seeds", type=_parse_ints, required=True)
    validate.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "build-calibration":
        value = build_calibration(
            args.template_dir.resolve(),
            args.runtime_profile.resolve(),
            args.output_dir.resolve(),
            args.timing_pairs,
        )
    elif args.command == "select-edf":
        value = select_edf_calibration(args.index.resolve(), args.runs_root.resolve())
        _write_json(args.output.resolve(), value)
    elif args.command == "freeze":
        value = freeze_configs(
            args.index.resolve(),
            args.selection.resolve(),
            args.output_dir.resolve(),
            args.profile_name,
            args.validation.resolve() if args.validation else None,
        )
    else:
        value = validate_matrix(
            args.runs_root.resolve(), args.expected_profile, args.expected_seeds
        )
        _write_json(args.output.resolve(), value)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
