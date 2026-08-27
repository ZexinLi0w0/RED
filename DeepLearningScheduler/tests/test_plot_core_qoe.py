import json

import pytest

from experiments.plot_core_qoe import METHODS, PROFILES, SCENARIOS, load_qoe_data


def _summary_rows():
    rows = []
    for profile_index, (profile, _) in enumerate(PROFILES):
        for scenario_index, (scenario, _) in enumerate(SCENARIOS):
            for method_index, (method, _, _, _) in enumerate(METHODS):
                mean = 0.5 + 0.01 * (profile_index + scenario_index + method_index)
                rows.append(
                    {
                        "profile": profile,
                        "scenario": scenario,
                        "method": method,
                        "n": 5,
                        "metrics": {
                            "qoe_score": {"mean": mean, "sample_sd": 0.01}
                        },
                    }
                )
    return rows


def test_load_qoe_data_preserves_declared_plot_order(tmp_path):
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps({"aggregates": _summary_rows()}))

    values = load_qoe_data(summary_path)

    assert values["tight"]["baseline"]["means"] == pytest.approx(
        [0.5, 0.51, 0.52]
    )
    assert values["loose"]["feedback-fine-grained"]["means"] == pytest.approx(
        [0.55, 0.56, 0.57]
    )


def test_load_qoe_data_rejects_an_incomplete_matrix(tmp_path):
    rows = _summary_rows()
    rows.pop()
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps({"aggregates": rows}))

    with pytest.raises(ValueError, match="missing aggregate row"):
        load_qoe_data(summary_path)
