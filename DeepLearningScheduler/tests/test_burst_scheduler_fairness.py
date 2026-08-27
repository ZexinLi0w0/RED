import logging
from collections import defaultdict
from queue import Queue

from burst_task_manager import BurstTaskManager
from task_generator import generate_tasks_from_dag
from task_scheduler import TaskSchedule


def _tasks():
    dag = [[{
        "TaskName": "node",
        "HandlerId": 5,
        "Priority": 1,
        "Dependencies": [],
        "RunArgs": [1],
        "WorstRunningTime": 100,
    }]]
    return generate_tasks_from_dag(
        dag,
        deadline_factor=1.0,
        arrival_scale=1.0,
        dag_repeated_times=4,
        seed=101,
    )


def _burst_config():
    return {
        "burst_enabled": True,
        "burst_regime": "sustained",
        "burst_start_seconds": 0.0,
        "release_horizon_seconds": 0.5,
        "gpu_threshold": 90.0,
        "queue_threshold": 8,
        "persistence_window": 3,
        "drop_threshold": 0.5,
        "monitoring_interval": 0.05,
    }


def test_all_methods_receive_identical_burst_workload(monkeypatch) -> None:
    monkeypatch.setattr(BurstTaskManager, "start_monitoring", lambda self: None)
    methods = {
        "baseline": "edf",
        "llf-dag": "llf_dag",
        "feedback-fine-grained": "edf",
    }
    schedulers = {}
    for method, scheduler_name in methods.items():
        scheduler = TaskSchedule(
            _tasks(),
            handler_status=defaultdict(int),
            control_queue=Queue(),
            scheduler=scheduler_name,
            logger=logging,
            approach_module=method,
            burst_enabled=True,
            burst_config=_burst_config(),
            burst_task_ratio=50,
        )
        scheduler.generate_task_list()
        schedulers[method] = scheduler

    assert len({s.offered_task_stream_hash for s in schedulers.values()}) == 1
    assert len({len(s.offered_tasks_by_id) for s in schedulers.values()}) == 1
    assert schedulers["baseline"].burst_management_enabled is False
    assert schedulers["llf-dag"].burst_management_enabled is False
    assert schedulers["feedback-fine-grained"].burst_management_enabled is True


def test_management_disabled_never_drops() -> None:
    manager = BurstTaskManager(management_enabled=False)
    manager.health_monitor.queue_length = 100
    tasks = [{"TaskId": "task", "ReleaseTime": 0.0, "Deadline": 1.0}]

    remaining, dropped = manager.proactive_drop(tasks, current_time=0.0)

    assert remaining == tasks
    assert dropped == []
    assert manager.get_burst_statistics()["drop_records"] == []


def test_unreleased_work_is_not_counted_as_active_backlog(monkeypatch) -> None:
    monkeypatch.setattr(BurstTaskManager, "start_monitoring", lambda self: None)
    scheduler = TaskSchedule(
        _tasks(),
        handler_status=defaultdict(int),
        control_queue=Queue(),
        scheduler="edf",
        logger=logging,
        approach_module="feedback-fine-grained",
        burst_enabled=True,
        burst_config=_burst_config(),
        burst_task_ratio=100,
    )
    scheduler.generate_task_list()
    scheduler.TaskStartTime = 100.0
    scheduler.handler_status[5] = 0

    # At relative time zero only the first base release and its Burst clone are
    # eligible; future releases
    # must remain in the queue and cannot trip the queue threshold.
    monkeypatch.setattr("task_scheduler.time.time", lambda: 100.0)
    scheduler.distribute_tasks()

    assert scheduler.burst_manager.health_monitor.queue_length == 2
    assert scheduler.burst_manager.get_burst_statistics()[
        "dropped_tasks_count"
    ] == 0
