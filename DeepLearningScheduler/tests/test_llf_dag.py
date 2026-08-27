from task_generator import generate_tasks_from_dag
from task_scheduler import (
    TaskSchedule,
    remaining_critical_path_costs,
)


def _node(name, output, worst_ms, dependencies):
    return {
        "TaskName": name,
        "HandlerId": 5,
        "Priority": 1,
        "Dependencies": dependencies,
        "RunArgs": [output],
        "WorstRunningTime": worst_ms,
    }


def test_remaining_critical_path_uses_latest_predecessor_stage() -> None:
    dag = [[
        _node("a", 1, 100, []),
        _node("b", 2, 200, [1]),
        _node("c", 3, 300, [2]),
    ]]
    tasks = generate_tasks_from_dag(
        dag,
        deadline_factor=10.0,
        arrival_scale=1.0,
        dag_repeated_times=1,
    )

    costs = remaining_critical_path_costs(tasks)
    by_name = {
        task["TaskId"].split("_[")[0]: costs[task["TaskId"]]
        for task in tasks
    }
    assert by_name == {"a": 0.6, "b": 0.5, "c": 0.3}


def test_llf_orders_by_laxity_then_uses_deterministic_ties() -> None:
    first = {
        "TaskId": "later-deadline-long-path",
        "Deadline": 1.0,
        "ReleaseTime": 0.0,
        "RemainingCriticalPathCost": 0.8,
    }
    second = {
        "TaskId": "earlier-deadline-short-path",
        "Deadline": 0.5,
        "ReleaseTime": 0.0,
        "RemainingCriticalPathCost": 0.1,
    }
    scheduler = TaskSchedule([first, second], scheduler="llf_dag")
    scheduler.TaskQueue = [second, first]

    scheduler.llf_dag(now_relative=0.0)

    assert [task["TaskId"] for task in scheduler.TaskQueue] == [
        "later-deadline-long-path",
        "earlier-deadline-short-path",
    ]
