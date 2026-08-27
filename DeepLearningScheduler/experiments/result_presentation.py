"""Select and format paper-facing experimental results.

Raw artifacts retain their full precision.  Paper tables and figures use one
complete representative run per experiment group and truncate its values to
three decimal places without rounding.
"""

import hashlib
import math
import random


PAPER_DECIMAL_DIGITS = 3
REPRESENTATIVE_METRIC = "end_to_end_latency_seconds"


def truncate_value(value, digits=PAPER_DECIMAL_DIGITS):
    """Truncate a finite experimental value without rounding."""
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("paper-facing experimental values must be finite")
    factor = 10**digits
    return math.trunc(value * factor) / factor


def format_truncated(value, digits=PAPER_DECIMAL_DIGITS):
    """Format a value after decimal truncation."""
    return f"{truncate_value(value, digits):.{digits}f}"


def _stable_random(group_key):
    material = "|".join(map(str, group_key)).encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return random.Random(seed)


def select_representative(
    records,
    group_key,
    metric=REPRESENTATIVE_METRIC,
):
    """Select one median run while preserving its complete metric tuple.

    Odd-sized groups select the exact median.  Even-sized groups randomly
    select one of the two central runs.  The random choice is seeded from the
    group identity so it is reproducible and auditable.  No metrics are ever
    averaged across runs.
    """
    records = list(records)
    if not records:
        raise ValueError("cannot select a representative from an empty group")
    ordered = sorted(
        records,
        key=lambda record: (
            float(record[metric]),
            int(record.get("seed", 0)),
            str(record.get("run_id", "")),
        ),
    )
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return _stable_random(group_key).choice(
        (ordered[midpoint - 1], ordered[midpoint])
    )
