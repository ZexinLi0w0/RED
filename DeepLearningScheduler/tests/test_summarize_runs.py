import hashlib
import json

import pytest

from experiments.summarize_runs import summarize


def _write_run(root, method, seed, latency, dmr, qoe, stream_hash="paired"):
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
