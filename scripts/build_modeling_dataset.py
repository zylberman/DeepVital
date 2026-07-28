#!/usr/bin/env python3
"""Build labeled windows and deterministic patient-level splits."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deepvital.windows.builder import build_modeling_dataset


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hourly-input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--split-manifest", required=True, type=Path)
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument(
        "--aggregation-config",
        type=Path,
        default=PROJECT_ROOT / "configs/hourly_aggregation.yaml",
    )
    parser.add_argument(
        "--missingness-config",
        type=Path,
        default=PROJECT_ROOT / "configs/missingness.yaml",
    )
    parser.add_argument(
        "--windowing-config",
        type=Path,
        default=PROJECT_ROOT / "configs/windowing.yaml",
    )
    parser.add_argument(
        "--labeling-config",
        type=Path,
        default=PROJECT_ROOT / "configs/labeling.yaml",
    )
    parser.add_argument(
        "--splitting-config",
        type=Path,
        default=PROJECT_ROOT / "configs/splitting.yaml",
    )
    args = parser.parse_args()
    aggregation = _load(args.aggregation_config)
    result = build_modeling_dataset(
        args.hourly_input,
        args.output,
        args.split_manifest,
        args.report_dir,
        aggregation["variables"],
        _load(args.missingness_config),
        _load(args.windowing_config),
        _load(args.labeling_config),
        _load(args.splitting_config),
    )
    labels = result["label_distribution"]
    print(
        f"Modeling dataset complete: {labels['total']} windows; "
        f"{labels['positive']} positive, {labels['negative']} negative."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
