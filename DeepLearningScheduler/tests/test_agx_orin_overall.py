import json

import experiments.agx_orin_overall as agx_orin_overall

from experiments.agx_orin_overall import (
    METHODS,
    SCENARIOS,
    build_calibration,
    freeze_configs,
    select_edf_calibration,
    validate_matrix,
)


def _write_template(path, scenario):
    path.write_text(
        json.dumps(
            {
                "DeadlineFactor": 1.5,
                "ArrivalScale": 1.5,
                "DagRepeatedTimes": 10,
                "QoELambda": 0.05,
                "dag_list": [[{
                    "TaskName": f"{scenario}_lane",
                    "HandlerId": 5,
                    "Priority": 1,
                    "Dependencies": [],
                    "RunArgs": [1],
                    "RunningTime": 999,
                    "WorstRunningTime": 1000,
                }]],
            }
        ),
        encoding="utf-8",
    )


def test_build_calibration_profiles_all_scenarios(tmp_path):
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    for scenario in SCENARIOS:
        _write_template(template_dir / f"agx_loose_{scenario}.json", scenario)

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "torch_runtime": {"resolved": "cuda:0"},
                "power_mode": "MAXN",
                "bound_policy": "maximum plus margin",
                "bound_margin_fraction": 0.1,
                "cases": {
                    "lane_detection": {
                        "mean_ms": 12.5,
                        "profiled_execution_bound_ms": 14.0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "overall"
    index = build_calibration(
        template_dir,
        profile_path,
        output_dir,
        ((2.0, 3.0), (4.0, 5.0)),
    )

    assert len(index["configs"]) == len(SCENARIOS) * 2
    assert tuple(METHODS) == (
        "baseline",
        "llf-dag",
        "fine-grained",
        "feedback",
        "feedback-fine-grained",
    )
    for entry in index["configs"]:
        config = json.loads((output_dir / entry["config_path"]).read_text())
        assert config["DeadlineFactor"] in {2.0, 4.0}
        assert config["ArrivalScale"] in {3.0, 5.0}
        task = config["dag_list"][0][0]
        assert task["RunningTime"] == 12.5
        assert task["WorstRunningTime"] == 14.0
        assert config["RuntimeProfile"]["torch_device"] == "cuda:0"
        assert config["SourceExperiment"]["scenario"] == entry["scenario"]


def test_edf_selection_and_pilot_freeze(tmp_path):
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    for scenario in SCENARIOS:
        _write_template(template_dir / f"agx_loose_{scenario}.json", scenario)

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "torch_runtime": {"resolved": "cuda:0"},
                "power_mode": "MAXN",
                "bound_policy": "maximum plus margin",
                "bound_margin_fraction": 0.1,
                "cases": {
                    "lane_detection": {
                        "mean_ms": 12.5,
                        "profiled_execution_bound_ms": 14.0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "overall"
    index = build_calibration(
        template_dir,
        profile_path,
        output_dir,
        ((2.0, 3.0), (4.0, 5.0)),
    )
    index_path = output_dir / "calibration_index.json"

    runs_root = tmp_path / "runs"
    for entry in index["configs"]:
        accepted = entry["deadline_factor"] == 2.0
        run_dir = runs_root / f"{entry['scenario']}-{entry['profile']}"
        run_dir.mkdir(parents=True)
        (run_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "run_id": run_dir.name,
                    "scenario": entry["scenario"],
                    "profile": entry["profile"],
                    "method": "baseline",
                    "status": "complete",
                    "config_sha256": entry["config_sha256"],
                    "git_commit": "abc123",
                    "seed": 11,
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "summary.json").write_text(
            json.dumps(
                {
                    "deadline_missing_rate": 0.5 if accepted else 1.0,
                    "qoe_score": 0.6 if accepted else 1.0,
                    "end_to_end_latency_seconds": 1.0 if accepted else 2.0,
                }
            ),
            encoding="utf-8",
        )

    selection = select_edf_calibration(index_path, runs_root)
    assert selection["git_commits"] == ["abc123"]
    assert selection["seeds"] == [11]
    for scenario in SCENARIOS:
        assert selection["selected"][scenario]["quality_gate"]["accepted"]
        assert selection["selected"][scenario]["deadline_factor"] == 2.0
        assert selection["selected"][scenario]["arrival_scale"] == 3.0

    selection_path = output_dir / "selection_report.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    pilot_dir = output_dir / "pilot"
    frozen = freeze_configs(
        index_path,
        selection_path,
        pilot_dir,
        "pilot",
    )
    assert frozen["seeds"] == [11, 22, 33]
    assert len(frozen["configs"]) == len(SCENARIOS)
    for entry in frozen["configs"]:
        config = json.loads((pilot_dir / entry["config_path"]).read_text())
        assert config["DeadlineFactor"] == 2.0
        assert config["ArrivalScale"] == 3.0
        assert config["PilotExperiment"]["calibration_frozen_before_formal_runs"] is False


def test_validation_accepts_two_interior_qoe_methods_with_clear_spread(
    tmp_path, monkeypatch
):
    deadline_rates = [0.81, 0.78, 0.42, 0.22, 0.18]
    qoe_scores = [0.40, 0.65, 1.0, 1.0, 1.0]
    aggregates = []
    for scenario in SCENARIOS:
        for index, method in enumerate(METHODS):
            aggregates.append(
                {
                    "device": "agx",
                    "profile": "pilot",
                    "scenario": scenario,
                    "method": method,
                    "seeds": [11, 22, 33],
                    "metrics": {
                        "deadline_missing_rate": {"mean": deadline_rates[index]},
                        "qoe_score": {"mean": qoe_scores[index]},
                    },
                }
            )

    monkeypatch.setattr(
        agx_orin_overall,
        "summarize",
        lambda _runs_root: {
            "validation": {
                "complete_run_count": 45,
                "methods": list(METHODS),
                "git_commits": ["abc123"],
                "torch_devices": ["cuda:0"],
            },
            "aggregates": aggregates,
        },
    )

    report = validate_matrix(tmp_path, "pilot", (11, 22, 33))
    assert report["quality_gate"]["accepted"]
    for scenario in SCENARIOS:
        checks = report["quality_gate"]["scenario_checks"][scenario]["checks"]
        assert checks["at_least_two_interior_qoe_scores"]
