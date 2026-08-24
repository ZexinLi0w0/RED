import pytest

from task_generator import (
    DagTimingConfig,
    generate_tasks_from_dag,
    overall_deadline_seconds,
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
