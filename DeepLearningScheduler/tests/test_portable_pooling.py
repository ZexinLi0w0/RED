import torch

from SIMO.backbone.MLP import _adaptive_avg_pool2d_exact  # noqa: E402


def test_portable_pooling_matches_native_nondivisible_bins() -> None:
    values = torch.arange(2 * 3 * 28 * 28, dtype=torch.float32).reshape(
        2, 3, 28, 28
    )

    expected = torch.nn.functional.adaptive_avg_pool2d(values, (6, 6))
    actual = _adaptive_avg_pool2d_exact(values, (6, 6))

    assert torch.allclose(actual, expected)
