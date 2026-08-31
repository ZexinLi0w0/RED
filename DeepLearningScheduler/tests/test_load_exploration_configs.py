import json
from decimal import Decimal

from experiments.build_load_exploration_configs import build_grid


def test_load_exploration_grid_changes_only_arrival_and_deadline(tmp_path) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "generated"
    source_dir.mkdir()
    source_config = {
        "DeadlineFactor": 1.0,
        "ArrivalScale": 1.0,
        "DagRepeatedTimes": 10,
        "QoELambda": 0.05,
        "dag_list": [[{"TaskName": "example"}]],
    }
    (source_dir / "nano_loose_urban_navigation.json").write_text(
        json.dumps(source_config), encoding="utf-8"
    )

    index = build_grid(
        source_dir,
        output_dir,
        [Decimal("1.25"), Decimal("1.5")],
        [Decimal("1.2"), Decimal("2.0")],
        ["urban_navigation"],
    )

    assert len(index["configs"]) == 4
    generated = json.loads(
        (output_dir / "nano_load_s125_a120_urban_navigation.json").read_text()
    )
    assert generated["ArrivalScale"] == 1.25
    assert generated["DeadlineFactor"] == 1.2
    assert generated["DagRepeatedTimes"] == source_config["DagRepeatedTimes"]
    assert generated["QoELambda"] == source_config["QoELambda"]
    assert generated["dag_list"] == source_config["dag_list"]

    assert build_grid(
        source_dir,
        output_dir,
        [Decimal("1.25"), Decimal("1.5")],
        [Decimal("1.2"), Decimal("2.0")],
        ["urban_navigation"],
    ) == index
