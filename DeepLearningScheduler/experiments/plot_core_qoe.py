#!/usr/bin/env python3
"""Plot the audited M3 Max core QoE results from a summary artifact."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


METHODS = (
    ("baseline", "EDF", "#4C78A8", ""),
    ("llf-dag", "LLF-DAG", "#F58518", "//"),
    ("fine-grained", "MERIS-FG", "#54A24B", "xx"),
    ("feedback", "MERIS-IDA", "#B279A2", ".."),
    ("feedback-fine-grained", "MERIS", "#E45756", "\\\\"),
)
SCENARIOS = (
    ("urban_navigation", "Urban"),
    ("emergency_obstacle_avoidance", "Emergency"),
    ("night_driving", "Night"),
)
PROFILES = (("tight", "(a) Tight"), ("loose", "(b) Loose"))


def load_qoe_data(summary_path):
    """Return mean and sample-SD QoE values in the declared plot order."""
    report = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    aggregates = {}
    for row in report.get("aggregates", []):
        key = (row["profile"], row["scenario"], row["method"])
        if key in aggregates:
            raise ValueError(f"duplicate aggregate row: {key}")
        aggregates[key] = row

    values = {}
    for profile, _ in PROFILES:
        values[profile] = {}
        for method, _, _, _ in METHODS:
            means = []
            sample_sds = []
            for scenario, _ in SCENARIOS:
                key = (profile, scenario, method)
                if key not in aggregates:
                    raise ValueError(f"missing aggregate row: {key}")
                row = aggregates[key]
                if row.get("n") != 5:
                    raise ValueError(f"expected five repetitions for {key}")
                metric = row["metrics"]["qoe_score"]
                means.append(float(metric["mean"]))
                sample_sds.append(float(metric["sample_sd"]))
            values[profile][method] = {
                "means": means,
                "sample_sds": sample_sds,
            }
    return values


def plot_qoe(summary_path, output_path):
    values = load_qoe_data(summary_path)
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

    figure, axes = plt.subplots(1, 2, figsize=(7.1, 2.9), sharey=True)
    x = np.arange(len(SCENARIOS), dtype=float)
    width = 0.155
    offsets = (np.arange(len(METHODS)) - (len(METHODS) - 1) / 2) * width

    for axis, (profile, title) in zip(axes, PROFILES):
        for offset, (method, label, color, hatch) in zip(offsets, METHODS):
            means = values[profile][method]["means"]
            sample_sds = values[profile][method]["sample_sds"]
            bars = axis.bar(
                x + offset,
                means,
                width=width,
                yerr=sample_sds,
                capsize=1.8,
                error_kw={"elinewidth": 0.7, "capthick": 0.7},
                label=label,
                color=color,
                edgecolor="black",
                linewidth=0.55,
                hatch=hatch,
                zorder=3,
            )
            if method == "feedback-fine-grained":
                for bar, mean, sample_sd in zip(bars, means, sample_sds):
                    axis.text(
                        bar.get_x() + bar.get_width() / 2,
                        mean + sample_sd + 0.025,
                        f"{mean:.3f}",
                        ha="center",
                        va="bottom",
                        fontsize=6.6,
                        fontweight="bold",
                        color="#9C2F2F",
                    )

        axis.set_title(title, pad=4, fontweight="bold")
        axis.set_xticks(x, [label for _, label in SCENARIOS])
        axis.set_ylim(0.0, 1.02)
        axis.set_yticks(np.arange(0.0, 1.01, 0.2))
        axis.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.55, zorder=0)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.set_xlabel("Scenario")
    axes[0].set_ylabel("Corrected QoE score")

    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="upper center",
        ncol=5,
        frameon=False,
        bbox_to_anchor=(0.5, 0.995),
        columnspacing=1.1,
        handlelength=1.8,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.86), pad=0.5, w_pad=0.8)
    figure.savefig(
        output_path,
        format="pdf",
        bbox_inches="tight",
        metadata={
            "Title": "Audited M3 Max core QoE results",
            "Subject": "Mean and sample standard deviation over five paired runs",
        },
    )
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot_qoe(args.summary, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
