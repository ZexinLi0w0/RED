import math

import pytest

from matrics import QoEScore, deadline_miss_rate_from_outcomes
from visual_scripts.visual_task import statistics_compution


def test_qoe_honors_the_requested_lambda() -> None:
    assert QoEScore([2.0], [1.0], lambda_param=0.0) == pytest.approx(0.5)
    assert QoEScore([2.0], [1.0], lambda_param=1.0) == pytest.approx(
        1.0 / (1.0 + math.e)
    )


@pytest.mark.parametrize(
    ("finished_times", "deadlines"),
    [([], []), ([1.0], []), ([1.0, 2.0], [1.0])],
)
def test_qoe_rejects_empty_or_unpaired_samples(finished_times, deadlines) -> None:
    with pytest.raises(ValueError):
        QoEScore(finished_times, deadlines)


def test_deadline_miss_rate_counts_every_unfinished_outcome() -> None:
    outcomes = ["success", "failure", "skip", "burst_drop"]
    assert deadline_miss_rate_from_outcomes(outcomes) == pytest.approx(0.75)


def test_statistics_excludes_nonexecuted_work_from_latency(tmp_path) -> None:
    task_statistics = {
        "success": {
            "taskid": "success",
            "res": "success",
            "start_time": 1.0,
            "end_time": 1.1,
            "is_non_partitionable": False,
        },
        "failure": {
            "taskid": "failure",
            "res": "failure",
            "start_time": 2.0,
            "end_time": 2.2,
            "is_non_partitionable": True,
        },
        "skip": {
            "taskid": "skip",
            "res": "skip",
            "start_time": 3.0,
            "end_time": 3.0,
            "is_non_partitionable": False,
        },
        "burst_drop": {
            "taskid": "burst_drop",
            "res": "burst_drop",
            "start_time": 4.0,
            "end_time": 4.0,
            "is_non_partitionable": True,
        },
    }

    missing_rate, missing_info, average_latency, finished_info, _ = (
        statistics_compution(
            task_statistics,
            task_config_path=str(tmp_path / "missing.json"),
            now_time=10.0,
            task_start_time=0.0,
        )
    )

    assert missing_rate == pytest.approx(0.75)
    assert set(missing_info) == {"failure", "skip", "burst_drop"}
    assert average_latency == pytest.approx(0.15)
    assert set(finished_info) == {"success", "failure"}
