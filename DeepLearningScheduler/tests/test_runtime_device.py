import os
import sys
from types import SimpleNamespace

import pytest

from runtime_device import (
    REQUESTED_DEVICE_ENV,
    RESOLVED_DEVICE_ENV,
    configure_torch_device,
    synchronize_torch_device,
)


class _FakeDevice:
    def __init__(self, value):
        self.type = str(value).split(":", 1)[0]
        self.value = str(value)

    def __str__(self):
        return self.value


def _fake_torch(*, cuda=False, mps=False):
    calls = []
    return SimpleNamespace(
        device=_FakeDevice,
        cuda=SimpleNamespace(
            is_available=lambda: cuda,
            synchronize=lambda device: calls.append(("cuda", str(device))),
        ),
        backends=SimpleNamespace(
            mps=SimpleNamespace(
                is_available=lambda: mps,
                is_built=lambda: mps,
            )
        ),
        mps=SimpleNamespace(synchronize=lambda: calls.append(("mps", None))),
        calls=calls,
    )


def test_auto_device_prefers_mps_when_cuda_is_unavailable(
    monkeypatch,
) -> None:
    fake_torch = _fake_torch(mps=True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.delenv(REQUESTED_DEVICE_ENV, raising=False)
    monkeypatch.delenv(RESOLVED_DEVICE_ENV, raising=False)

    assert str(configure_torch_device("auto")) == "mps"
    assert os.environ[RESOLVED_DEVICE_ENV] == "mps"


def test_explicit_unavailable_accelerator_fails(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "torch", _fake_torch())
    with pytest.raises(RuntimeError, match="MPS was requested"):
        configure_torch_device("mps")


def test_accelerator_synchronization_is_explicit(monkeypatch) -> None:
    fake_torch = _fake_torch(mps=True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    synchronize_torch_device("mps")

    assert fake_torch.calls == [("mps", None)]
