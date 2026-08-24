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
        merge_threshold_ms=20.0,
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


def test_merge_threshold_is_loaded_from_the_experiment_config() -> None:
    timing = timing_config_from_mapping(
        {
            "DeadlineFactor": 1.0,
            "ArrivalScale": 1.0,
            "MergeThresholdMs": 100,
        }
    )
    assert timing.merge_threshold_ms == pytest.approx(100.0)


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
