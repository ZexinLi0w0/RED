import logging

import pytest

from burst_task_manager import (
    BurstTaskManager,
    BurstWorkloadConfig,
)


def _manager(**overrides):
    arguments = {
        "gpu_threshold": 90.0,
        "queue_threshold": 8,
        "persistence_window": 3,
        "workload_config": BurstWorkloadConfig(
            regime="sustained",
            burst_start_seconds=0.0,
            release_horizon_seconds=1.0,
        ),
        "logger": logging,
    }
    arguments.update(overrides)
    return BurstTaskManager(**arguments)


def test_paper_burst_defaults_are_exposed_in_statistics() -> None:
    manager = _manager()

    statistics = manager.get_burst_statistics()

    assert statistics["gpu_threshold"] == 90.0
    assert statistics["queue_threshold"] == 8
    assert statistics["persistence_window"] == 3


def test_overload_requires_the_configured_number_of_consecutive_ticks() -> None:
    manager = _manager()
    health = {"gpu_utilization": 95.0, "queue_length": 0}
    manager.health_monitor.get_system_health = lambda: health

    assert not manager.is_overload_detected()
    assert not manager.is_overload_detected()
    assert manager.is_overload_detected()
    assert manager.burst_mode_active
    assert manager.overload_activation_count == 1
    assert manager.maximum_consecutive_overload_ticks == 3

    health["gpu_utilization"] = 0.0
    assert not manager.is_overload_detected()
    assert manager.consecutive_overload_ticks == 0
    assert not manager.burst_mode_active


def test_queue_length_participates_in_sustained_overload_detection() -> None:
    manager = _manager(persistence_window=1)
    manager.health_monitor.get_system_health = lambda: {
        "gpu_utilization": 0.0,
        "queue_length": manager.health_monitor.queue_length,
    }

    manager.update_queue_length(9)

    assert manager.is_overload_detected()


def test_overload_ticks_are_time_gated() -> None:
    manager = _manager(overload_sample_interval_seconds=0.005)
    manager.health_monitor.get_system_health = lambda: {
        "gpu_utilization": 95.0,
        "queue_length": 0,
    }

    assert not manager.is_overload_detected(sample_time=0.000)
    assert not manager.is_overload_detected(sample_time=0.001)
    assert manager.consecutive_overload_ticks == 1
    assert not manager.is_overload_detected(sample_time=0.005)
    assert manager.is_overload_detected(sample_time=0.010)


def test_transient_recovery_only_sheds_residual_burst_work() -> None:
    manager = BurstTaskManager(
        gpu_threshold=100.0,
        queue_threshold=1,
        queue_recovery_threshold=0,
        persistence_window=1,
        workload_config=BurstWorkloadConfig(
            regime="transient",
            burst_start_seconds=0.0,
            transient_duration_seconds=1.0,
            release_horizon_seconds=2.0,
        ),
        logger=logging,
    )
    burst_task = {
        "TaskId": "residual-burst",
        "ReleaseTime": 0.5,
        "Deadline": 2.0,
        "Priority": 1,
        "DropThreshold": 0.5,
        "Droppable": True,
        "IsBurstTask": True,
        "BurstRegime": "transient",
    }
    baseline_task = {
        "TaskId": "post-window-baseline",
        "ReleaseTime": 1.1,
        "Deadline": 2.0,
        "Priority": 1,
        "DropThreshold": 0.5,
        "Droppable": True,
        "IsBurstTask": False,
    }
    manager.update_queue_length(2)

    remaining, dropped = manager.proactive_drop(
        [burst_task, baseline_task], current_time=1.1
    )

    assert [task["TaskId"] for task in dropped] == ["residual-burst"]
    assert [task["TaskId"] for task in remaining] == [
        "post-window-baseline"
    ]
    assert manager.workload_phase == "recovery"
    manager.finalize_workload(1.2)
    assert manager.workload_phase == "normal"
    assert manager.transient_recovery_completed is True


@pytest.mark.parametrize(
    "arguments, message",
    (
        ({"gpu_threshold": 101}, "gpu_threshold"),
        ({"queue_threshold": -1}, "queue_threshold"),
        ({"persistence_window": 0}, "persistence_window"),
    ),
)
def test_invalid_burst_sensitivity_parameters_are_rejected(arguments, message) -> None:
    with pytest.raises(ValueError, match=message):
        _manager(**arguments)


def test_burst_duplicates_have_independent_reporting_identities() -> None:
    manager = _manager()
    base = [{
        "TaskId": "base",
        "ConstituentTaskIds": ["base"],
        "Priority": 1,
        "DagIndex": 0,
        "DagPeriod": 0,
        "StageIndex": 0,
        "MergeKey": "dag=0/period=0/stage=0",
        "ReleaseTime": 0.0,
        "Deadline": 0.1,
    }]

    duplicates = manager.generate_burst_tasks(base, 100)

    assert duplicates[0]["TaskId"] == "base_burst_sustained_1"
    assert duplicates[0]["ConstituentTaskIds"] == [
        "base_burst_sustained_1"
    ]
