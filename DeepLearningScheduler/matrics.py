"""Pure metric helpers used by the scheduler and analysis scripts.

All time values passed to this module must use the same unit. Runtime code uses
seconds; keeping the helpers unit-agnostic makes accidental conversions easier
to detect in their callers and tests.
"""

import math
from collections.abc import Iterable, Sequence


DEFAULT_QOE_LAMBDA = 0.05
EXECUTED_OUTCOMES = frozenset({"success", "failure"})
DEADLINE_MISS_OUTCOMES = frozenset({"failure", "skip", "burst_drop"})
KNOWN_OUTCOMES = EXECUTED_OUTCOMES | DEADLINE_MISS_OUTCOMES


def _validate_paired_samples(
    finished_times: Sequence[float], deadlines: Sequence[float]
) -> None:
    if len(finished_times) != len(deadlines):
        raise ValueError("finished_times and deadlines must have equal length")
    if not finished_times:
        raise ValueError("at least one finished-time/deadline pair is required")


def throughput_score(latencies, min_latency=5.5):
    """Return reference latency divided by mean observed latency."""
    if not latencies:
        raise ValueError("at least one latency sample is required")
    latency_avg = sum(latencies) / len(latencies)
    return min_latency / latency_avg


def deadline_hit_rate(finished_times, deadlines):
    """Return the fraction of samples that finish on or before their deadline."""
    _validate_paired_samples(finished_times, deadlines)
    hits = sum(
        finished_time <= deadline
        for finished_time, deadline in zip(finished_times, deadlines)
    )
    return hits / len(finished_times)


def RTscore(finished_times, deadlines):
    """Backward-compatible alias for the historical deadline-hit-rate metric."""
    return deadline_hit_rate(finished_times, deadlines)


def qoe_score(finished_times, deadlines, lambda_param=DEFAULT_QOE_LAMBDA):
    """Compute the existing QoE formula over paired completion/deadline values.

    The formula is intentionally unchanged. This function only makes the
    parameter effective and validates that callers supply paired samples.
    """
    _validate_paired_samples(finished_times, deadlines)
    if not math.isfinite(lambda_param) or lambda_param < 0:
        raise ValueError("lambda_param must be a finite non-negative number")

    scores = [
        1.0
        / (
            1.0
            + math.exp(lambda_param)
            * max(0.0, finished_time - deadline)
        )
        for finished_time, deadline in zip(finished_times, deadlines)
    ]
    return sum(scores) / len(scores)


def QoEScore(finished_times, deadlines, lambda_param=DEFAULT_QOE_LAMBDA):
    """Backward-compatible wrapper for :func:`qoe_score`."""
    score = qoe_score(finished_times, deadlines, lambda_param=lambda_param)
    print(
        "[DEBUG] QoE score calculation, finished_times: ",
        finished_times,
        "deadlines: ",
        deadlines,
        "lambda_param: ",
        lambda_param,
        "QoE Score: ",
        score,
    )
    return score


def deadline_miss_rate_from_outcomes(outcomes: Iterable[str]) -> float:
    """Return the miss fraction for the scheduler's terminal outcome taxonomy.

    ``failure`` means the task executed but completed after its deadline.
    ``skip`` and ``burst_drop`` mean no on-time result was produced, so both
    count as misses while remaining excluded from execution-latency averages.
    """
    outcomes = list(outcomes)
    if not outcomes:
        return 0.0

    unknown = sorted(set(outcomes) - KNOWN_OUTCOMES)
    if unknown:
        raise ValueError(f"unknown terminal task outcomes: {unknown}")

    return sum(outcome in DEADLINE_MISS_OUTCOMES for outcome in outcomes) / len(
        outcomes
    )


if __name__ == "__main__":
    assert math.isclose(throughput_score([1, 2, 3, 4]), 2.2)
    assert math.isclose(RTscore([3, 3, 4, 3, 3], [3, 3, 3, 3, 3]), 0.8)
    assert math.isclose(
        QoEScore([3, 3, 4, 3, 3], [3, 3, 3, 3, 3]),
        0.8 + 0.2 / (1 + math.exp(DEFAULT_QOE_LAMBDA)),
    )
    print("All tests passed!")
