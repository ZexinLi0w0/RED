import logging

import pytest

from burst_task_manager import BurstTaskManager


def _manager(**overrides):
    arguments = {
        "gpu_threshold": 90.0,
        "queue_threshold": 8,
        "persistence_window": 3,
        "logger": logging,
    }
    arguments.update(overrides)
    return BurstTaskManager(**arguments)


def test_paper_burst_defaults_are_exposed_in_statistics() -> None:
    manager = BurstTaskManager(logger=logging)

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
    base = [{"TaskId": "base", "ConstituentTaskIds": ["base"], "Priority": 1}]

    duplicates = manager.generate_burst_tasks(base, 100)

    assert duplicates[0]["TaskId"] == "base_burst_0"
    assert duplicates[0]["ConstituentTaskIds"] == ["base_burst_0"]
