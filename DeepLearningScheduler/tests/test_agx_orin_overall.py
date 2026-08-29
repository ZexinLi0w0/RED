import json

from experiments.agx_orin_overall import (
    METHODS,
    SCENARIOS,
    build_calibration,
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
