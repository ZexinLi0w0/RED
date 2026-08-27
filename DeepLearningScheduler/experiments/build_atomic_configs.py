#!/usr/bin/env python3
"""Derive immutable atomic-node ratio configs from one frozen workload."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_atomic(path, value):
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    with open(temporary_path, "w", encoding="utf-8") as output_file:
        json.dump(value, output_file, indent=2, sort_keys=False)
        output_file.write("\n")
    os.replace(temporary_path, path)


def build_atomic_configs(
    source_config, output_dir, device, scenario, ratios=(0, 50, 100)
):
    source_config = Path(source_config).resolve()
    output_dir = Path(output_dir).resolve()
    source = json.loads(source_config.read_text(encoding="utf-8"))
    source_sha256 = _sha256(source_config)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for ratio in ratios:
        if isinstance(ratio, bool) or not isinstance(ratio, int):
            raise ValueError("atomic ratios must be integers")
        if ratio < 0 or ratio > 100:
            raise ValueError("atomic ratios must be between 0 and 100")
        config = dict(source)
        config["NonPartitionablePercentage"] = ratio
        config["AtomicExperiment"] = {
            "source_config": source_config.name,
            "source_config_sha256": source_sha256,
            "selection_rule": (
                "frozen tight config whose EDF-only calibration DMR is "
                "closest to 0.50"
            ),
            "semantics": (
                "marked offered scheduling nodes cannot participate in "
                "MIMONet-aware merge; no intra-kernel partitioning"
            ),
            "ratio_percent": ratio,
            "position_selection": (
                "stable SHA-256 rank of seed and structural TaskPosition; "
                "ratio sets are nested"
            ),
        }
        output_path = output_dir / f"{device}_atomic{ratio}_{scenario}.json"
        if output_path.exists():
            raise FileExistsError(f"refusing to overwrite {output_path}")
        _write_json_atomic(output_path, config)
        outputs.append(
            {
                "ratio_percent": ratio,
                "config_path": output_path.name,
                "config_sha256": _sha256(output_path),
            }
        )

    index = {
        "schema_version": 1,
        "device": device,
        "scenario": scenario,
        "source_config": source_config.name,
        "source_config_sha256": source_sha256,
        "ratios_percent": list(ratios),
        "configs": outputs,
    }
    index_path = output_dir / "atomic_config_index.json"
    if index_path.exists():
        raise FileExistsError(f"refusing to overwrite {index_path}")
    _write_json_atomic(index_path, index)
    return index_path, outputs


def _parse_ratios(value):
    try:
        return tuple(int(item.strip()) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "ratios must be comma-separated integers"
        ) from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--ratios", type=_parse_ratios, default=(0, 50, 100))
    args = parser.parse_args()
    index_path, outputs = build_atomic_configs(
        args.source_config,
        args.output_dir,
        args.device,
        args.scenario,
        ratios=args.ratios,
    )
    print(f"Wrote {len(outputs)} atomic configs and {index_path}")


if __name__ == "__main__":
    main()
