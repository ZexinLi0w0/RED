import json
import logging
from collections import defaultdict
from queue import Queue

from task_generator import generate_tasks_from_dag
from task_scheduler import TaskSchedule


def test_completed_run_writes_machine_readable_summary(tmp_path) -> None:
    dag = [[{
        "TaskName": "single",
        "HandlerId": 5,
        "Priority": 1,
        "Dependencies": [],
        "RunArgs": [1],
        "WorstRunningTime": 100,
    }]]
    config_path = tmp_path / "task.json"
    config_path.write_text(
        json.dumps(
            {
                "DeadlineFactor": 1.0,
                "ArrivalScale": 1.0,
                "DagRepeatedTimes": 1,
                "ParallelStagePolicy": "max",
                "QoELambda": 0.05,
                "dag_list": dag,
            }
        ),
        encoding="utf-8",
    )
    tasks = generate_tasks_from_dag(
        dag,
        deadline_factor=1.0,
        arrival_scale=1.0,
        dag_repeated_times=1,
        seed=7,
    )
    output_dir = tmp_path / "run"
    scheduler = TaskSchedule(
        tasks,
        handler_status=defaultdict(int),
        control_queue=Queue(),
        scheduler="edf",
        logger=logging,
        approach_module="baseline",
        task_config_path=str(config_path),
        output_dir=str(output_dir),
        run_id="test-run",
    )
    scheduler.generate_task_list()
    task_id = scheduler.TaskQueue[0]["TaskId"]
    scheduler.finished_task(task_id, "success", 0.0, 0.05)
    scheduler.after_finsihed_task_distribution()

    summary = json.loads((output_dir / "summary.json").read_text())
    assert summary["run_id"] == "test-run"
    assert summary["offered_task_count"] == 1
    assert summary["execution_task_count"] == 1
    assert summary["finished_execution_task_count"] == 1
    assert summary["outcome_counts"] == {"success": 1}
    assert summary["qoe_lambda"] == 0.05
    assert summary["qoe_time_unit"] == "seconds"
    assert summary["moving_average_reassignment"] == {
        "enabled": False,
        "window": 8,
        "event_count": 0,
        "events": [],
    }
    assert summary["atomic_node_statistics"]["atomic_offered_ratio"] == 0.0
    assert summary["atomic_node_statistics"]["atomic"][
        "offered_node_count"
    ] == 0
    assert summary["atomic_node_statistics"]["partitionable"][
        "offered_node_count"
    ] == 1
    assert "original QoEScore" in summary["qoe_score_definition"]
    assert len(summary["offered_task_stream_sha256"]) == 64
    assert (output_dir / "task_statistics.pkl").is_file()
    assert (output_dir / "end2end_time.txt").is_file()
