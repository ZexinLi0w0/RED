import hashlib
import json
import csv

import pytest

from experiments.summarize_runs import _write_csv, summarize


def _write_run(
    root,
    method,
    seed,
    latency,
    dmr,
    qoe,
    stream_hash="paired",
    atomic_ratio=None,
):
    run_id = f"mac-demo-tight-{method}-seed{seed}"
    run_dir = root / run_id
    run_dir.mkdir()
    summary = {
        "run_id": run_id,
        "end_to_end_latency_seconds": latency,
        "deadline_missing_rate": dmr,
        "qoe_score": qoe,
        "outcome_counts": {"success": 2},
    }
    if atomic_ratio is not None:
        atomic_count = int(2 * atomic_ratio)
        partitionable_count = 2 - atomic_count

        def subgroup(count):
            if count == 0:
                return {
                    "offered_node_count": 0,
                    "outcome_counts": {},
                    "deadline_missing_rate": None,
                    "qoe_score": None,
                }
            return {
                "offered_node_count": count,
                "outcome_counts": {"success": count},
                "deadline_missing_rate": 0.0,
                "qoe_score": qoe,
            }

        summary["offered_task_count"] = 2
        summary["atomic_node_statistics"] = {
            "semantics": "test atomic semantics",
            "atomic_offered_ratio": atomic_ratio,
            "atomic": subgroup(atomic_count),
            "partitionable": subgroup(partitionable_count),
        }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    summary_hash = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    manifest = {
        "run_id": run_id,
        "status": "complete",
        "device": "mac",
        "profile": "tight",
        "scenario": "demo",
        "method": method,
        "seed": seed,
        "config_sha256": "config",
        "offered_task_count": 2,
        "offered_task_stream_sha256": stream_hash,
        "git_commit": "commit",
        "power_mode": "ac",
        "torch_runtime": {"resolved": "mps"},
        "summary_sha256": summary_hash,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def test_summarize_validates_pairs_and_computes_candidate_improvements(tmp_path):
    _write_run(tmp_path, "baseline", 1, 2.0, 0.5, 0.4)
    _write_run(tmp_path, "candidate", 1, 1.0, 0.2, 0.8)
    _write_run(tmp_path, "baseline", 2, 4.0, 0.7, 0.2)
    _write_run(tmp_path, "candidate", 2, 2.0, 0.3, 0.6)

    report = summarize(tmp_path)

    assert report["validation"]["complete_run_count"] == 4
    candidate = next(
        row for row in report["aggregates"] if row["method"] == "candidate"
    )
    assert candidate["metrics"]["end_to_end_latency_seconds"]["mean"] == 1.5
    comparison = report["paired_comparisons"][0]
    assert comparison["metrics"]["end_to_end_latency_seconds"]["mean"] == 1.5
    assert comparison["metrics"]["deadline_missing_rate"]["mean"] == 0.35
    assert comparison["metrics"]["qoe_score"]["mean"] == pytest.approx(0.4)
    assert comparison["metrics"]["qoe_score"]["wins"] == 2
    presentation = candidate["paper_presentation"]
    assert presentation["seed"] in {1, 2}
    assert presentation["display_metrics"] == {
        key: f"{value:.3f}"
        for key, value in presentation["raw_metrics"].items()
    }

    csv_path = tmp_path / "paper-results.csv"
    _write_csv(csv_path, report)
    with csv_path.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    candidate_row = next(row for row in rows if row["method"] == "candidate")
    assert candidate_row["representative_seed"] in {"1", "2"}
    assert candidate_row["end_to_end_latency_seconds"] in {"1.000", "2.000"}
    assert not any("mean" in column or "sample_sd" in column for column in rows[0])


def test_summarize_rejects_unpaired_streams(tmp_path):
    _write_run(tmp_path, "baseline", 1, 2.0, 0.5, 0.4)
    _write_run(
        tmp_path,
        "candidate",
        1,
        1.0,
        0.2,
        0.8,
        stream_hash="different",
    )

    with pytest.raises(ValueError, match="inconsistent offered_task_stream_sha256"):
        summarize(tmp_path)


def test_summarize_aggregates_defined_atomic_subgroups(tmp_path):
    for seed in (1, 2):
        _write_run(
            tmp_path,
            "baseline",
            seed,
            2.0,
            0.5,
            0.4,
            atomic_ratio=0.5,
        )
        _write_run(
            tmp_path,
            "candidate",
            seed,
            1.0,
            0.2,
            0.8,
            atomic_ratio=0.5,
        )

    report = summarize(tmp_path)

    assert len(report["atomic_subgroup_aggregates"]) == 2
    candidate = next(
        row
        for row in report["atomic_subgroup_aggregates"]
        if row["method"] == "candidate"
    )
    assert candidate["atomic_offered_ratio"] == 0.5
    assert candidate["subgroups"]["atomic"]["n_defined"] == 2
    assert candidate["subgroups"]["atomic"]["metrics"]["qoe_score"][
        "mean"
    ] == 0.8
