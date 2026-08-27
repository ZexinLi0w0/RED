import csv
import hashlib
import json

from experiments.parameter_sensitivity import (
    DEFAULT_SEEDS,
    PAPER_DEFAULTS,
    SENSITIVITY_POINTS,
    _seeds_for_repetitions,
    generate_study_plan,
    summarize_study,
)


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _base_configs(tmp_path):
    task_path = tmp_path / "base-task.json"
    burst_path = tmp_path / "base-burst.json"
    _write_json(
        task_path,
        {
            "DeadlineFactor": 1.0,
            "ArrivalScale": 1.0,
            "DagRepeatedTimes": 1,
            "ParallelStagePolicy": "max",
            "BurstTaskRatio": 100,
            "dag_list": [[{
                "TaskName": "node",
                "HandlerId": 5,
                "Priority": 1,
                "Dependencies": [],
                "RunArgs": [1],
                "WorstRunningTime": 1,
            }]],
        },
    )
    _write_json(
        burst_path,
        {
            "burst_enabled": True,
            "burst_regime": "sustained",
            "burst_start_seconds": 0.0,
            "release_horizon_seconds": 0.1,
            "gpu_threshold": 10,
            "queue_threshold": 99,
            "persistence_window": 7,
            "drop_threshold": 0.5,
            "monitoring_interval": 0.05,
            "scheduler_tick_seconds": 0.005,
        },
    )
    return task_path, burst_path


def test_plan_defaults_to_one_run_per_point(tmp_path) -> None:
    task_path, burst_path = _base_configs(tmp_path)

    plan = generate_study_plan(task_path, burst_path, tmp_path / "study")

    assert len(plan["points"]) == 47
    assert plan["planned_run_count"] == 47
    assert plan["repetitions_per_point"] == 1
    assert plan["seeds"] == list(DEFAULT_SEEDS) == [101]
    assert [point["point_slug"] for point in plan["points"]] == [
        point.slug for point in SENSITIVITY_POINTS
    ]


def test_repetition_count_generates_deterministic_seeds() -> None:
    assert _seeds_for_repetitions(1) == (101,)
    assert _seeds_for_repetitions(3) == (101, 202, 303)


def test_generated_points_keep_the_two_blocks_independent(tmp_path) -> None:
    task_path, burst_path = _base_configs(tmp_path)
    plan = generate_study_plan(
        task_path, burst_path, tmp_path / "study", seeds=(1, 2)
    )

    for point in plan["points"]:
        generated_task = json.loads(
            open(point["task_config_path"], encoding="utf-8").read()
        )
        generated_burst = json.loads(
            open(point["burst_config_path"], encoding="utf-8").read()
        )
        assert generated_task["MovingAverageWindow"] == point[
            "executed_parameters"
        ]["moving_average_window"]
        assert generated_task["ReleaseTimeSkewThresholdMs"] == point[
            "executed_parameters"
        ]["release_time_skew_threshold_ms"]
        assert generated_burst["gpu_threshold"] == point[
            "executed_parameters"
        ]["gpu_threshold"]
        assert generated_burst["queue_threshold"] == point[
            "executed_parameters"
        ]["queue_threshold"]
        assert generated_burst["persistence_window"] == point[
            "executed_parameters"
        ]["persistence_window"]
        assert generated_burst["burst_enabled"] == point["executed_parameters"][
            "burst_enabled"
        ]
        if point["block"] == "refinement":
            assert generated_task["BurstTaskRatio"] == 0
            assert generated_task["NonPartitionablePercentage"] == 0
        else:
            assert generated_task["BurstTaskRatio"] == 100
            assert generated_task["NonPartitionablePercentage"] == 100
            assert generated_task["MovingAverageWindow"] == PAPER_DEFAULTS[
                "moving_average_window"
            ]
            assert generated_task["ReleaseTimeSkewThresholdMs"] == PAPER_DEFAULTS[
                "release_time_skew_threshold_ms"
            ]

    refinement = [point for point in plan["points"] if point["block"] == "refinement"]
    burst = [point for point in plan["points"] if point["block"] == "burst-management"]
    assert len(refinement) == 4 * 5
    assert len(burst) == 3 * 3 * 3


def test_summarizer_extracts_table_values_from_validated_run_artifacts(tmp_path) -> None:
    task_path, burst_path = _base_configs(tmp_path)
    output_root = tmp_path / "study"
    plan = generate_study_plan(
        task_path, burst_path, output_root, seeds=(1, 2)
    )
    for point in plan["points"]:
        for seed in plan["seeds"]:
            run_id = f"{point['point_slug']}-seed{seed}"
            run_dir = output_root / "runs" / run_id
            parameters = point["executed_parameters"]
            summary = {
                "run_id": run_id,
                "offered_task_count": 2,
                "offered_task_stream_sha256": "stream",
                "end_to_end_latency_seconds": point["point_order"] + seed,
                "deadline_missing_rate": 0.1 * seed,
                "qoe_score": 1.0 - 0.1 * seed,
                "release_time_skew_threshold_ms": parameters["release_time_skew_threshold_ms"],
                "moving_average_reassignment": {
                    "window": parameters["moving_average_window"]
                },
                "burst_statistics": (
                    {
                        "gpu_threshold": parameters["gpu_threshold"],
                        "queue_threshold": parameters["queue_threshold"],
                        "persistence_window": parameters["persistence_window"],
                    }
                    if parameters["burst_enabled"]
                    else None
                ),
            }
            summary_path = run_dir / "summary.json"
            _write_json(summary_path, summary)
            summary_hash = hashlib.sha256(summary_path.read_bytes()).hexdigest()
            _write_json(
                run_dir / "manifest.json",
                {
                    "run_id": run_id,
                    "status": "complete",
                    "point_slug": point["point_slug"],
                    "seed": seed,
                    "offered_task_count": 2,
                    "offered_task_stream_sha256": "stream",
                    "executed_parameters": parameters,
                    "summary_sha256": summary_hash,
                },
            )

    report = summarize_study(output_root)

    assert report["complete_run_count"] == 94
    assert report["aggregation"] == "arithmetic mean across 2 configured repetitions"
    assert len(report["points"]) == 47
    first = report["points"][0]
    assert first["metrics"]["end_to_end_latency_seconds"]["mean"] == 2.5
    table_path = output_root / "report" / "parameter_sensitivity_table.csv"
    with table_path.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    assert len(rows) == 47
    assert rows[0]["end_to_end_latency_seconds"] == "2.500"
    assert rows[0]["deadline_missing_rate"] == "0.150"
    assert rows[0]["qoe_score"] == "0.850"
    assert (
        output_root / "report" / "parameter_sensitivity_table_rows.tex"
    ).is_file()
