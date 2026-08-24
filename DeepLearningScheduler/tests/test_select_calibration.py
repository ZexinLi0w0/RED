from experiments.select_calibration import select_tight_loose


def _point(alpha, miss_rate):
    return {
        "deadline_alpha": alpha,
        "mean_deadline_missing_rate": miss_rate,
    }


def test_selection_uses_ordered_points_inside_predeclared_intervals() -> None:
    result = select_tight_loose(
        [
            _point(0.8, 0.90),
            _point(1.0, 0.55),
            _point(1.2, 0.32),
            _point(1.4, 0.20),
            _point(1.6, 0.11),
            _point(2.0, 0.01),
        ]
    )
    assert result["status"] == "ready"
    assert result["tight"]["deadline_alpha"] == 1.0
    assert result["loose"]["deadline_alpha"] == 1.6


def test_selection_requests_extension_when_targets_are_saturated() -> None:
    result = select_tight_loose(
        [_point(0.8, 1.0), _point(1.0, 0.95), _point(1.2, 0.90)]
    )
    assert result["status"] == "needs-grid-extension"
