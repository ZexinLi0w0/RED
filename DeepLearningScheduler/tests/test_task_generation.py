import pytest

from task_generator import (
    DagTimingConfig,
    generate_tasks_from_dag,
    overall_deadline_seconds,
    task_stream_sha256,
    timing_config_from_mapping,
)


def _task(name: str, worst_ms: float) -> dict:
    return {
        "TaskName": name,
        "HandlerId": 5,
        "Priority": 1,
        "Dependencies": [],
        "RunArgs": [1],
        "WorstRunningTime": worst_ms,
    }


def _parallel_dag() -> list:
    return [[[ _task("parallel-a", 10), _task("parallel-b", 20)], _task("serial", 5)]]


def test_deadline_and_arrival_scaling_are_independent() -> None:
    tasks = generate_tasks_from_dag(
        _parallel_dag(),
        deadline_factor=2.0,
        arrival_scale=3.0,
        dag_repeated_times=2,
        parallel_stage_policy="max",
    )

    first_period = tasks[:3]
    assert [task["ReleaseTime"] for task in first_period] == pytest.approx(
        [0.0, 0.0, 0.06]
    )
    assert [task["Deadline"] for task in first_period] == pytest.approx(
        [0.02, 0.04, 0.07]
    )

    second_period = tasks[3:]
    assert [task["ReleaseTime"] for task in second_period] == pytest.approx(
        [0.075, 0.075, 0.135]
    )
    assert [task["Deadline"] for task in second_period] == pytest.approx(
        [0.095, 0.115, 0.145]
    )


def test_parallel_stage_uses_the_same_policy_for_release_and_run_deadline() -> None:
    dag = _parallel_dag()
    timing = DagTimingConfig(
        deadline_factor=2.0,
        arrival_scale=3.0,
        dag_repeated_times=2,
        parallel_stage_policy="max",
    )
    tasks = generate_tasks_from_dag(
        dag,
        deadline_factor=timing.deadline_factor,
        arrival_scale=timing.arrival_scale,
        dag_repeated_times=timing.dag_repeated_times,
        parallel_stage_policy=timing.parallel_stage_policy,
    )

    assert overall_deadline_seconds(dag, timing) == pytest.approx(
        max(task["Deadline"] for task in tasks)
    )
    assert overall_deadline_seconds(dag, timing) == pytest.approx(0.145)


def test_legacy_factor_maps_to_both_explicit_dimensions() -> None:
    timing = timing_config_from_mapping({"RunningTimeFactor": 1.5})
    assert timing == DagTimingConfig(
        deadline_factor=1.5,
        arrival_scale=1.5,
        dag_repeated_times=10,
        parallel_stage_policy="max",
        task_seed=0,
        release_time_skew_threshold_ms=100.0,
    )


def test_mixed_legacy_and_explicit_timing_is_rejected() -> None:
    with pytest.raises(ValueError, match="RunningTimeFactor"):
        timing_config_from_mapping(
            {
                "RunningTimeFactor": 1.5,
                "DeadlineFactor": 1.5,
                "ArrivalScale": 1.0,
            }
        )


def test_release_time_skew_threshold_is_loaded_from_experiment_config() -> None:
    timing = timing_config_from_mapping(
        {
            "DeadlineFactor": 1.0,
            "ArrivalScale": 1.0,
            "ReleaseTimeSkewThresholdMs": 100,
        }
    )
    assert timing.release_time_skew_threshold_ms == pytest.approx(100.0)


def test_legacy_merge_threshold_field_preserves_historical_configs() -> None:
    timing = timing_config_from_mapping(
        {
            "DeadlineFactor": 1.0,
            "ArrivalScale": 1.0,
            "MergeThresholdMs": 20,
        }
    )
    assert timing.release_time_skew_threshold_ms == pytest.approx(20.0)


def test_release_time_skew_threshold_rejects_conflicting_field_names() -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        timing_config_from_mapping(
            {
                "ReleaseTimeSkewThresholdMs": 100,
                "MergeThresholdMs": 20,
            }
        )


def test_generated_stream_is_deterministic_for_a_seed() -> None:
    kwargs = {
        "deadline_factor": 1.0,
        "arrival_scale": 1.0,
        "dag_repeated_times": 4,
        "parallel_stage_policy": "max",
        "non_partitionable_percentage": 50,
        "seed": 2026,
    }
    first = generate_tasks_from_dag(_parallel_dag(), **kwargs)
    second = generate_tasks_from_dag(_parallel_dag(), **kwargs)

    assert first == second
    assert task_stream_sha256(first) == task_stream_sha256(second)
    assert len({task["TaskId"] for task in first}) == len(first)


def test_task_level_drop_threshold_is_preserved() -> None:
    task_config = _task("drop-aware", 10)
    task_config["DropThreshold"] = 0.25

    generated = generate_tasks_from_dag(
        [[task_config]],
        deadline_factor=1.0,
        arrival_scale=1.0,
        dag_repeated_times=1,
    )

    assert generated[0]["DropThreshold"] == pytest.approx(0.25)


def test_invalid_task_level_drop_threshold_is_rejected() -> None:
    task_config = _task("invalid-drop-threshold", 10)
    task_config["DropThreshold"] = 1.5

    with pytest.raises(ValueError, match="DropThreshold"):
        generate_tasks_from_dag(
            [[task_config]],
            deadline_factor=1.0,
            arrival_scale=1.0,
            dag_repeated_times=1,
        )


def test_parallel_release_offsets_create_fixed_predicted_skews() -> None:
    dag = [[[
        {
            "TaskName": "first",
            "HandlerId": 5,
            "Priority": 1,
            "Dependencies": [],
            "RunArgs": [1],
            "WorstRunningTime": 20,
            "ReleaseTimeOffsetMs": 0,
        },
        {
            "TaskName": "second",
            "HandlerId": 5,
            "Priority": 1,
            "Dependencies": [],
            "RunArgs": [3],
            "WorstRunningTime": 20,
            "ReleaseTimeOffsetMs": 50,
        },
        {
            "TaskName": "third",
            "HandlerId": 5,
            "Priority": 1,
            "Dependencies": [],
            "RunArgs": [4],
            "WorstRunningTime": 20,
            "ReleaseTimeOffsetMs": 100,
        },
    ]]]

    tasks = generate_tasks_from_dag(
        dag,
        deadline_factor=1.0,
        arrival_scale=1.0,
        dag_repeated_times=1,
    )

    assert [task["ReleaseTime"] for task in tasks] == pytest.approx(
        [0.0, 0.05, 0.1]
    )
    assert [task["Deadline"] for task in tasks] == pytest.approx(
        [0.02, 0.07, 0.12]
    )
    assert overall_deadline_seconds(
        dag,
        timing_config_from_mapping(
            {
                "DeadlineFactor": 1.0,
                "ArrivalScale": 1.0,
                "DagRepeatedTimes": 1,
            }
        ),
    ) == pytest.approx(0.12)


def test_atomic_positions_are_nested_across_ratios() -> None:
    common = {
        "deadline_factor": 1.0,
        "arrival_scale": 1.0,
        "dag_repeated_times": 10,
        "parallel_stage_policy": "max",
        "seed": 42,
    }
    tasks_50 = generate_tasks_from_dag(
        _parallel_dag(), non_partitionable_percentage=50, **common
    )
    tasks_100 = generate_tasks_from_dag(
        _parallel_dag(), non_partitionable_percentage=100, **common
    )

    positions_50 = {
        task["TaskPosition"]
        for task in tasks_50
        if task["IsNonPartitionable"]
    }
    positions_100 = {
        task["TaskPosition"]
        for task in tasks_100
        if task["IsNonPartitionable"]
    }
    assert positions_50 < positions_100


def test_seed_changes_atomic_positions_without_changing_offered_work() -> None:
    common = {
        "deadline_factor": 1.0,
        "arrival_scale": 1.0,
        "dag_repeated_times": 10,
        "parallel_stage_policy": "max",
        "non_partitionable_percentage": 50,
    }
    first = generate_tasks_from_dag(_parallel_dag(), seed=1, **common)
    second = generate_tasks_from_dag(_parallel_dag(), seed=2, **common)

    first_positions = [task["TaskPosition"] for task in first]
    second_positions = [task["TaskPosition"] for task in second]
    assert first_positions == second_positions
    assert [task["IsNonPartitionable"] for task in first] != [
        task["IsNonPartitionable"] for task in second
    ]
