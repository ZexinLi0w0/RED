#!/usr/bin/env python3
"""Freeze Tight/Loose JSON files from a ready EDF-only selection report."""

import argparse
import hashlib
import json
from pathlib import Path


def _payload(value):
    return (json.dumps(value, indent=2, sort_keys=False) + "\n").encode("utf-8")


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def _write_if_absent_or_equal(path, payload):
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to overwrite frozen config: {path}")
        return
    path.write_bytes(payload)


def freeze_configs(report_path, calibration_dir, output_dir):
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not report.get("ready_to_freeze"):
        raise ValueError("calibration report is not ready_to_freeze")
    output_dir.mkdir(parents=True, exist_ok=True)
    frozen_entries = []

    for selection in report["selections"]:
        for selected_as in ("tight", "loose"):
            selected_point = selection[selected_as]
            source_path = calibration_dir / selected_point["config_path"]
            source_payload = source_path.read_bytes()
            if _sha256(source_payload) != selected_point["config_sha256"]:
                raise ValueError(f"calibration config hash mismatch: {source_path}")
            config = json.loads(source_payload)
            config["CalibrationSelection"] = {
                "selected_as": selected_as,
                "source_profile": selected_point["profile"],
                "deadline_alpha": selected_point["deadline_alpha"],
                "edf_mean_deadline_missing_rate": selected_point[
                    "mean_deadline_missing_rate"
                ],
                "edf_repetitions": selected_point["repetitions"],
                "edf_seeds": selected_point["seeds"],
                "selection_report": report_path.name,
            }
            output_name = (
                f"{selection['device']}_{selected_as}_{selection['scenario']}.json"
            )
            output_path = output_dir / output_name
            frozen_payload = _payload(config)
            _write_if_absent_or_equal(output_path, frozen_payload)
            frozen_entries.append(
                {
                    "device": selection["device"],
                    "scenario": selection["scenario"],
                    "profile": selected_as,
                    "source_profile": selected_point["profile"],
                    "source_config_sha256": selected_point["config_sha256"],
                    "config_path": output_name,
                    "config_sha256": _sha256(frozen_payload),
                }
            )

    frozen_index = {
        "schema_version": 1,
        "selection_report": report_path.name,
        "selection_source": report["selection_source"],
        "code_commits": report["code_commits"],
        "configs": frozen_entries,
    }
    _write_if_absent_or_equal(
        output_dir / "frozen_index.json", _payload(frozen_index)
    )
    return frozen_index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--calibration-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    frozen_index = freeze_configs(
        args.report.resolve(),
        args.calibration_dir.resolve(),
        args.output_dir.resolve(),
    )
    print(f"Frozen/verified {len(frozen_index['configs'])} configs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
