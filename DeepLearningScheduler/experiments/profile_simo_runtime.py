#!/usr/bin/env python3
"""Profile synchronized SIMONet inference costs on an explicit device."""

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import platform
import socket
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "SIMO"))

from runtime_device import (  # noqa: E402
    synchronize_torch_device,
    torch_runtime_info,
)


DECODER_CASES = {
    "lane_detection": [1],
    "control_autopilot": [2],
    "segmentation": [3],
    "object_detection": [4],
    "lane_and_object": [1, 4],
    "segmentation_and_object": [3, 4],
    "all_decoders": [1, 2, 3, 4],
}


def _percentile(samples, percentile):
    if not samples:
        raise ValueError("cannot summarize an empty sample population")
    ordered = sorted(float(sample) for sample in samples)
    rank = (len(ordered) - 1) * percentile / 100.0
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize_samples(samples_ms, margin_fraction):
    if margin_fraction < 0:
        raise ValueError("margin_fraction must be non-negative")
    observed_max_ms = max(samples_ms)
    return {
        "sample_count": len(samples_ms),
        "mean_ms": sum(samples_ms) / len(samples_ms),
        "p50_ms": _percentile(samples_ms, 50),
        "p95_ms": _percentile(samples_ms, 95),
        "p99_ms": _percentile(samples_ms, 99),
        "observed_max_ms": observed_max_ms,
        "bound_margin_fraction": margin_fraction,
        "profiled_execution_bound_ms": observed_max_ms
        * (1.0 + margin_fraction),
    }


def _git_output(*arguments):
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _write_new_json(path, value):
    if path.exists():
        raise FileExistsError(f"refusing to overwrite profile: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_bytes(payload)
    os.replace(temporary_path, path)
    return hashlib.sha256(payload).hexdigest()


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--torch-device", default="auto")
    parser.add_argument("--power-mode", required=True)
    parser.add_argument("--warmup-iterations", type=int, default=20)
    parser.add_argument("--sample-iterations", type=int, default=200)
    parser.add_argument("--bound-margin", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=0)
    return parser


def main():
    args = _build_parser().parse_args()
    if args.warmup_iterations <= 0 or args.sample_iterations <= 0:
        raise ValueError("warmup and sample iterations must be positive")
    if args.bound_margin < 0:
        raise ValueError("bound margin must be non-negative")

    runtime = torch_runtime_info(args.torch_device)
    import torch
    from SIMONet import SIMONet

    device = torch.device(runtime["resolved"])
    torch.manual_seed(args.seed)
    input_tensor = torch.randn(1, 3, 224, 224, device=device)
    model = SIMONet().to(device).eval()

    with torch.inference_mode():
        for decoder_list in DECODER_CASES.values():
            for _ in range(args.warmup_iterations):
                model(input_tensor, decoder_list)
                synchronize_torch_device(device)

        samples_by_case = defaultdict(list)
        for _ in range(args.sample_iterations):
            for case_name, decoder_list in DECODER_CASES.items():
                started_ns = time.perf_counter_ns()
                output = model(input_tensor, decoder_list)
                synchronize_torch_device(device)
                elapsed_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
                if output != "Success":
                    raise RuntimeError(
                        f"invalid model output for {case_name}: {output!r}"
                    )
                samples_by_case[case_name].append(elapsed_ms)

    cases = {}
    for case_name, decoder_list in DECODER_CASES.items():
        samples = samples_by_case[case_name]
        cases[case_name] = {
            "decoder_list": decoder_list,
            **summarize_samples(samples, args.bound_margin),
            "samples_ms": samples,
        }

    profile = {
        "schema_version": 1,
        "measurement_scope": (
            "SIMONet encoder plus selected decoder(s), inference mode, "
            "including explicit accelerator completion synchronization"
        ),
        "bound_policy": "observed maximum times (1 + fixed margin)",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "power_mode": args.power_mode,
        "torch_runtime": runtime,
        "git_commit": _git_output("rev-parse", "HEAD"),
        "git_status_porcelain": _git_output("status", "--porcelain", "--", "."),
        "seed": args.seed,
        "warmup_iterations_per_case": args.warmup_iterations,
        "sample_iterations_per_case": args.sample_iterations,
        "bound_margin_fraction": args.bound_margin,
        "cases": cases,
    }
    output_path = args.output.resolve()
    sha256 = _write_new_json(output_path, profile)
    print(json.dumps({"output": str(output_path), "sha256": sha256}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
