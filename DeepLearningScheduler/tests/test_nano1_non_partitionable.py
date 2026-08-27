import json

import pytest

from experiments.nano1_non_partitionable import (
    build_calibration,
    build_formal,
    select_calibration,
)


def _source(path):
    value = {
        "DeadlineFactor": 1.0,
        "ArrivalScale": 1.0,
        "DagRepeatedTimes": 10,
        "TaskSeed": 0,
        "QoELambda": 0.05,
        "dag_list": [[{"TaskName": "x"}]],
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_calibration_grid_changes_timing_and_shortens_run(tmp_path):
    index = build_calibration(_source(tmp_path / "source.json"), tmp_path / "cal")
    assert len(index["configs"]) == 12
    config = json.loads(
        (tmp_path / "cal" / "nano1_cal_d010_a025_p050.json").read_text()
    )
    assert config["DeadlineFactor"] == 0.1
    assert config["ArrivalScale"] == 0.25
    assert config["DagRepeatedTimes"] == 3
    assert config["NonPartitionablePercentage"] == 50


def test_formal_configs_differ_only_by_percentage(tmp_path):
    output_dir = tmp_path / "formal"
    build_formal(_source(tmp_path / "source.json"), output_dir, 0.5, 0.25, 10)
    configs = []
    for percentage in (0, 50, 100):
        config = json.loads(
            (output_dir / f"nano1_balanced_nonpartition_{percentage:03d}.json")
            .read_text()
        )
        assert config["NonPartitionablePercentage"] == percentage
        config.pop("NonPartitionablePercentage")
        config["FormalExperiment"].pop("non_partitionable_percentage")
        configs.append(config)
    assert configs[0] == configs[1] == configs[2]


def test_selection_penalizes_saturated_qoe(tmp_path):
    cases = {
        "d010_a025_p050": ((0.6, 1.0), (0.3, 1.0)),
        "d050_a050_p050": ((0.7, 0.55), (0.4, 0.8)),
    }
    for scenario, metrics in cases.items():
        for method, (deadline_rate, qoe) in zip(
            ("baseline", "feedback-fine-grained"), metrics
        ):
            run_dir = tmp_path / f"{scenario}-{method}"
            run_dir.mkdir()
            (run_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "scenario": scenario,
                        "method": method,
                    }
                )
            )
            (run_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "deadline_missing_rate": deadline_rate,
                        "qoe_score": qoe,
                        "end_to_end_latency_seconds": 2.0,
                    }
                )
            )
    report = select_calibration(tmp_path)
    assert report["selected"]["scenario"] == "d050_a050_p050"


def test_selection_requires_complete_pairs(tmp_path):
    with pytest.raises(ValueError, match="no complete paired"):
        select_calibration(tmp_path)
