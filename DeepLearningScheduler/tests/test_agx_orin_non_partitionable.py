import json

import pytest

from experiments.agx_orin_non_partitionable import (
    build_calibration,
    build_formal,
    build_source,
    select_calibration,
)


def _template(path):
    value = {
        "DeadlineFactor": 1.5,
        "ArrivalScale": 1.5,
        "DagRepeatedTimes": 10,
        "MergeThresholdMs": 20,
        "QoELambda": 0.05,
        "dag_list": [
            [
                {
                    "TaskName": "x",
                    "RunArgs": [1],
                    "RunningTime": 999,
                    "WorstRunningTime": 999,
                }
            ]
        ],
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _profile(path):
    value = {
        "torch_runtime": {"resolved": "cuda"},
        "power_mode": "agx-orin-maxn",
        "bound_policy": "observed maximum times (1 + fixed margin)",
        "bound_margin_fraction": 0.1,
        "cases": {
            "lane_detection": {
                "mean_ms": 28.5,
                "profiled_execution_bound_ms": 32.0,
            }
        },
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_source_uses_measured_runtime_profile(tmp_path):
    output = tmp_path / "source.json"
    config = build_source(
        _template(tmp_path / "template.json"),
        _profile(tmp_path / "profile.json"),
        output,
    )
    task = config["dag_list"][0][0]
    assert task["RunningTime"] == 28.5
    assert task["WorstRunningTime"] == 32.0
    assert config["ReleaseTimeSkewThresholdMs"] == 20
    assert "MergeThresholdMs" not in config
    assert config["RuntimeProfile"]["torch_device"] == "cuda"


def test_calibration_grid_changes_load_and_deadline(tmp_path):
    source = tmp_path / "source.json"
    config = build_source(
        _template(tmp_path / "template.json"),
        _profile(tmp_path / "profile.json"),
        source,
    )
    assert config["DeadlineFactor"] == 1.0
    index = build_calibration(source, tmp_path / "cal")
    assert len(index["configs"]) == 12
    generated = json.loads(
        (tmp_path / "cal" / "agx_orin_cal_d100_a075_p050.json").read_text()
    )
    assert generated["DeadlineFactor"] == 1.0
    assert generated["ArrivalScale"] == 0.75
    assert generated["NonPartitionablePercentage"] == 50


def test_calibration_grid_accepts_refined_timing_values(tmp_path):
    source = tmp_path / "source.json"
    build_source(
        _template(tmp_path / "template.json"),
        _profile(tmp_path / "profile.json"),
        source,
    )
    index = build_calibration(
        source,
        tmp_path / "cal",
        deadline_factors=(2.0, 4.0),
        arrival_scales=(4.0, 8.0),
    )
    assert len(index["configs"]) == 4
    assert (
        tmp_path / "cal" / "agx_orin_cal_d400_a800_p050.json"
    ).is_file()


def test_formal_configs_differ_only_by_percentage(tmp_path):
    source = tmp_path / "source.json"
    build_source(
        _template(tmp_path / "template.json"),
        _profile(tmp_path / "profile.json"),
        source,
    )
    output_dir = tmp_path / "formal"
    index = build_formal(source, output_dir, 4.0, 1.0, 10)
    assert index["seeds"] == [101, 202, 303, 404, 505]
    configs = []
    for percentage in (0, 50, 100):
        config = json.loads(
            (
                output_dir
                / f"agx_orin_balanced_nonpartition_{percentage:03d}.json"
            ).read_text()
        )
        assert config["NonPartitionablePercentage"] == percentage
        config.pop("NonPartitionablePercentage")
        config["FormalExperiment"].pop("non_partitionable_percentage")
        configs.append(config)
    assert configs[0] == configs[1] == configs[2]


def _result(root, scenario, method, deadline_rate, qoe):
    run_dir = root / f"{scenario}-{method}"
    run_dir.mkdir()
    (run_dir / "manifest.json").write_text(
        json.dumps({"status": "complete", "scenario": scenario, "method": method})
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


def test_selection_prefers_candidate_that_passes_quality_gate(tmp_path):
    cases = {
        "d100_a075_p050": ((0.6, 1.0), (0.5, 1.0), (0.35, 1.0)),
        "d400_a100_p050": ((0.7, 0.70), (0.5, 0.82), (0.3, 0.92)),
    }
    methods = ("baseline", "llf-dag", "feedback-fine-grained")
    for scenario, values in cases.items():
        for method, (deadline_rate, qoe) in zip(methods, values):
            _result(tmp_path, scenario, method, deadline_rate, qoe)
    selected = select_calibration(tmp_path)["selected"]
    assert selected["scenario"] == "d400_a100_p050"
    assert selected["quality_gate"]["accepted"] is True


def test_selection_requires_complete_method_set(tmp_path):
    _result(tmp_path, "d400_a100_p050", "baseline", 0.5, 0.8)
    with pytest.raises(ValueError, match="no complete paired"):
        select_calibration(tmp_path)
