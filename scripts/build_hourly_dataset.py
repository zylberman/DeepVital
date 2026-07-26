#!/usr/bin/env python3
"""Build the ICU-period-bounded hourly DeepVital dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deepvital.cohort.hourly_dataset import build_hourly_dataset  # noqa: E402


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-input", required=True, type=Path)
    parser.add_argument("--fhir-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--quality-report", required=True, type=Path)
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
    args = parser.parse_args()
    report = build_hourly_dataset(
        args.canonical_input,
        args.fhir_dir,
        args.output,
        args.quality_report,
        _load(args.aggregation_config),
        _load(args.missingness_config),
    )
    print(
        f"Hourly build complete: {report['counts'].get('hourly_rows', 0)} rows; "
        f"{report['entities']['icu_stays']} ICU stays."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
