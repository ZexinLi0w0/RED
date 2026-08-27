from collections import defaultdict
from queue import Queue

import pytest

from task_generator import generate_tasks_from_dag
from task_scheduler import TaskSchedule, merge_tasks, tasks_merge_eligible


def _task(name: str, run_arg: int, deadline: float, merge_key: str) -> dict:
    return {
        "TaskId": name,
        "TaskPosition": name,
        "DagPeriod": 0,
        "HandlerId": 5,
        "ReleaseTime": 0.0,
        "Deadline": deadline,
        "Priority": 1,
        "Dependencies": [run_arg],
        "RunArgs": str([run_arg]),
        "IsNonPartitionable": False,
        "MergeKey": merge_key,
        "ConstituentTaskIds": [name],
    }


def test_merge_requires_the_same_structural_stage() -> None:
    first = _task("first", 1, 0.10, "dag=0/period=0/stage=0")
    second = _task("second", 2, 0.20, "dag=0/period=0/stage=1")
    assert not tasks_merge_eligible(first, second, release_time_skew_threshold_seconds=0.02)

    second["MergeKey"] = first["MergeKey"]
    assert tasks_merge_eligible(first, second, release_time_skew_threshold_seconds=0.02)

    second["IsNonPartitionable"] = True
    assert not tasks_merge_eligible(first, second, release_time_skew_threshold_seconds=0.02)


def test_merge_threshold_changes_execution_graph_for_fixed_release_skews() -> None:
    tasks = [
        {
            **_task(name, run_arg, 1.0, "same-stage"),
            "ReleaseTime": release,
        }
        for name, run_arg, release in (
            ("first", 1, 0.0),
            ("second", 3, 0.05),
            ("third", 4, 0.10),
        )
    ]

    execution_counts = []
    for threshold in (0.0, 0.05, 0.10):
        scheduler = TaskSchedule(
            tasks,
            handler_status=defaultdict(int),
            control_queue=Queue(),
            scheduler="edf",
            approach_module="fine-grained",
            release_time_skew_threshold_seconds=threshold,
        )
        scheduler.generate_task_list()
        execution_counts.append(scheduler.task_num)

    assert execution_counts == [3, 2, 1]


def test_merged_task_uses_the_earliest_deadline_and_preserves_constituents() -> None:
    first = _task("first", 1, 0.10, "same-stage")
    second = _task("second", 2, 0.20, "same-stage")

    merged = merge_tasks(first, second)

    assert merged["Deadline"] == pytest.approx(0.10)
    assert merged["RunArgs"] == "1,2"
    assert merged["Dependencies"] == [1, 2]
    assert merged["ConstituentTaskIds"] == ["first", "second"]


def test_merged_execution_reports_outcomes_for_the_original_population() -> None:
    dag = [[[
        {
            "TaskName": "first",
            "HandlerId": 5,
            "Priority": 1,
            "Dependencies": [],
            "RunArgs": [1],
            "WorstRunningTime": 100,
        },
        {
            "TaskName": "second",
            "HandlerId": 5,
            "Priority": 1,
            "Dependencies": [],
            "RunArgs": [2],
            "WorstRunningTime": 200,
        },
    ]]]
    tasks = generate_tasks_from_dag(
        dag,
        deadline_factor=1.0,
        arrival_scale=1.0,
        dag_repeated_times=1,
        seed=0,
    )
    scheduler = TaskSchedule(
        tasks,
        handler_status=defaultdict(int),
        control_queue=Queue(),
        scheduler="edf",
        approach_module="fine-grained",
    )
    scheduler.generate_task_list()

    assert scheduler.task_num == 1
    assert len(scheduler.task_statistics) == 2

    execution_task_id = scheduler.TaskQueue[0]["TaskId"]
    scheduler.finished_task(
        execution_task_id,
        output="failure",
        start_time=0.0,
        end_time=0.15,
    )

    outcomes = {
        task["taskid"]: task["res"]
        for task in scheduler.task_statistics.values()
    }
    assert sorted(outcomes.values()) == ["failure", "success"]
    assert scheduler.all_task_finished()


def test_feedback_updates_merged_constituents_without_ghost_statistics() -> None:
    dag = [[[
        {
            "TaskName": "first",
            "HandlerId": 5,
            "Priority": 1,
            "Dependencies": [],
            "RunArgs": [1],
            "WorstRunningTime": 100,
        },
        {
            "TaskName": "second",
            "HandlerId": 5,
            "Priority": 1,
            "Dependencies": [],
            "RunArgs": [2],
            "WorstRunningTime": 200,
        },
    ]]]
    tasks = generate_tasks_from_dag(
        dag,
        deadline_factor=1.0,
        arrival_scale=1.0,
        dag_repeated_times=1,
        seed=0,
    )
    scheduler = TaskSchedule(
        tasks,
        handler_status=defaultdict(int),
        control_queue=Queue(),
        scheduler="edf",
        approach_module="feedback-fine-grained",
    )
    scheduler.generate_task_list()

    offered_ids = {task["TaskId"] for task in tasks}
    execution_task = scheduler.TaskQueue[0]
    assert execution_task["TaskId"].startswith("merged_")
    assert set(scheduler.task_statistics) == offered_ids

    scheduler.feedback_adjust(end_time=-0.01)

    assert set(scheduler.task_statistics) == offered_ids
    assert {
        record["release_time"] for record in scheduler.task_statistics.values()
    } == {-0.01}
