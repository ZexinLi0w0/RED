from experiments.result_presentation import (
    format_truncated,
    select_representative,
    truncate_value,
)


def test_paper_values_are_truncated_without_rounding():
    assert truncate_value(0.8867) == 0.886
    assert format_truncated(0.8867) == "0.886"
    assert format_truncated(0.0009) == "0.000"


def test_even_group_selects_one_complete_central_run_reproducibly():
    records = [
        {
            "run_id": f"run-{index}",
            "seed": index,
            "end_to_end_latency_seconds": latency,
            "deadline_missing_rate": index / 10,
            "qoe_score": 1 - index / 10,
        }
        for index, latency in enumerate((1.0, 2.0, 3.0, 4.0))
    ]

    first = select_representative(records, ("device", "scenario", "method"))
    second = select_representative(records, ("device", "scenario", "method"))

    assert first is second
    assert first["run_id"] in {"run-1", "run-2"}
    assert (first["deadline_missing_rate"], first["qoe_score"]) in {
        (0.1, 0.9),
        (0.2, 0.8),
    }
