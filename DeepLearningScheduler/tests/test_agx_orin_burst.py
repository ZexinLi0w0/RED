import json

from experiments.agx_orin_burst import CONDITIONS, METHODS, validate_formal_results


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_quality_gate_accepts_complete_distinctive_matrix(tmp_path) -> None:
    seeds = (101, 202, 303)
    for condition_index, condition in enumerate(CONDITIONS):
        for method_index, method in enumerate(METHODS):
            for seed in seeds:
                run_root = tmp_path / "runs" / f"{condition}-{method}-{seed}"
                stream_hash = f"stream-{condition}-{seed}"
                deadline_missing_rate = min(
                    0.95,
                    0.05 + condition_index * 0.15 + method_index * 0.05,
                )
                qoe_score = max(
                    0.05,
                    0.95 - condition_index * 0.12 - method_index * 0.04,
                )
                _write_json(
                    run_root / "manifest.json",
                    {
                        "condition_slug": condition,
                        "method": method,
                        "seed": seed,
                        "status": "complete",
                        "validation_problems": [],
                        "device": "agx_orin",
                        "torch_runtime": {"resolved": "cuda:0"},
                        "power_mode": "MAXN",
                        "git_commit": "abc123",
                    },
                )
                _write_json(
                    run_root / "summary.json",
                    {
                        "offered_task_stream_sha256": stream_hash,
                        "end_to_end_latency_seconds": 1.0 + condition_index,
                        "deadline_missing_rate": deadline_missing_rate,
                        "qoe_score": qoe_score,
                        "outcome_counts": {"success": 1},
                    },
                )

    report = validate_formal_results(tmp_path, seeds)

    assert report["quality_gate"]["accepted"] is True
    assert report["complete_run_count"] == 45
    assert len(report["aggregate_rows"]) == 15
    assert all(
        row["representative_run"]["seed"] == 202
        for row in report["aggregate_rows"]
    )
    assert "mean" not in json.dumps(report)


def test_quality_gate_rejects_saturated_metrics(tmp_path) -> None:
    report = validate_formal_results(tmp_path, (101,))

    assert report["quality_gate"]["accepted"] is False
    assert report["quality_gate"]["checks"][
        "deadline_missing_rate_has_interior_representative"
    ] is False


def test_quality_gate_requires_an_odd_repetition_count(tmp_path) -> None:
    try:
        validate_formal_results(tmp_path, (101, 202))
    except ValueError as exc:
        assert "must be odd" in str(exc)
    else:
        raise AssertionError("an even repetition count was accepted")
