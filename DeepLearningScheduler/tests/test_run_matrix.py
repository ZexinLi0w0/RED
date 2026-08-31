from experiments.run_matrix import (
    DEFAULT_REPETITIONS,
    _execution_cells,
    _resolve_seeds,
    _seeds_for_repetitions,
)


def test_matrix_defaults_to_one_repetition() -> None:
    assert DEFAULT_REPETITIONS == 1
    assert _seeds_for_repetitions(DEFAULT_REPETITIONS) == [101]
    assert _resolve_seeds(DEFAULT_REPETITIONS, None) == [101]


def test_matrix_repetitions_generate_deterministic_seeds() -> None:
    assert _seeds_for_repetitions(3) == [101, 202, 303]


def test_explicit_seeds_override_repetition_count() -> None:
    assert _resolve_seeds(9, [7, 11]) == [7, 11]


def test_execution_order_shuffle_is_fixed_and_cell_complete() -> None:
    ordered = _execution_cells(["tight", "loose"], ["night"], [101, 202], ["edf"])
    shuffled = _execution_cells(
        ["tight", "loose"], ["night"], [101, 202], ["edf"], order_seed=1729
    )

    assert shuffled == _execution_cells(
        ["tight", "loose"], ["night"], [101, 202], ["edf"], order_seed=1729
    )
    assert shuffled != ordered
    assert sorted(shuffled) == sorted(ordered)
