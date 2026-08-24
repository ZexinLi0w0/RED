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
        "MergeThresholdMs": 20,
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
