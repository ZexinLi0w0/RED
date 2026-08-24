"""Pure metric helpers used by the scheduler and analysis scripts.

All time values passed to this module must use the same unit. Runtime code uses
seconds; keeping the helpers unit-agnostic makes accidental conversions easier
to detect in their callers and tests.
"""

import math
from collections.abc import Iterable, Sequence


DEFAULT_QOE_LAMBDA = 0.05
DEFAULT_XRBENCH_RT_K = 15.0
EXECUTED_OUTCOMES = frozenset({"success", "failure", "execution_error"})
VALID_OUTPUT_OUTCOMES = frozenset({"success", "failure"})
DEADLINE_MISS_OUTCOMES = frozenset(
    {"failure", "skip", "burst_drop", "execution_error"}
)
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


def xrbench_realtime_score(inference_latency, time_window, k=DEFAULT_XRBENCH_RT_K):
    """Return XRBench's sigmoid real-time utility for one inference.

    Both latency and the request-to-deadline time window are in seconds, so
    ``k`` is expressed in inverse seconds. The score is 0.5 exactly at the
    deadline, approaches one for increasingly early completion, and approaches
    zero as lateness grows.
    """
    values = (inference_latency, time_window, k)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("latency, time_window, and k must be finite")
    if inference_latency < 0 or time_window <= 0 or k < 0:
        raise ValueError(
            "latency must be non-negative, time_window positive, and k "
            "non-negative"
        )
    exponent = k * (inference_latency - time_window)
    if exponent >= 0:
        inverse = math.exp(-min(exponent, 709.0))
        return inverse / (1.0 + inverse)
    return 1.0 / (1.0 + math.exp(exponent))


def timeliness_qoe_score(task_records, k=DEFAULT_XRBENCH_RT_K):
    """Aggregate XRBench timing utility over the offered-node population.

    Valid inference outputs receive the per-inference real-time score. Skips,
    proactive drops, and execution errors receive zero, which is equivalent to
    combining XRBench's processed-frame ratio with its mean RT score. This
    makes the denominator identical across methods.
    """
    records = list(task_records)
    if not records:
        return 0.0
    scores = []
    for record in records:
        outcome = record["res"]
        if outcome not in KNOWN_OUTCOMES:
            raise ValueError(f"unknown terminal task outcome: {outcome}")
        if outcome not in VALID_OUTPUT_OUTCOMES:
            scores.append(0.0)
            continue
        release_time = float(record["release_time"])
        deadline = float(record["deadline"])
        end_time = float(record["end_time"])
        scores.append(
            xrbench_realtime_score(
                end_time - release_time,
                deadline - release_time,
                k=k,
            )
        )
    return sum(scores) / len(scores)


def deadline_miss_rate_from_outcomes(outcomes: Iterable[str]) -> float:
    """Return the miss fraction for the scheduler's terminal outcome taxonomy.

    ``failure`` means the task executed but completed after its deadline.
    ``execution_error`` means execution completed without a valid inference
    output. ``skip`` and ``burst_drop`` mean the task was not executed. Every
    case without a valid on-time output counts as a miss.
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
