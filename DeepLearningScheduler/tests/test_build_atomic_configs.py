import json

from experiments.build_atomic_configs import build_atomic_configs


def test_build_atomic_configs_change_only_ratio_and_metadata(tmp_path):
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "DeadlineFactor": 1.25,
                "ArrivalScale": 1.5,
                "dag_list": [[{"TaskName": "demo"}]],
            }
        ),
        encoding="utf-8",
    )

    index_path, outputs = build_atomic_configs(
        source,
        tmp_path / "derived",
        device="mac",
        scenario="demo",
        ratios=(0, 50, 100),
    )

    assert [row["ratio_percent"] for row in outputs] == [0, 50, 100]
    index = json.loads(index_path.read_text())
    assert index["ratios_percent"] == [0, 50, 100]
    for ratio in (0, 50, 100):
        config = json.loads(
            (tmp_path / "derived" / f"mac_atomic{ratio}_demo.json").read_text()
        )
        assert config["DeadlineFactor"] == 1.25
        assert config["ArrivalScale"] == 1.5
        assert config["NonPartitionablePercentage"] == ratio
        assert config["AtomicExperiment"]["ratio_percent"] == ratio
