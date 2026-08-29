#!/usr/bin/env python3
"""Build a scenario-specific EDF calibration grid from a checked-in spec."""

import argparse
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path


def _scaled_label(prefix, value):
    decimal_value = Decimal(str(value))
    scaled = decimal_value * 100
    if scaled != scaled.to_integral_value() or decimal_value <= 0:
        raise ValueError("grid values must be positive with at most two decimals")
    return f"{prefix}{int(scaled):03d}"


def _payload(value):
    return (json.dumps(value, indent=2, sort_keys=False) + "\n").encode("utf-8")


def _write_if_absent_or_equal(path, payload):
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to overwrite non-identical config: {path}")
        return
    path.write_bytes(payload)


def _replace_index(path, payload):
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_bytes(payload)
    os.replace(temporary_path, path)


def build_grid(spec_path, source_dir, output_dir):
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    device = spec["device"]
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = []

    for workload in spec["workloads"]:
        scenario = workload["scenario"]
        arrival_scale = float(workload["arrival_scale"])
        source_path = source_dir / f"{device}_loose_{scenario}.json"
        source_config = json.loads(source_path.read_text(encoding="utf-8"))

        for deadline_factor_value in workload["deadline_factors"]:
            deadline_factor = float(deadline_factor_value)
            profile = (
                "cal_"
                + _scaled_label("s", arrival_scale)
                + "_"
                + _scaled_label("a", deadline_factor)
            )
            generated = dict(source_config)
            generated["ArrivalScale"] = arrival_scale
            generated["DeadlineFactor"] = deadline_factor
            generated["Calibration"] = {
                "kind": "edf-only-scenario-specific-grid",
                "arrival_scale": arrival_scale,
                "deadline_factor": deadline_factor,
                "source_config": source_path.name,
                "spec": spec_path.name,
                "selection_targets": {"tight": 0.50, "loose": 0.10},
            }
            output_path = output_dir / f"{device}_{profile}_{scenario}.json"
            config_payload = _payload(generated)
            _write_if_absent_or_equal(output_path, config_payload)
            entries.append(
                {
                    "device": device,
                    "scenario": scenario,
                    "profile": profile,
                    "deadline_alpha": deadline_factor,
                    "arrival_scale": arrival_scale,
                    "source_config": source_path.name,
                    "config_path": output_path.name,
                    "config_sha256": hashlib.sha256(config_payload).hexdigest(),
                }
            )

    index = {
        "schema_version": 1,
        "selection_method": "EDF only; proposed-method results must remain hidden",
        "tight_target": {"center": 0.50, "preferred_interval": [0.30, 0.70]},
        "loose_target": {"center": 0.10, "preferred_interval": [0.05, 0.25]},
        "spec": spec_path.name,
        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "configs": entries,
    }
    _replace_index(output_dir / "calibration_index.json", _payload(index))
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    index = build_grid(
        args.spec.resolve(), args.source_dir.resolve(), args.output_dir.resolve()
    )
    print(f"Generated/verified {len(index['configs'])} calibration configs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
