import pytest

from experiments.profile_simo_runtime import _percentile, summarize_samples


def test_profile_summary_uses_observed_max_plus_fixed_margin() -> None:
    summary = summarize_samples([1.0, 2.0, 3.0, 4.0], 0.10)

    assert summary["p50_ms"] == pytest.approx(2.5)
    assert summary["p95_ms"] == pytest.approx(3.85)
    assert summary["observed_max_ms"] == 4.0
    assert summary["profiled_execution_bound_ms"] == pytest.approx(4.4)


def test_percentile_rejects_empty_population() -> None:
    with pytest.raises(ValueError, match="empty"):
        _percentile([], 50)
