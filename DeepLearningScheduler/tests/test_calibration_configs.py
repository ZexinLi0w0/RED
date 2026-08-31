import json
from decimal import Decimal

from experiments.build_calibration_configs import build_grid


def test_calibration_grid_changes_only_deadline_factor(tmp_path) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "generated"
    source_dir.mkdir()
    source_config = {
        "DeadlineFactor": 1.5,
        "ArrivalScale": 2.5,
        "DagRepeatedTimes": 10,
        "ParallelStagePolicy": "max",
        "TaskSeed": 0,
        "ReleaseTimeSkewThresholdMs": 20,
        "QoELambda": 0.05,
        "dag_list": [],
    }
    (source_dir / "agx_loose_example.json").write_text(
        json.dumps(source_config), encoding="utf-8"
    )

    index = build_grid(
        source_dir, output_dir, [Decimal("0.8"), Decimal("1.2")]
    )

    assert len(index["configs"]) == 2
    generated = json.loads(
        (output_dir / "agx_cal_a080_example.json").read_text()
    )
    assert generated["DeadlineFactor"] == 0.8
    assert generated["ArrivalScale"] == source_config["ArrivalScale"]
    assert generated["dag_list"] == source_config["dag_list"]

    # Regeneration is an idempotent verification, not an overwrite.
    assert build_grid(
        source_dir, output_dir, [Decimal("0.8"), Decimal("1.2")]
    ) == index


def test_calibration_grid_can_be_limited_to_one_device(tmp_path) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "generated"
    source_dir.mkdir()
    config = {
        "DeadlineFactor": 1.0,
        "ArrivalScale": 1.0,
        "dag_list": [],
    }
    for device in ("mac", "agx"):
        (source_dir / f"{device}_loose_example.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

    index = build_grid(
        source_dir, output_dir, [Decimal("0.8")], devices=["mac"]
    )

    assert {entry["device"] for entry in index["configs"]} == {"mac"}
    assert (output_dir / "mac_cal_a080_example.json").is_file()
    assert not (output_dir / "agx_cal_a080_example.json").exists()


def test_calibration_grid_can_be_limited_to_one_scenario(tmp_path) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "generated"
    source_dir.mkdir()
    config = {
        "DeadlineFactor": 1.0,
        "ArrivalScale": 1.0,
        "dag_list": [],
    }
    for scenario in ("urban_navigation", "night_driving"):
        (source_dir / f"nano_loose_{scenario}.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

    index = build_grid(
        source_dir,
        output_dir,
        [Decimal("1.08")],
        devices=["nano"],
        scenarios=["night_driving"],
    )

    assert {entry["scenario"] for entry in index["configs"]} == {"night_driving"}
    assert (output_dir / "nano_cal_a108_night_driving.json").is_file()
    assert not (output_dir / "nano_cal_a108_urban_navigation.json").exists()
