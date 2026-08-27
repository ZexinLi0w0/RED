import logging

import pytest

from burst_task_manager import (
    BurstTaskManager,
    BurstWorkloadConfig,
    burst_workload_config_from_mapping,
)


def _base_tasks(group_count=8):
    tasks = []
    for period in range(group_count):
        for stage in range(2):
            task_id = f"base-p{period}-s{stage}"
            tasks.append(
                {
                    "TaskId": task_id,
                    "ConstituentTaskIds": [task_id],
                    "DagIndex": 0,
                    "DagPeriod": period,
                    "StageIndex": stage,
                    "MergeKey": f"dag=0/period={period}/stage={stage}",
                    "HandlerId": 5,
                    "ReleaseTime": period + 0.1 * stage,
                    "Deadline": period + 0.5 + 0.1 * stage,
                    "Priority": 3,
                    "DropThreshold": 0.25,
                    "Dependencies": [] if stage == 0 else [1],
                }
            )
    return tasks


def _manager(regime, duration=None):
    return BurstTaskManager(
        workload_config=BurstWorkloadConfig(
            regime=regime,
            burst_start_seconds=2.0,
            transient_duration_seconds=duration,
            release_horizon_seconds=8.0,
        ),
        management_enabled=False,
        logger=logging,
    )


def test_transient_and_sustained_use_distinct_release_windows() -> None:
    base = _base_tasks()

    transient = _manager("transient", duration=2.0).generate_burst_tasks(
        base, 100
    )
    sustained = _manager("sustained").generate_burst_tasks(base, 100)

    assert sorted({task["BurstSourceDagPeriod"] for task in transient}) == [2, 3]
    assert sorted({task["BurstSourceDagPeriod"] for task in sustained}) == [
        2,
        3,
        4,
        5,
        6,
        7,
    ]


def test_fifty_percent_burst_is_distributed_across_the_window() -> None:
    duplicates = _manager("sustained").generate_burst_tasks(
        _base_tasks(), 50
    )

    assert sorted({task["BurstSourceDagPeriod"] for task in duplicates}) == [
        3,
        5,
        7,
    ]


def test_burst_clones_keep_timing_and_priority_but_use_independent_periods() -> None:
    base = _base_tasks()
    duplicates = _manager("transient", duration=2.0).generate_burst_tasks(
        base, 100
    )

    assert {task["DagPeriod"] for task in duplicates} == {8, 9}
    assert all(task["Priority"] == 3 for task in duplicates)
    for duplicate in duplicates:
        source = next(
            task
            for task in base
            if task["DagPeriod"] == duplicate["BurstSourceDagPeriod"]
            and task["StageIndex"] == duplicate["StageIndex"]
        )
        assert duplicate["ReleaseTime"] == source["ReleaseTime"]
        assert duplicate["Deadline"] == source["Deadline"]
        assert duplicate["DropThreshold"] == source["DropThreshold"]
        assert f"period={duplicate['DagPeriod']}" in duplicate["MergeKey"]


@pytest.mark.parametrize(
    "mapping, message",
    (
        ({}, "burst_regime"),
        (
            {
                "burst_regime": "transient",
                "burst_start_seconds": 1.0,
                "release_horizon_seconds": 2.0,
            },
            "transient_duration_seconds",
        ),
        (
            {
                "burst_regime": "sustained",
                "burst_start_seconds": 2.0,
                "release_horizon_seconds": 2.0,
            },
            "release_horizon_seconds",
        ),
    ),
)
def test_invalid_burst_workload_config_is_rejected(mapping, message) -> None:
    with pytest.raises(ValueError, match=message):
        burst_workload_config_from_mapping(mapping)


def test_release_horizon_must_cover_every_base_release() -> None:
    manager = BurstTaskManager(
        workload_config=BurstWorkloadConfig(
            regime="sustained",
            burst_start_seconds=0.0,
            release_horizon_seconds=6.0,
        ),
        logger=logging,
    )

    with pytest.raises(ValueError, match="cover every base-task ReleaseTime"):
        manager.generate_burst_tasks(_base_tasks(), 100)
