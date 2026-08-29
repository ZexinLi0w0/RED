#!/usr/bin/env python3
"""Build a predeclared arrival-scale/deadline-factor exploration grid."""

import argparse
import hashlib
import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path


DEFAULT_ARRIVAL_SCALES = "1.25,1.5,1.75,2.0"
DEFAULT_DEADLINE_FACTORS = "1.2,2.0"
DEFAULT_SCENARIOS = "urban_navigation,emergency_obstacle_avoidance"


def _parse_positive_decimals(raw_value):
    values = []
    try:
        for value in raw_value.split(","):
            parsed = Decimal(value.strip())
            if parsed <= 0:
                raise argparse.ArgumentTypeError("grid values must be positive")
            values.append(parsed)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("grid values must be decimal numbers") from exc
    if not values or len(set(values)) != len(values):
        raise argparse.ArgumentTypeError("grid values must be non-empty and unique")
    return values


def _label(prefix, value):
    scaled = value * 100
    if scaled != scaled.to_integral_value():
        raise ValueError("grid labels require values with at most two decimals")
    return f"{prefix}{int(scaled):03d}"


def _payload(value):
    return (json.dumps(value, indent=2, sort_keys=False) + "\n").encode("utf-8")


def _write_if_absent_or_equal(path, payload):
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(
                f"refusing to replace non-identical generated config: {path}"
            )
        return
    path.write_bytes(payload)


def _replace_index(path, payload):
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_bytes(payload)
    os.replace(temporary_path, path)


def build_grid(
    source_dir,
    output_dir,
    arrival_scales,
    deadline_factors,
    scenarios=None,
):
    selected_scenarios = set(scenarios or [])
    source_paths = sorted(source_dir.glob("*_loose_*.json"))
    if selected_scenarios:
        source_paths = [
            path
            for path in source_paths
            if path.name.split("_loose_", 1)[1].removesuffix(".json")
            in selected_scenarios
        ]
    if not source_paths:
        raise FileNotFoundError(f"no selected *_loose_*.json files found in {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for source_path in source_paths:
        device, scenario_with_suffix = source_path.name.split("_loose_", 1)
        scenario = scenario_with_suffix.removesuffix(".json")
        source_config = json.loads(source_path.read_text(encoding="utf-8"))
        for arrival_scale in arrival_scales:
            for deadline_factor in deadline_factors:
                profile = (
                    "load_"
                    + _label("s", arrival_scale)
                    + "_"
                    + _label("a", deadline_factor)
                )
                generated = dict(source_config)
                generated["ArrivalScale"] = float(arrival_scale)
                generated["DeadlineFactor"] = float(deadline_factor)
                generated["Calibration"] = {
                    "kind": "edf-only-arrival-deadline-exploration",
                    "arrival_scale": float(arrival_scale),
                    "deadline_factor": float(deadline_factor),
                    "source_config": source_path.name,
                }
                output_path = output_dir / f"{device}_{profile}_{scenario}.json"
                config_payload = _payload(generated)
                _write_if_absent_or_equal(output_path, config_payload)
                entries.append(
                    {
                        "device": device,
                        "scenario": scenario,
                        "profile": profile,
                        "arrival_scale": float(arrival_scale),
                        "deadline_factor": float(deadline_factor),
                        "source_config": source_path.name,
                        "config_path": output_path.name,
                        "config_sha256": hashlib.sha256(config_payload).hexdigest(),
                    }
                )

    index = {
        "schema_version": 1,
        "selection_method": "EDF only; proposed-method results must remain hidden",
        "purpose": "separate offered-load saturation from deadline tightness",
        "configs": entries,
    }
    _replace_index(output_dir / "load_exploration_index.json", _payload(index))
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--arrival-scales",
        type=_parse_positive_decimals,
        default=_parse_positive_decimals(DEFAULT_ARRIVAL_SCALES),
    )
    parser.add_argument(
        "--deadline-factors",
        type=_parse_positive_decimals,
        default=_parse_positive_decimals(DEFAULT_DEADLINE_FACTORS),
    )
    parser.add_argument("--scenarios", default=DEFAULT_SCENARIOS)
    args = parser.parse_args()
    index = build_grid(
        args.source_dir.resolve(),
        args.output_dir.resolve(),
        args.arrival_scales,
        args.deadline_factors,
        [value.strip() for value in args.scenarios.split(",") if value.strip()],
    )
    print(f"Generated/verified {len(index['configs'])} load-exploration configs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
