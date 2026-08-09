"""Generate the three frozen private Phase 3 sensitivity inputs without modeling."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from deepvital.cohort.hourly_dataset import build_hourly_dataset
from deepvital.phase3.generation import (
    build_phase3_sensitivity_windows,
    filter_bp_source_rows,
    read_canonical_rows,
    write_canonical_rows_exclusively,
)
from deepvital.reproducibility.fingerprints import fingerprint_file

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-input", type=Path, required=True)
    parser.add_argument("--canonical-hourly-input", type=Path, required=True)
    parser.add_argument("--fhir-dir", type=Path, required=True)
    parser.add_argument("--future-map-output", type=Path, required=True)
    parser.add_argument("--bp-invasive-preferred-output", type=Path, required=True)
    parser.add_argument("--bp-non-invasive-only-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configs = ROOT / "configs"
    build_phase3_sensitivity_windows(
        args.canonical_hourly_input,
        args.future_map_output,
        include_incomplete_future_map=True,
        config_root=configs,
    )
    canonical_rows = read_canonical_rows(args.canonical_input)
    aggregation = __import__("json").loads(
        (configs / "hourly_aggregation.yaml").read_text()
    )
    missingness = __import__("json").loads((configs / "missingness.yaml").read_text())
    with tempfile.TemporaryDirectory(prefix="deepvital-phase3-") as directory:
        temporary_root = Path(directory)
        for alternative, output in (
            ("invasive_preferred", args.bp_invasive_preferred_output),
            ("non_invasive_only", args.bp_non_invasive_only_output),
        ):
            canonical_variant = temporary_root / f"{alternative}_canonical.csv"
            hourly_variant = temporary_root / f"{alternative}_hourly.csv"
            quality_path = temporary_root / f"{alternative}_quality.json"
            selected = filter_bp_source_rows(canonical_rows, alternative)
            write_canonical_rows_exclusively(canonical_variant, selected)
            build_hourly_dataset(
                canonical_variant,
                args.fhir_dir,
                hourly_variant,
                quality_path,
                aggregation,
                missingness,
            )
            build_phase3_sensitivity_windows(
                hourly_variant,
                output,
                include_incomplete_future_map=False,
                config_root=configs,
            )
    print(
        {
            "future_map_sensitivity": fingerprint_file(args.future_map_output),
            "bp_invasive_preferred": fingerprint_file(
                args.bp_invasive_preferred_output
            ),
            "bp_non_invasive_only": fingerprint_file(
                args.bp_non_invasive_only_output
            ),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
