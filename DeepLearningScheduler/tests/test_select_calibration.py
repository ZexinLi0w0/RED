import json

import pytest

from experiments.select_calibration import (
    _load_completed_edf_runs,
    select_tight_loose,
)


def _point(alpha, miss_rate):
    return {
        "deadline_alpha": alpha,
        "mean_deadline_missing_rate": miss_rate,
    }


def test_selection_uses_ordered_points_inside_predeclared_intervals() -> None:
    result = select_tight_loose(
        [
            _point(0.8, 0.90),
            _point(1.0, 0.55),
            _point(1.2, 0.32),
            _point(1.4, 0.20),
            _point(1.6, 0.11),
            _point(2.0, 0.01),
        ]
    )
    assert result["status"] == "ready"
    assert result["tight"]["deadline_alpha"] == 1.0
    assert result["loose"]["deadline_alpha"] == 1.6


def test_selection_requests_extension_when_targets_are_saturated() -> None:
    result = select_tight_loose(
        [_point(0.8, 1.0), _point(1.0, 0.95), _point(1.2, 0.90)]
    )
    assert result["status"] == "needs-grid-extension"


def test_calibration_rejects_mixed_execution_devices(tmp_path) -> None:
    key = ("mac", "example", "cal_a100")
    entries = {key: {"config_sha256": "config-hash"}}
    for seed, device in ((101, "mps"), (202, "cpu")):
        run_dir = tmp_path / f"run-{seed}"
        run_dir.mkdir()
        (run_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "run_id": f"run-{seed}",
                    "status": "complete",
                    "method": "baseline",
                    "device": "mac",
                    "scenario": "example",
                    "profile": "cal_a100",
                    "seed": seed,
                    "power_mode": "test",
                    "config_sha256": "config-hash",
                    "offered_task_stream_sha256": "task-hash",
                    "git_commit": "same-commit",
                    "torch_runtime": {"resolved": device},
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "summary.json").write_text(
            json.dumps(
                {
                    "offered_task_stream_sha256": "task-hash",
                    "deadline_missing_rate": 0.5,
                }
            ),
            encoding="utf-8",
        )

    with pytest.raises(ValueError, match="multiple PyTorch devices"):
        _load_completed_edf_runs(tmp_path, entries)
