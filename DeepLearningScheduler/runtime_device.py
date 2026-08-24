"""Explicit PyTorch runtime-device selection for reproducible experiments."""

import os


REQUESTED_DEVICE_ENV = "RED_TORCH_DEVICE"
RESOLVED_DEVICE_ENV = "RED_TORCH_DEVICE_RESOLVED"


def configure_torch_device(requested=None):
    """Resolve and record the accelerator used by handler subprocesses.

    ``auto`` prefers CUDA, then Apple MPS, then CPU. Explicit requests fail
    instead of silently falling back, so a run cannot claim an accelerator it
    did not actually use.
    """
    import torch

    requested = requested or os.environ.get(REQUESTED_DEVICE_ENV, "auto")
    requested = str(requested).strip().lower()
    if requested == "auto":
        if torch.cuda.is_available():
            resolved = "cuda:0"
        elif torch.backends.mps.is_available():
            resolved = "mps"
        else:
            resolved = "cpu"
    elif requested == "mps":
        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS was requested but is not available")
        resolved = "mps"
    elif requested in {"cuda", "cuda:0"}:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available")
        resolved = "cuda:0"
    elif requested == "cpu":
        resolved = "cpu"
    else:
        raise ValueError(
            "torch device must be one of: auto, cpu, mps, cuda, cuda:0"
        )

    os.environ[REQUESTED_DEVICE_ENV] = requested
    os.environ[RESOLVED_DEVICE_ENV] = resolved
    return torch.device(resolved)


def synchronize_torch_device(device):
    """Wait for asynchronous accelerator work before recording completion."""
    import torch

    device = torch.device(device)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elif device.type == "mps":
        torch.mps.synchronize()


def torch_runtime_info(requested=None):
    """Return JSON-safe runtime metadata after resolving the device."""
    import torch

    device = configure_torch_device(requested)
    return {
        "requested": os.environ[REQUESTED_DEVICE_ENV],
        "resolved": str(device),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "mps_built": torch.backends.mps.is_built(),
        "mps_available": torch.backends.mps.is_available(),
    }
