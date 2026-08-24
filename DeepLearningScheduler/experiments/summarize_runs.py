#!/usr/bin/env python3
"""Validate paired experiment artifacts and summarize repeated runs."""

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


METRICS = {
    "end_to_end_latency_seconds": "lower",
    "deadline_missing_rate": "lower",
    "qoe_score": "higher",
}

# Two-sided 95% Student-t critical values for the small repeated-run samples
# used by the revision. Values above 30 degrees of freedom use the normal
# approximation, which is conservative enough for descriptive reporting here.
T_CRITICAL_975 = {
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


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sample_summary(values):
    if not values:
        raise ValueError("cannot summarize an empty sample")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("samples must be finite")
    mean = statistics.mean(values)
    sample_sd = statistics.stdev(values) if len(values) > 1 else 0.0
    if len(values) > 1:
        critical = T_CRITICAL_975.get(len(values) - 1, 1.960)
        half_width = critical * sample_sd / math.sqrt(len(values))
    else:
        half_width = 0.0
    return {
        "mean": mean,
        "sample_sd": sample_sd,
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
        "minimum": min(values),
        "maximum": max(values),
    }


def _load_runs(input_root):
    runs = []
    problems = []
    for manifest_path in sorted(input_root.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "complete":
            problems.append(
                f"{manifest_path.parent.name}: status={manifest.get('status')}"
            )
            continue
        summary_path = manifest_path.parent / "summary.json"
        if not summary_path.is_file():
            problems.append(f"{manifest_path.parent.name}: missing summary.json")
            continue
        if _sha256(summary_path) != manifest.get("summary_sha256"):
            problems.append(f"{manifest_path.parent.name}: summary hash mismatch")
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("run_id") != manifest.get("run_id"):
            problems.append(f"{manifest_path.parent.name}: run_id mismatch")
            continue
        for metric in METRICS:
            value = summary.get(metric)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                problems.append(
                    f"{manifest_path.parent.name}: invalid metric {metric}"
                )
        runs.append({"manifest": manifest, "summary": summary})
    if not runs:
        problems.append("no complete runs found")
    if problems:
        raise ValueError("artifact validation failed:\n" + "\n".join(problems))
    return runs


def summarize(input_root, reference_method="baseline"):
    input_root = Path(input_root).resolve()
    runs = _load_runs(input_root)
    methods = sorted({run["manifest"]["method"] for run in runs})
    if reference_method not in methods:
        raise ValueError(f"reference method is absent: {reference_method}")

    paired_groups = defaultdict(list)
    aggregate_groups = defaultdict(list)
    problems = []
    execution_errors = 0
    for run in runs:
        manifest = run["manifest"]
        summary = run["summary"]
        paired_key = (
            manifest["device"],
            manifest["profile"],
            manifest["scenario"],
            manifest["seed"],
        )
        aggregate_key = paired_key[:3] + (manifest["method"],)
        paired_groups[paired_key].append(run)
        aggregate_groups[aggregate_key].append(run)
        execution_errors += summary.get("outcome_counts", {}).get(
            "execution_error", 0
        )

    method_set = set(methods)
    for key, group in sorted(paired_groups.items()):
        group_methods = {run["manifest"]["method"] for run in group}
        if group_methods != method_set:
            problems.append(f"{key}: methods={sorted(group_methods)}")
        for field in (
            "config_sha256",
            "offered_task_count",
            "offered_task_stream_sha256",
            "git_commit",
            "power_mode",
        ):
            if len({run["manifest"][field] for run in group}) != 1:
                problems.append(f"{key}: inconsistent {field}")
        if len(
            {
                run["manifest"]["torch_runtime"]["resolved"]
                for run in group
            }
        ) != 1:
            problems.append(f"{key}: inconsistent torch device")
    if execution_errors:
        problems.append(f"execution_error outcomes={execution_errors}")
    if problems:
        raise ValueError("paired-run validation failed:\n" + "\n".join(problems))

    aggregates = []
    values_by_seed = {}
    for key, group in sorted(aggregate_groups.items()):
        ordered = sorted(group, key=lambda run: run["manifest"]["seed"])
        seeds = [run["manifest"]["seed"] for run in ordered]
        if len(seeds) != len(set(seeds)):
            raise ValueError(f"duplicate seed in aggregate group {key}")
        metric_values = {
            metric: [run["summary"][metric] for run in ordered]
            for metric in METRICS
        }
        values_by_seed[key] = {
            seed: {
                metric: values[index]
                for metric, values in metric_values.items()
            }
            for index, seed in enumerate(seeds)
        }
        aggregates.append(
            {
                "device": key[0],
                "profile": key[1],
                "scenario": key[2],
                "method": key[3],
                "n": len(ordered),
                "seeds": seeds,
                "metrics": {
                    metric: _sample_summary(values)
                    for metric, values in metric_values.items()
                },
            }
        )

    comparisons = []
    conditions = sorted({key[:3] for key in aggregate_groups})
    for condition in conditions:
        reference_key = condition + (reference_method,)
        reference = values_by_seed[reference_key]
        for method in methods:
            if method == reference_method:
                continue
            candidate = values_by_seed[condition + (method,)]
            if set(candidate) != set(reference):
                raise ValueError(
                    f"unpaired seeds for {condition}: {reference_method} vs {method}"
                )
            metric_differences = {}
            for metric, direction in METRICS.items():
                if direction == "lower":
                    differences = [
                        reference[seed][metric] - candidate[seed][metric]
                        for seed in sorted(reference)
                    ]
                    definition = f"{reference_method}_minus_{method}"
                else:
                    differences = [
                        candidate[seed][metric] - reference[seed][metric]
                        for seed in sorted(reference)
                    ]
                    definition = f"{method}_minus_{reference_method}"
                metric_differences[metric] = {
                    **_sample_summary(differences),
                    "definition": definition,
                    "positive_means_candidate_improves": True,
                    "per_seed": dict(zip(sorted(reference), differences)),
                    "wins": sum(value > 0 for value in differences),
                    "ties": sum(abs(value) <= 1e-12 for value in differences),
                }
            comparisons.append(
                {
                    "device": condition[0],
                    "profile": condition[1],
                    "scenario": condition[2],
                    "reference_method": reference_method,
                    "candidate_method": method,
                    "n": len(reference),
                    "metrics": metric_differences,
                }
            )

    return {
        "schema_version": 1,
        "input_root": str(input_root),
        "validation": {
            "complete_run_count": len(runs),
            "paired_group_count": len(paired_groups),
            "methods": methods,
            "git_commits": sorted(
                {run["manifest"]["git_commit"] for run in runs}
            ),
            "torch_devices": sorted(
                {
                    run["manifest"]["torch_runtime"]["resolved"]
                    for run in runs
                }
            ),
            "execution_error_count": execution_errors,
            "problems": [],
        },
        "aggregates": aggregates,
        "paired_comparisons": comparisons,
    }


def _write_csv(path, report):
    comparison_lookup = {
        (
            row["device"],
            row["profile"],
            row["scenario"],
            row["candidate_method"],
        ): row
        for row in report["paired_comparisons"]
    }
    fieldnames = ["device", "profile", "scenario", "method", "n", "seeds"]
    for metric in METRICS:
        fieldnames.extend(
            f"{metric}_{suffix}"
            for suffix in ("mean", "sample_sd", "ci95_low", "ci95_high")
        )
        fieldnames.append(f"{metric}_paired_improvement_vs_reference")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for aggregate in report["aggregates"]:
            row = {
                key: aggregate[key]
                for key in ("device", "profile", "scenario", "method", "n")
            }
            row["seeds"] = ";".join(map(str, aggregate["seeds"]))
            comparison = comparison_lookup.get(
                (
                    aggregate["device"],
                    aggregate["profile"],
                    aggregate["scenario"],
                    aggregate["method"],
                )
            )
            for metric in METRICS:
                for suffix in ("mean", "sample_sd", "ci95_low", "ci95_high"):
                    row[f"{metric}_{suffix}"] = aggregate["metrics"][metric][
                        suffix
                    ]
                row[f"{metric}_paired_improvement_vs_reference"] = (
                    comparison["metrics"][metric]["mean"]
                    if comparison
                    else 0.0
                )
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--reference-method", default="baseline")
    args = parser.parse_args()

    report = summarize(args.input_root, reference_method=args.reference_method)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_csv(args.output_csv, report)
    print(
        f"Validated {report['validation']['complete_run_count']} runs; "
        f"wrote {args.output_json} and {args.output_csv}"
    )


if __name__ == "__main__":
    main()
