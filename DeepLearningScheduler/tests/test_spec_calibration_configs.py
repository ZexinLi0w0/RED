import json

from experiments.build_spec_calibration_configs import build_grid


def test_spec_grid_supports_scenario_specific_arrival_scales(tmp_path) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "generated"
    source_dir.mkdir()
    source = {
        "DeadlineFactor": 1.0,
        "ArrivalScale": 1.0,
        "QoELambda": 0.05,
        "dag_list": [[{"TaskName": "example"}]],
    }
    for scenario in ("urban_navigation", "night_driving"):
        (source_dir / f"nano_loose_{scenario}.json").write_text(
            json.dumps(source), encoding="utf-8"
        )
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "device": "nano",
                "workloads": [
                    {
                        "scenario": "urban_navigation",
                        "arrival_scale": 1.6,
                        "deadline_factors": [2.0, 2.4],
                    },
                    {
                        "scenario": "night_driving",
                        "arrival_scale": 1.0,
                        "deadline_factors": [1.1, 1.2],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    index = build_grid(spec_path, source_dir, output_dir)

    assert len(index["configs"]) == 4
    urban = json.loads(
        (output_dir / "nano_cal_s160_a200_urban_navigation.json").read_text()
    )
    night = json.loads(
        (output_dir / "nano_cal_s100_a110_night_driving.json").read_text()
    )
    assert (urban["ArrivalScale"], urban["DeadlineFactor"]) == (1.6, 2.0)
    assert (night["ArrivalScale"], night["DeadlineFactor"]) == (1.0, 1.1)
    assert urban["QoELambda"] == night["QoELambda"] == 0.05

    assert build_grid(spec_path, source_dir, output_dir) == index
