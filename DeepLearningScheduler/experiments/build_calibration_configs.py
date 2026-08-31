#!/usr/bin/env python3
"""Build the predeclared EDF-only deadline-factor calibration grid."""

import argparse
import hashlib
import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path


DEFAULT_ALPHAS = "0.8,1.0,1.2,1.4,1.6,2.0"


def _parse_alphas(raw_value):
    alphas = []
    try:
        for value in raw_value.split(","):
            alpha = Decimal(value.strip())
            if alpha <= 0:
                raise argparse.ArgumentTypeError("alphas must be positive")
            alphas.append(alpha)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("alphas must be decimal numbers") from exc
    if not alphas or len(set(alphas)) != len(alphas):
        raise argparse.ArgumentTypeError("alphas must be non-empty and unique")
    return alphas


def _alpha_label(alpha):
    scaled = alpha * 100
    if scaled != scaled.to_integral_value():
        raise ValueError("alpha labels require values with at most two decimals")
    return f"cal_a{int(scaled):03d}"


def _sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def _json_payload(value):
    return (json.dumps(value, indent=2, sort_keys=False) + "\n").encode("utf-8")


def _write_if_absent_or_equal(path, payload):
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(
                f"refusing to replace non-identical generated config: {path}"
            )
        return
    path.write_bytes(payload)


def _replace_generated_index(path, payload):
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_bytes(payload)
    os.replace(temporary_path, path)


def build_grid(source_dir, output_dir, alphas, devices=None, scenarios=None):
    source_paths = sorted(source_dir.glob("*_loose_*.json"))
    if devices:
        devices = set(devices)
        source_paths = [
            path
            for path in source_paths
            if path.name.split("_loose_", 1)[0] in devices
        ]
    if scenarios:
        scenarios = set(scenarios)
        source_paths = [
            path
            for path in source_paths
            if path.name.split("_loose_", 1)[1].removesuffix(".json")
            in scenarios
        ]
    if not source_paths:
        raise FileNotFoundError(f"no *_loose_*.json files found in {source_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    index_entries = []

    for source_path in source_paths:
        prefix, scenario_with_suffix = source_path.name.split("_loose_", 1)
        scenario = scenario_with_suffix.removesuffix(".json")
        source_config = json.loads(source_path.read_text(encoding="utf-8"))
        if "DeadlineFactor" not in source_config or "ArrivalScale" not in source_config:
            raise ValueError(f"source config is not on the explicit schema: {source_path}")

        for alpha in alphas:
            profile = _alpha_label(alpha)
            generated = dict(source_config)
            generated["DeadlineFactor"] = float(alpha)
            generated["Calibration"] = {
                "kind": "edf-only-deadline-factor-grid",
                "deadline_alpha": float(alpha),
                "source_config": source_path.name,
                "selection_targets": {
                    "tight": 0.50,
                    "loose": 0.10,
                },
            }
            output_path = output_dir / f"{prefix}_{profile}_{scenario}.json"
            payload = _json_payload(generated)
            _write_if_absent_or_equal(output_path, payload)
            index_entries.append(
                {
                    "device": prefix,
                    "scenario": scenario,
                    "profile": profile,
                    "deadline_alpha": float(alpha),
                    "arrival_scale": generated["ArrivalScale"],
                    "source_config": source_path.name,
                    "config_path": output_path.name,
                    "config_sha256": _sha256_bytes(payload),
                }
            )

    index = {
        "schema_version": 1,
        "selection_method": "EDF only; proposed-method results must remain hidden",
        "tight_target": {"center": 0.50, "preferred_interval": [0.30, 0.70]},
        "loose_target": {"center": 0.10, "preferred_interval": [0.05, 0.25]},
        "configs": index_entries,
    }
    index_path = output_dir / "calibration_index.json"
    _replace_generated_index(index_path, _json_payload(index))
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--alphas", type=_parse_alphas, default=_parse_alphas(DEFAULT_ALPHAS))
    parser.add_argument(
        "--devices",
        default="",
        help="optional comma-separated device prefixes (for example: mac)",
    )
    parser.add_argument(
        "--scenarios",
        default="",
        help="optional comma-separated scenario names",
    )
    args = parser.parse_args()
    index = build_grid(
        args.source_dir.resolve(),
        args.output_dir.resolve(),
        args.alphas,
        [value.strip() for value in args.devices.split(",") if value.strip()],
        [value.strip() for value in args.scenarios.split(",") if value.strip()],
    )
    print(f"Generated/verified {len(index['configs'])} calibration configs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
