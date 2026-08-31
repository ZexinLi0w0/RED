import argparse
import hashlib
import json

import pytest

from experiments.burst_study import (
    DEFAULT_BASE_TASK_CONFIG,
    DEFAULT_SEEDS,
    _validate_summary,
    _csv_values,
    _seeds_for_repetitions,
    generate_study_plan,
    summarize_study,
)


NANO1_BASE_TASK_CONFIG = (
    DEFAULT_BASE_TASK_CONFIG.parent / "nano1_cuda_proactive_drop_v3.json"
)


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def test_default_plan_runs_each_cell_once(tmp_path) -> None:
    plan = generate_study_plan(DEFAULT_BASE_TASK_CONFIG, tmp_path / "study")

    assert plan["planned_run_count"] == 15
    assert plan["repetitions_per_cell"] == 1
    assert plan["seeds"] == list(DEFAULT_SEEDS) == [101]
    assert [
        condition["expected_offered_task_count"]
        for condition in plan["conditions"]
    ] == [84, 96, 108, 114, 150]
    assert [
        condition["expected_workload"]["added_dag_release_count"]
        for condition in plan["conditions"]
    ] == [0, 2, 4, 5, 11]
    assert plan["deadline_factor"] == 6.0
    assert plan["arrival_scale"] == 4.0
    assert plan["timing_source"] == {
        "deadline_factor": "task-config",
        "arrival_scale": "task-config",
    }
    assert plan["gpu_threshold"] == 100.0
    assert plan["queue_threshold"] == 10
    assert plan["persistence_window"] == 3
    assert plan["require_proactive_drop_for_meris_burst"] is True
    assert plan["require_no_proactive_drop_for_meris_control"] is True


def test_repetition_count_generates_deterministic_seeds() -> None:
    assert _seeds_for_repetitions(1) == (101,)
    assert _seeds_for_repetitions(3) == (101, 202, 303)


def test_calibration_subset_parser_rejects_duplicates() -> None:
    assert _csv_values("control-000,sustained-100") == (
        "control-000",
        "sustained-100",
    )
    with pytest.raises(argparse.ArgumentTypeError, match="duplicates"):
        _csv_values("control-000,control-000")


def test_plan_records_non_mac_runtime_and_device(tmp_path) -> None:
    plan = generate_study_plan(
        DEFAULT_BASE_TASK_CONFIG,
        tmp_path / "study",
        device="nano1",
        platform_label="Jetson Orin Nano",
        power_mode="15W",
        torch_device="cuda",
        transient_duration_seconds=0.7,
        require_proactive_drop_for_meris_burst=False,
        require_no_proactive_drop_for_meris_control=False,
    )

    assert plan["device"] == "nano1"
    assert plan["platform_label"] == "Jetson Orin Nano"
    assert plan["power_mode"] == "15W"
    assert plan["torch_device"] == "cuda"
    assert plan["conditions"][1]["transient_duration_seconds"] == 0.7
    assert plan["require_proactive_drop_for_meris_burst"] is False
    assert plan["require_no_proactive_drop_for_meris_control"] is False


def test_nano1_plan_uses_calibrated_queue_boundary(tmp_path) -> None:
    plan = generate_study_plan(
        NANO1_BASE_TASK_CONFIG,
        tmp_path / "nano1-study",
        burst_start_seconds=0.0,
        transient_duration_seconds=3.0,
        release_horizon_seconds=10.0,
        gpu_threshold=100.0,
        queue_threshold=15,
        persistence_window=1,
        device="nano1",
        platform_label="Jetson Orin Nano",
        power_mode="15W; jetson_clocks",
        torch_device="cuda",
        require_proactive_drop_for_meris_burst=False,
    )

    assert plan["deadline_factor"] == 5000.0
    assert plan["arrival_scale"] == 40.0
    assert plan["timing_source"] == {
        "deadline_factor": "task-config",
        "arrival_scale": "task-config",
    }
    assert plan["queue_threshold"] == 15
    assert plan["persistence_window"] == 1
    assert [
        condition["expected_offered_task_count"]
        for condition in plan["conditions"]
    ] == [16, 20, 24, 24, 32]
    assert [
        condition["expected_workload"]["added_dag_release_count"]
        for condition in plan["conditions"]
    ] == [0, 1, 2, 2, 4]
    assert plan["require_proactive_drop_for_meris_burst"] is False
    assert plan["require_no_proactive_drop_for_meris_control"] is True

    config = json.loads(NANO1_BASE_TASK_CONFIG.read_text(encoding="utf-8"))
    running_times = {
        task["TaskName"]: task["RunningTime"]
        for task in config["dag_list"][0][0]
    }
    assert running_times == {
        "Nano1_Burst_Critical_LaneDetection": 44.382938,
        "Nano1_Burst_Critical_Control": 37.229989,
        "Nano1_Burst_Redundant_Segmentation": 40.925567,
        "Nano1_Burst_Redundant_ObjectDetection": 51.641363,
    }
    assert config["RuntimeProfile"]["sample_counts"] == {
        "lane_detection": 69,
        "control": 73,
        "segmentation": 48,
        "object_detection": 52,
    }
    drop_thresholds = [
        task["DropThreshold"] for task in config["dag_list"][0][0]
    ]
    assert sum(threshold > 0 for threshold in drop_thresholds) == 1
    assert config["BurstStudyWorkload"][
        "expected_meris_sustained_100_drop_count"
    ] == 8
    assert config["BurstStudyWorkload"][
        "target_sustained_100_deadline_missing_rate"
    ] == [0.2, 0.3]


def test_meris_burst_validation_requires_activation_and_drop_records() -> None:
    expected_workload = {"added_dag_release_count": 5}
    manifest = {
        "run_id": "red-burst",
        "method": "feedback-fine-grained",
        "offered_task_count": 114,
        "offered_task_stream_sha256": "same-stream",
        "expected_workload": expected_workload,
        "require_proactive_drop": True,
    }
    summary = {
        "run_id": "red-burst",
        "method": "feedback-fine-grained",
        "offered_task_count": 114,
        "offered_task_stream_sha256": "same-stream",
        "end_to_end_latency_seconds": 1.9,
        "deadline_missing_rate": 0.5,
        "qoe_score": 0.97,
        "outcome_counts": {},
        "burst_statistics": {
            "management_enabled": True,
            "workload": expected_workload,
            "overload_activation_count": 0,
            "dropped_tasks_count": 0,
            "drop_records": [],
        },
    }

    problems = _validate_summary(manifest, summary)

    assert "MERIS Burst run did not activate ProactiveDrop" in problems
    assert "MERIS Burst run did not record proactive drops" in problems

    summary["burst_statistics"].update(
        {
            "overload_activation_count": 3,
            "dropped_tasks_count": 10,
            "drop_records": [{"task_id": "redundant"}],
        }
    )
    assert _validate_summary(manifest, summary) == []


def test_meris_control_validation_rejects_proactive_drop() -> None:
    expected_workload = {"added_dag_release_count": 0}
    manifest = {
        "run_id": "red-control",
        "method": "feedback-fine-grained",
        "offered_task_count": 84,
        "offered_task_stream_sha256": "control-stream",
        "expected_workload": expected_workload,
        "require_no_proactive_drop": True,
    }
    summary = {
        "run_id": "red-control",
        "method": "feedback-fine-grained",
        "offered_task_count": 84,
        "offered_task_stream_sha256": "control-stream",
        "end_to_end_latency_seconds": 1.9,
        "deadline_missing_rate": 0.3,
        "qoe_score": 0.98,
        "outcome_counts": {},
        "burst_statistics": {
            "management_enabled": True,
            "workload": expected_workload,
            "overload_activation_count": 1,
            "dropped_tasks_count": 1,
            "drop_records": [{"task_id": "unexpected"}],
        },
    }

    assert _validate_summary(manifest, summary) == [
        "MERIS zero-Burst control unexpectedly activated ProactiveDrop"
    ]


def test_summarizer_selects_complete_runs_and_reuses_control(tmp_path) -> None:
    output_root = tmp_path / "study"
    plan = generate_study_plan(
        DEFAULT_BASE_TASK_CONFIG,
        output_root,
        seeds=(1, 2, 3, 4, 5),
    )
    for condition in plan["conditions"]:
        for method_index, method in enumerate(plan["methods"]):
            for seed in plan["seeds"]:
                run_id = f"{condition['slug']}-{method}-{seed}"
                run_dir = output_root / "runs" / run_id
                latency = float(seed + method_index)
                summary = {
                    "run_id": run_id,
                    "method": method,
                    "offered_task_count": condition[
                        "expected_offered_task_count"
                    ],
                    "offered_task_stream_sha256": f"{condition['slug']}-stream",
                    "end_to_end_latency_seconds": latency,
                    "deadline_missing_rate": seed / 10,
                    "qoe_score": 1 - seed / 20,
                    "outcome_counts": {"success": condition["expected_offered_task_count"]},
                    "burst_statistics": {
                        "management_enabled": method == "feedback-fine-grained",
                        "workload": condition["expected_workload"],
                        "drop_records": [],
                    },
                }
                summary_path = run_dir / "summary.json"
                _write_json(summary_path, summary)
                summary_hash = hashlib.sha256(summary_path.read_bytes()).hexdigest()
                _write_json(
                    run_dir / "manifest.json",
                    {
                        "run_id": run_id,
                        "status": "complete",
                        "condition_slug": condition["slug"],
                        "method": method,
                        "seed": seed,
                        "offered_task_count": condition[
                            "expected_offered_task_count"
                        ],
                        "offered_task_stream_sha256": f"{condition['slug']}-stream",
                        "expected_workload": condition["expected_workload"],
                        "summary_sha256": summary_hash,
                    },
                )

    report = summarize_study(output_root)

    assert len(report["table_rows"]) == 6
    transient_control = report["table_rows"][0]
    sustained_control = report["table_rows"][3]
    assert transient_control["EDF"] == sustained_control["EDF"]
    assert transient_control["EDF"]["end_to_end_latency_seconds"] == "3.000"
    assert report["drop_composition"]["transient"][
        "dropped_offered_nodes"
    ] == 0
    assert report["representative_runs"][0]["burst_statistics"] == {
        "overload_activation_count": 0,
        "maximum_consecutive_overload_ticks": 0,
        "dropped_tasks_count": 0,
    }
