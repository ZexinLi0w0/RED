import hashlib
import json

import pytest

from experiments.freeze_calibrated_configs import freeze_configs


def _write_json(path, value):
    payload = (json.dumps(value, indent=2) + "\n").encode()
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def test_freeze_requires_ready_report_and_preserves_selected_evidence(tmp_path) -> None:
    calibration_dir = tmp_path / "calibration"
    output_dir = tmp_path / "frozen"
    calibration_dir.mkdir()
    tight_path = calibration_dir / "agx_cal_a100_example.json"
    loose_path = calibration_dir / "agx_cal_a160_example.json"
    tight_hash = _write_json(tight_path, {"DeadlineFactor": 1.0})
    loose_hash = _write_json(loose_path, {"DeadlineFactor": 1.6})
    report_path = tmp_path / "report.json"
    report = {
        "ready_to_freeze": True,
        "selection_source": "EDF-only completed runs",
        "code_commits": ["abc"],
        "selections": [
            {
                "device": "agx",
                "scenario": "example",
                "tight": {
                    "profile": "cal_a100",
                    "deadline_alpha": 1.0,
                    "config_path": tight_path.name,
                    "config_sha256": tight_hash,
                    "mean_deadline_missing_rate": 0.5,
                    "repetitions": 3,
                    "seeds": [1, 2, 3],
                },
                "loose": {
                    "profile": "cal_a160",
                    "deadline_alpha": 1.6,
                    "config_path": loose_path.name,
                    "config_sha256": loose_hash,
                    "mean_deadline_missing_rate": 0.1,
                    "repetitions": 3,
                    "seeds": [1, 2, 3],
                },
            }
        ],
    }
    _write_json(report_path, report)

    index = freeze_configs(report_path, calibration_dir, output_dir)

    assert len(index["configs"]) == 2
    frozen_tight = json.loads(
        (output_dir / "agx_tight_example.json").read_text()
    )
    assert frozen_tight["DeadlineFactor"] == 1.0
    assert frozen_tight["CalibrationSelection"]["selected_as"] == "tight"

    report["ready_to_freeze"] = False
    _write_json(report_path, report)
    with pytest.raises(ValueError, match="ready_to_freeze"):
        freeze_configs(report_path, calibration_dir, output_dir)
