import json

from experiments.apply_runtime_profile import apply_profile


def test_runtime_profile_updates_only_measured_cost_fields(tmp_path) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "torch_runtime": {"resolved": "mps"},
                "power_mode": "test-power",
                "bound_policy": "test-bound",
                "bound_margin_fraction": 0.1,
                "cases": {
                    "lane_detection": {
                        "mean_ms": 12.5,
                        "profiled_execution_bound_ms": 20.25,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    source_dir = tmp_path / "configs"
    source_dir.mkdir()
    config_path = source_dir / "mac_loose_example.json"
    original = {
        "DeadlineFactor": 1.5,
        "ArrivalScale": 2.0,
        "dag_list": [[{
            "TaskName": "lane",
            "RunArgs": [1],
            "RunningTime": 999,
            "WorstRunningTime": 1000,
        }]],
    }
    config_path.write_text(json.dumps(original), encoding="utf-8")

    changed = apply_profile(profile_path, source_dir, "mac")
    updated = json.loads(config_path.read_text())

    assert changed == [config_path]
    assert updated["DeadlineFactor"] == original["DeadlineFactor"]
    assert updated["ArrivalScale"] == original["ArrivalScale"]
    assert updated["dag_list"][0][0]["RunningTime"] == 12.5
    assert updated["dag_list"][0][0]["WorstRunningTime"] == 20.25
    assert updated["RuntimeProfile"]["torch_device"] == "mps"

    assert apply_profile(profile_path, source_dir, "mac") == []
