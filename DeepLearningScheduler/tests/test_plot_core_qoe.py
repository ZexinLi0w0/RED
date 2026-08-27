import json

import pytest

from experiments.plot_core_qoe import (
    METHODS,
    PROFILES,
    SCENARIOS,
    format_truncated,
    load_representative_runs,
    select_representative,
)


def _write_run(root, profile, scenario, method, seed, latency):
    run_id = f"mac-{scenario}-{profile}-{method}-seed{seed}"
    run_dir = root / run_id
    run_dir.mkdir()
    manifest = {
        "method": method,
        "profile": profile,
        "run_id": run_id,
        "scenario": scenario,
        "seed": seed,
        "status": "complete",
    }
    summary = {
        "deadline_missing_rate": seed / 1000,
        "end_to_end_latency_seconds": latency,
        "qoe_score": seed / 1000,
        "run_id": run_id,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")


def _write_matrix(root):
    latencies = {101: 5.0, 202: 1.0, 303: 3.0, 404: 4.0, 505: 2.0}
    for profile, _ in PROFILES:
        for scenario, _ in SCENARIOS:
            for method, _, _ in METHODS:
                for seed, latency in latencies.items():
                    _write_run(root, profile, scenario, method, seed, latency)


def test_load_representative_runs_preserves_one_complete_median_tuple(tmp_path):
    _write_matrix(tmp_path)

    selected = load_representative_runs(tmp_path)

    record = selected["tight"]["baseline"]["urban_navigation"]
    assert record["seed"] == 303
    assert record["end_to_end_latency_seconds"] == 3.0
    assert record["deadline_missing_rate"] == pytest.approx(0.303)
    assert record["qoe_score"] == pytest.approx(0.303)


def test_load_representative_runs_rejects_an_incomplete_matrix(tmp_path):
    _write_matrix(tmp_path)
    first_run = next(tmp_path.iterdir())
    (first_run / "manifest.json").unlink()

    with pytest.raises(ValueError, match="expected five complete repetitions"):
        load_representative_runs(tmp_path)


def test_even_selection_uses_one_of_the_two_central_runs():
    records = [
        {"seed": seed, "end_to_end_latency_seconds": latency}
        for seed, latency in ((1, 1.0), (2, 2.0), (3, 3.0), (4, 4.0))
    ]

    selected = select_representative(records, ("tight", "urban", "baseline"))

    assert selected["seed"] in {2, 3}


def test_format_truncated_never_rounds_up():
    assert format_truncated(0.8867) == "0.886"
    assert format_truncated(0.0009) == "0.000"
    assert format_truncated(1.0) == "1.000"
