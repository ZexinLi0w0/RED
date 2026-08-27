import hashlib
import json

from experiments.burst_study import (
    DEFAULT_BASE_TASK_CONFIG,
    DEFAULT_SEEDS,
    _seeds_for_repetitions,
    generate_study_plan,
    summarize_study,
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
    ] == [80, 92, 104, 112, 144]
    assert [
        condition["expected_workload"]["added_dag_release_count"]
        for condition in plan["conditions"]
    ] == [0, 3, 6, 8, 16]


def test_repetition_count_generates_deterministic_seeds() -> None:
    assert _seeds_for_repetitions(1) == (101,)
    assert _seeds_for_repetitions(3) == (101, 202, 303)


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
