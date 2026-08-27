#!/usr/bin/env python3
"""Plot representative audited M3 Max QoE results from raw run artifacts."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from experiments.result_presentation import (
    format_truncated,
    select_representative,
    truncate_value,
)


METHODS = (
    ("baseline", "EDF", "#000000"),
    ("llf-dag", "LLF-DAG", "#3F3F3F"),
    ("fine-grained", "MERIS-FG", "#777777"),
    ("feedback", "MERIS-IDA", "#B5B5B5"),
    ("feedback-fine-grained", "MERIS", "#FFFFFF"),
)
SCENARIOS = (
    ("urban_navigation", "Urban"),
    ("emergency_obstacle_avoidance", "Emergency"),
    ("night_driving", "Night"),
)
PROFILES = (("tight", "Tight Deadline"), ("loose", "Loose Deadline"))
METRICS = (
    "end_to_end_latency_seconds",
    "deadline_missing_rate",
    "qoe_score",
)


def load_representative_runs(runs_root):
    """Return one complete, latency-median run for every declared experiment group."""
    grouped = defaultdict(list)
    runs_root = Path(runs_root)
    for manifest_path in sorted(runs_root.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "complete":
            continue
        group_key = (
            manifest["profile"],
            manifest["scenario"],
            manifest["method"],
        )
        summary_path = manifest_path.with_name("summary.json")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("run_id") != manifest.get("run_id"):
            raise ValueError(f"run id mismatch in {manifest_path.parent}")
        record = {
            "seed": int(manifest["seed"]),
            "run_id": manifest["run_id"],
        }
        for metric in METRICS:
            record[metric] = float(summary[metric])
        grouped[group_key].append(record)

    selected = {}
    for profile, _ in PROFILES:
        selected[profile] = {}
        for method, _, _ in METHODS:
            selected[profile][method] = {}
            for scenario, _ in SCENARIOS:
                group_key = (profile, scenario, method)
                records = grouped.get(group_key, [])
                if len(records) != 5:
                    raise ValueError(
                        f"expected five complete repetitions for {group_key}; "
                        f"found {len(records)}"
                    )
                seeds = [record["seed"] for record in records]
                if len(set(seeds)) != len(seeds):
                    raise ValueError(f"duplicate seed for {group_key}")
                selected[profile][method][scenario] = select_representative(
                    records, group_key
                )
    return selected


def selection_report(selected, profiles=None):
    """Return an auditable text report of selected seeds and metric triples."""
    if profiles is None:
        profiles = [profile for profile, _ in PROFILES]
    lines = [
        "profile\tscenario\tmethod\tseed\tlatency / Deadline Missing Rate / QoE"
    ]
    for profile in profiles:
        for scenario, scenario_label in SCENARIOS:
            for method, method_label, _ in METHODS:
                record = selected[profile][method][scenario]
                triple = " / ".join(
                    format_truncated(record[metric]) for metric in METRICS
                )
                lines.append(
                    f"{profile}\t{scenario_label}\t{method_label}\t"
                    f"{record['seed']}\t{triple}"
                )
    return "\n".join(lines)


def plot_qoe(runs_root, output_path, profiles=("tight",)):
    """Plot QoE for the requested profiles; the paper defaults to Tight only."""
    selected = load_representative_runs(runs_root)
    profile_titles = dict(PROFILES)
    profiles = tuple(profiles)
    unknown_profiles = set(profiles) - set(profile_titles)
    if not profiles or unknown_profiles:
        raise ValueError(f"invalid QoE profiles: {sorted(unknown_profiles)}")
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".pdf":
        raise ValueError("QoE figure output must be a PDF")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 8,
            "axes.labelsize": 9,
            "axes.titlesize": 9,
            "legend.fontsize": 7.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    figure_width = 4.15 if len(profiles) == 1 else 7.1
    figure, axes = plt.subplots(
        1,
        len(profiles),
        figsize=(figure_width, 2.65),
        sharey=True,
        squeeze=False,
    )
    axes = axes.ravel()
    x = np.arange(len(SCENARIOS), dtype=float)
    width = 0.155
    offsets = (np.arange(len(METHODS)) - (len(METHODS) - 1) / 2) * width

    for profile_index, (axis, profile) in enumerate(zip(axes, profiles)):
        for offset, (method, label, shade) in zip(offsets, METHODS):
            values = [
                truncate_value(selected[profile][method][scenario]["qoe_score"])
                for scenario, _ in SCENARIOS
            ]
            bars = axis.bar(
                x + offset,
                values,
                width=width,
                label=label,
                color=shade,
                edgecolor="black",
                linewidth=0.65,
                zorder=3,
            )
            if method == "feedback-fine-grained":
                for bar, value in zip(bars, values):
                    axis.text(
                        bar.get_x() + bar.get_width() / 2,
                        value + 0.018,
                        f"{value:.3f}",
                        ha="center",
                        va="bottom",
                        fontsize=6.6,
                        fontweight="bold",
                        color="black",
                    )

        title = profile_titles[profile]
        if len(profiles) > 1:
            title = f"({chr(ord('a') + profile_index)}) {title}"
        axis.set_title(title, pad=4)
        axis.set_xticks(x, [label for _, label in SCENARIOS])
        axis.set_ylim(0.0, 1.02)
        axis.set_yticks(np.arange(0.0, 1.01, 0.2))
        axis.grid(axis="y", linestyle=":", linewidth=0.45, color="#B0B0B0", zorder=0)
        axis.set_xlabel("Scenario")
    axes[0].set_ylabel("Quality of Experience Score")

    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="upper center",
        ncol=5,
        frameon=True,
        facecolor="white",
        edgecolor="black",
        bbox_to_anchor=(0.5, 0.995),
        columnspacing=1.1,
        handlelength=1.8,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.84), pad=0.5, w_pad=0.8)
    figure.savefig(
        output_path,
        format="pdf",
        bbox_inches="tight",
        metadata={
            "Title": "Representative M3 Max core Quality of Experience results",
            "Subject": (
                "Latency-median runs; plotted values are truncated to three decimals"
            ),
        },
    )
    plt.close(figure)
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=[profile for profile, _ in PROFILES],
        default=["tight"],
        help="deadline profiles to plot (default: tight)",
    )
    args = parser.parse_args()
    selected = plot_qoe(args.runs_root, args.output, profiles=args.profiles)
    report = selection_report(selected, profiles=args.profiles)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
