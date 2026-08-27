import pytest
from queue import Queue

from deadline_reassignment import (
    MovingAverageCostEstimator,
    proportional_residual_deadlines,
)
from task_generator import timing_config_from_mapping
from task_scheduler import TaskSchedule


def _task(task_id, stage, estimate=1.0):
    return {
        "TaskId": task_id,
        "DagIndex": 0,
        "DagPeriod": 0,
        "StageIndex": stage,
        "HandlerId": 5,
        "RunArgs": "[1]",
        "EstimatedExecutionTime": estimate,
    }


def test_moving_average_uses_only_the_latest_configured_window():
    task = _task("node", 0, estimate=9.0)
    estimator = MovingAverageCostEstimator(window=2)

    assert estimator.estimate(task) == pytest.approx(9.0)
    estimator.observe(task, 1.0)
    estimator.observe(task, 3.0)
    estimator.observe(task, 5.0)

    assert estimator.observations(task) == [3.0, 5.0]
    assert estimator.estimate(task) == pytest.approx(4.0)


def test_residual_deadlines_follow_level_cost_proportions():
    first = _task("first", 1, estimate=1.0)
    parallel = _task("parallel", 1, estimate=3.0)
    final = _task("final", 2, estimate=2.0)
    estimator = MovingAverageCostEstimator(window=8)

    assignments = proportional_residual_deadlines(
        [first, parallel, final],
        now_seconds=2.0,
        absolute_end_to_end_deadline=8.0,
        cost_estimator=estimator.estimate,
    )

    assert assignments["first"] == pytest.approx(6.0)
    assert assignments["parallel"] == pytest.approx(6.0)
    assert assignments["final"] == pytest.approx(8.0)


def test_timing_config_exposes_moving_average_window():
    timing = timing_config_from_mapping({"MovingAverageWindow": 16})

    assert timing.moving_average_window == 16
    with pytest.raises(ValueError, match="MovingAverageWindow"):
        timing_config_from_mapping({"MovingAverageWindow": 0})


def test_feedback_path_records_and_applies_moving_average_reassignment():
    tasks = []
    for task_id, stage, release, deadline, estimate in (
        ("first", 0, 0.0, 1.0, 1.0),
        ("second", 1, 1.0, 4.0, 3.0),
    ):
        tasks.append(
            {
                "TaskId": task_id,
                "TaskPosition": f"dag=0/period=0/stage={stage}/branch=single",
                "MergeKey": f"dag=0/period=0/stage={stage}",
                "ConstituentTaskIds": [task_id],
                "DagIndex": 0,
                "DagPeriod": 0,
                "StageIndex": stage,
                "BranchIndex": None,
                "HandlerId": 5,
                "ReleaseTime": release,
                "Deadline": deadline,
                "Priority": 1,
                "Dependencies": [],
                "RunArgs": "[1]",
                "EstimatedExecutionTime": estimate,
                "IsNonPartitionable": False,
            }
        )

    scheduler = TaskSchedule(
        tasks,
        control_queue=Queue(),
        scheduler="edf",
        approach_module="feedback",
        moving_average_window=2,
    )
    scheduler.generate_task_list()
    completed = scheduler.TaskQueue.pop(0)

    scheduler.feedback_adjust(
        end_time=0.5,
        completed_taskid=completed["TaskId"],
        start_time=0.1,
        outcome="success",
    )

    assert scheduler.TaskQueue[0]["ReleaseTime"] == pytest.approx(0.5)
    assert scheduler.TaskQueue[0]["Deadline"] == pytest.approx(4.0)
    assert scheduler.deadline_reassignment_trace[0]["window"] == 2
    assert scheduler.deadline_reassignment_trace[0][
        "observed_execution_seconds"
    ] == pytest.approx(0.4)
