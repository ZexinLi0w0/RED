#!/usr/bin/env python3
"""Validate and aggregate the formal AGX Orin Burst experiment."""

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


CONDITIONS = (
    "control-000",
    "transient-050",
    "transient-100",
    "sustained-050",
    "sustained-100",
)
METHODS = ("baseline", "llf-dag", "feedback-fine-grained")
DEFAULT_SEEDS = (101, 202, 303, 404, 505)
METRICS = (
    "end_to_end_latency_seconds",
    "deadline_missing_rate",
    "qoe_score",
)


def _load_json(path):
    with open(path, encoding="utf-8") as input_file:
        return json.load(input_file)


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    with open(temporary, "w", encoding="utf-8") as output_file:
        json.dump(value, output_file, indent=2, sort_keys=True)
        output_file.write("\n")
    temporary.replace(path)


def _finite_number(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _aggregate(values):
    quartiles = (
        statistics.quantiles(values, n=4, method="inclusive")
        if len(values) > 1
        else (values[0], values[0], values[0])
    )
    return {
        "median": statistics.median(values),
        "quartile_1": quartiles[0],
        "quartile_3": quartiles[2],
        "minimum": min(values),
        "maximum": max(values),
    }


def validate_formal_results(output_root, expected_seeds=DEFAULT_SEEDS):
    output_root = Path(output_root).resolve()
    expected_seeds = tuple(expected_seeds)
    if len(expected_seeds) % 2 == 0:
        raise ValueError(
            "formal AGX Orin Burst repetitions must be odd so the median "
            "corresponds to one concrete run"
        )
    expected_cells = {
        (condition, method, seed)
        for condition in CONDITIONS
        for method in METHODS
        for seed in expected_seeds
    }
    records = {}
    problems = []
    commits = set()
    stream_hashes = defaultdict(set)

    for manifest_path in sorted((output_root / "runs").glob("*/manifest.json")):
        manifest = _load_json(manifest_path)
        key = (
            manifest.get("condition_slug"),
            manifest.get("method"),
            manifest.get("seed"),
        )
        if key not in expected_cells:
            problems.append(f"unexpected run cell {key}")
            continue
        if key in records:
            problems.append(f"duplicate run cell {key}")
            continue
        summary_path = manifest_path.parent / "summary.json"
        if manifest.get("status") != "complete":
            problems.append(f"run cell {key} has status {manifest.get('status')!r}")
            continue
        if manifest.get("validation_problems"):
            problems.append(
                f"run cell {key} failed validation: "
                + "; ".join(manifest["validation_problems"])
            )
            continue
        if not summary_path.is_file():
            problems.append(f"run cell {key} is missing summary.json")
            continue
        summary = _load_json(summary_path)
        for metric in METRICS:
            if not _finite_number(summary.get(metric)):
                problems.append(f"run cell {key} has invalid {metric}")
        if summary.get("outcome_counts", {}).get("execution_error", 0):
            problems.append(f"run cell {key} contains execution errors")
        if manifest.get("device") != "agx_orin":
            problems.append(f"run cell {key} has wrong device")
        if manifest.get("torch_runtime", {}).get("resolved") != "cuda:0":
            problems.append(f"run cell {key} did not use cuda:0")
        if manifest.get("power_mode") != "MAXN":
            problems.append(f"run cell {key} did not use MAXN")
        commits.add(manifest.get("git_commit"))
        stream_hashes[(key[0], key[2])].add(
            summary.get("offered_task_stream_sha256")
        )
        records[key] = {"manifest": manifest, "summary": summary}

    missing_cells = sorted(expected_cells - set(records))
    if missing_cells:
        problems.append(f"missing {len(missing_cells)} expected run cells")
    if len(commits) != 1:
        problems.append(f"formal runs use {len(commits)} git commits")
    mismatched_streams = sorted(
        key for key, values in stream_hashes.items() if len(values) != 1
    )
    if mismatched_streams:
        problems.append(
            f"offered task stream differs between methods for {mismatched_streams}"
        )

    rows = []
    if not missing_cells:
        for condition in CONDITIONS:
            for method in METHODS:
                cell_records = [
                    records[(condition, method, seed)]
                    for seed in expected_seeds
                ]
                representative = sorted(
                    cell_records,
                    key=lambda record: (
                        float(record["summary"]["end_to_end_latency_seconds"]),
                        int(record["manifest"]["seed"]),
                    ),
                )[len(cell_records) // 2]
                row = {
                    "condition": condition,
                    "regime": "control" if condition == "control-000" else condition.split("-")[0],
                    "ratio_percent": int(condition.split("-")[1]),
                    "method": method,
                    "sample_count": len(cell_records),
                    "representative_run": {
                        "run_id": representative["manifest"].get("run_id"),
                        "seed": representative["manifest"]["seed"],
                        "selection_metric": "end_to_end_latency_seconds",
                        "metrics": {
                            metric: float(representative["summary"][metric])
                            for metric in METRICS
                        },
                    },
                }
                for metric in METRICS:
                    row[metric] = _aggregate(
                        [
                            float(record["summary"][metric])
                            for record in cell_records
                        ]
                    )
                rows.append(row)

    representative_deadline_missing_rates = [
        row["representative_run"]["metrics"]["deadline_missing_rate"]
        for row in rows
    ]
    representative_qoe_scores = [
        row["representative_run"]["metrics"]["qoe_score"] for row in rows
    ]
    metric_checks = {
        "deadline_missing_rate_has_interior_representative": bool(
            representative_deadline_missing_rates
        )
        and any(
            0.0 < value < 1.0
            for value in representative_deadline_missing_rates
        ),
        "deadline_missing_rate_spread_at_least_0_10": bool(
            representative_deadline_missing_rates
        )
        and max(representative_deadline_missing_rates)
        - min(representative_deadline_missing_rates)
        >= 0.10,
        "qoe_representatives_not_all_saturated_high": bool(
            representative_qoe_scores
        )
        and not all(value >= 0.995 for value in representative_qoe_scores),
        "qoe_representatives_not_all_saturated_low": bool(
            representative_qoe_scores
        )
        and not all(value <= 0.005 for value in representative_qoe_scores),
        "qoe_representative_spread_at_least_0_10": bool(
            representative_qoe_scores
        )
        and max(representative_qoe_scores) - min(representative_qoe_scores)
        >= 0.10,
    }
    failed_metric_checks = [
        name for name, passed in metric_checks.items() if not passed
    ]
    if failed_metric_checks:
        problems.append(
            "metric quality gate failed: " + ", ".join(failed_metric_checks)
        )

    report = {
        "schema_version": 2,
        "study": "agx-orin-transient-sustained-burst",
        "output_root": str(output_root),
        "expected_run_count": len(expected_cells),
        "complete_run_count": len(records),
        "expected_seeds": list(expected_seeds),
        "git_commits": sorted(str(commit) for commit in commits),
        "aggregate_rows": rows,
        "quality_gate": {
            "accepted": not problems,
            "checks": {
                "all_expected_runs_complete": not missing_cells
                and len(records) == len(expected_cells),
                "single_git_commit": len(commits) == 1,
                "paired_streams_match": not mismatched_streams,
                **metric_checks,
            },
            "problems": problems,
        },
    }
    report_root = output_root / "report"
    _write_json(report_root / "agx_orin_aggregate_summary.json", report)
    report_root.mkdir(parents=True, exist_ok=True)
    with open(
        report_root / "agx_orin_aggregate_summary.csv",
        "w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        fieldnames = [
            "condition",
            "regime",
            "ratio_percent",
            "method",
            "sample_count",
            "representative_run_id",
            "representative_seed",
            *[
                f"{metric}_{statistic}"
                for metric in METRICS
                for statistic in (
                    "median",
                    "quartile_1",
                    "quartile_3",
                    "minimum",
                    "maximum",
                )
            ],
            *[f"representative_{metric}" for metric in METRICS],
        ]
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flattened = {
                key: row[key]
                for key in (
                    "condition",
                    "regime",
                    "ratio_percent",
                    "method",
                    "sample_count",
                )
            }
            flattened["representative_run_id"] = row[
                "representative_run"
            ]["run_id"]
            flattened["representative_seed"] = row[
                "representative_run"
            ]["seed"]
            for metric in METRICS:
                for statistic, value in row[metric].items():
                    flattened[f"{metric}_{statistic}"] = value
                flattened[f"representative_{metric}"] = row[
                    "representative_run"
                ]["metrics"][metric]
            writer.writerow(flattened)
    return report


def _csv_ints(value):
    try:
        parsed = tuple(int(item) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seeds must be comma-separated integers") from exc
    if not parsed or len(set(parsed)) != len(parsed):
        raise argparse.ArgumentTypeError("seeds must be non-empty and unique")
    return parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--seeds", type=_csv_ints, default=DEFAULT_SEEDS)
    args = parser.parse_args()
    report = validate_formal_results(args.output_root, args.seeds)
    print(json.dumps(report["quality_gate"], indent=2, sort_keys=True))
    return 0 if report["quality_gate"]["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
