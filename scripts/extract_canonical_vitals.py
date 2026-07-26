#!/usr/bin/env python3
"""Extract local canonical ICU vital observations from FHIR NDJSON gzip files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deepvital.fhir.extraction import (  # noqa: E402
    extract_rows,
    load_yaml_compatible_json,
    write_output,
    write_quality_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fhir-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--quality-report", required=True, type=Path)
    parser.add_argument("--format", required=True, choices=("parquet", "csv"))
    parser.add_argument(
        "--vital-config",
        type=Path,
        default=PROJECT_ROOT / "configs/fhir_vital_signs.yaml",
    )
    parser.add_argument(
        "--unit-config",
        type=Path,
        default=PROJECT_ROOT / "configs/unit_conversions.yaml",
    )
    args = parser.parse_args()
    vital_config = load_yaml_compatible_json(args.vital_config)
    unit_config = load_yaml_compatible_json(args.unit_config)
    rows, quality = extract_rows(args.fhir_dir, vital_config, unit_config)
    _, output_format = write_output(args.output, rows, args.format)
    write_quality_report(args.quality_report, quality, output_format)
    print(
        f"Canonical extraction complete: {quality['canonical_observations']} rows; "
        f"{quality['observations_rejected']} aggregate rejection events; "
        f"output format: {output_format}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
