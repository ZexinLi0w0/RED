from matrics import throughput_score


def test_metrics_module_is_importable() -> None:
    assert throughput_score([5.5], min_latency=5.5) == 1.0
