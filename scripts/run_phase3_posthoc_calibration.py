"""Generate aggregate post-hoc calibration results from Phase 3 OOF predictions."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

from deepvital.phase3.calibration_reporting import (
    render_calibration_svg,
    summarize_calibration,
)
from deepvital.phase3.implementation import (
    discrimination_delta,
    load_frozen_manifest,
    run_frozen_nested_cv,
    validate_frozen_config,
)
from deepvital.reproducibility.fingerprints import (
    assert_public_metadata,
    fingerprint_file,
)

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATASET = (
    ROOT / "data/processed/canonical_v1/modeling_windows.csv"
)
DEFAULT_CONFIG = ROOT / "configs/phase3_frozen.json"
DEFAULT_ORIGINAL_REPORT = (
    ROOT / "reports/phase3_incremental_value.json"
)
DEFAULT_JSON_OUTPUT = (
    ROOT / "reports/phase3_posthoc_calibration.json"
)
DEFAULT_CSV_OUTPUT = (
    ROOT / "reports/phase3_posthoc_calibration_bins.csv"
)
DEFAULT_FIGURE_OUTPUT = (
    ROOT / "reports/figures/phase3_posthoc_calibration.svg"
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--original-report",
        type=Path,
        default=DEFAULT_ORIGINAL_REPORT,
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=DEFAULT_CSV_OUTPUT,
    )
    parser.add_argument(
        "--figure-output",
        type=Path,
        default=DEFAULT_FIGURE_OUTPUT,
    )
    parser.add_argument(
        "--confirm-posthoc-analysis",
        action="store_true",
        help=(
            "Explicitly authorize reconstruction of internal OOF "
            "predictions and creation of aggregate calibration outputs."
        ),
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read private modeling windows without printing row-level data."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_new_outputs(*paths: Path) -> None:
    """Refuse to overwrite existing post-hoc outputs."""
    existing = [path for path in paths if path.exists()]
    if existing:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"Refusing to overwrite existing output files: {names}"
        )


def json_safe(value: Any) -> Any:
    """Replace non-finite numbers before strict JSON serialization."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {
            str(key): json_safe(child)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [json_safe(child) for child in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a new aggregate JSON report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        handle.write("\n")


def write_bins_csv(
    path: Path,
    calibration: dict[str, Any],
) -> None:
    """Write aggregate calibration-bin values for both variants."""
    fieldnames = [
        "probability_variant",
        "bin",
        "lower_bound",
        "upper_bound",
        "count",
        "mean_predicted",
        "observed_proportion",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for variant_name in ("before_platt", "after_platt"):
            points = calibration["variants"][variant_name]["points"]
            for point in points:
                writer.writerow(
                    {
                        "probability_variant": variant_name,
                        "bin": point["bin"],
                        "lower_bound": point["lower_bound"],
                        "upper_bound": point["upper_bound"],
                        "count": point["count"],
                        "mean_predicted": point["mean_predicted"],
                        "observed_proportion": point[
                            "observed_proportion"
                        ],
                    }
                )


def main() -> int:
    """Run the protected aggregate calibration analysis."""
    args = parse_args()

    if not args.confirm_posthoc_analysis:
        raise SystemExit(
            "Analysis not executed. Pass --confirm-posthoc-analysis "
            "only after code review and synthetic testing."
        )

    assert_new_outputs(
        args.json_output,
        args.csv_output,
        args.figure_output,
    )

    config = json.loads(args.config.read_text(encoding="utf-8"))
    validate_frozen_config(config)

    expected_fingerprint = config["canonical_cohort"][
        "expected_fingerprint"
    ]
    actual_fingerprint = fingerprint_file(args.dataset)

    if actual_fingerprint != expected_fingerprint:
        raise ValueError(
            "Canonical modeling dataset fingerprint mismatch"
        )

    manifest_path = ROOT / config["fold_manifest"]["path"]
    manifest = load_frozen_manifest(
        manifest_path,
        config["fold_manifest"]["expected_fingerprint"],
    )

    rows = read_rows(args.dataset)

    expected_windows = int(
        config["canonical_cohort"]["expected_windows"]
    )
    expected_patients = int(
        config["canonical_cohort"][
            "expected_patients_with_windows"
        ]
    )

    if len(rows) != expected_windows:
        raise ValueError("Canonical eligible-window count mismatch")

    patient_count = len(
        {str(row["subject_id"]) for row in rows}
    )
    if patient_count != expected_patients:
        raise ValueError("Canonical eligible-patient count mismatch")

    oof = run_frozen_nested_cv(rows, manifest)

    original_report = json.loads(
        args.original_report.read_text(encoding="utf-8")
    )
    expected_delta = float(
        original_report["primary"]["observed_difference"]
    )
    reproduced = discrimination_delta(
        oof.labels,
        oof.raw_candidate,
        oof.benchmark,
    )
    reproduced_delta = reproduced["delta_auprc"]

    if not math.isclose(
        reproduced_delta,
        expected_delta,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RuntimeError(
            "Reconstructed primary delta AUPRC does not match "
            "the existing aggregate Phase 3 result"
        )

    calibration = summarize_calibration(
        oof.labels,
        oof.raw_candidate,
        oof.calibrated_candidate,
        bins=10,
    )

    report = {
        "analysis": {
            "name": "candidate calibration analysis",
            "role": (
                "reviewer-requested post-hoc internal reporting"
            ),
            "validation_description": (
                "patient-grouped nested cross-validation "
                "internal validation"
            ),
            "post_hoc_reporting": True,
            "confirmatory": False,
            "external_validation": False,
            "model_refitted": True,
            "primary_phase3_decision_changed": False,
            "interpretation": (
                "Calibration was estimated from outer-fold "
                "out-of-fold predictions. Each patient was absent "
                "from the model used to produce that patient's "
                "predictions."
            ),
        },
        "input_validation": {
            "dataset_fingerprint": actual_fingerprint,
            "expected_dataset_fingerprint": expected_fingerprint,
            "fold_manifest_fingerprint": config[
                "fold_manifest"
            ]["expected_fingerprint"],
            "number_of_patients": patient_count,
            "number_of_windows": len(rows),
        },
        "original_primary_reproduction": {
            "expected_delta_auprc": expected_delta,
            "reproduced_delta_auprc": reproduced_delta,
            "absolute_difference": abs(
                expected_delta - reproduced_delta
            ),
            "matched_with_absolute_tolerance_1e_minus_12": True,
        },
        "calibration": calibration,
        "limitations": [
            (
                "This post-hoc analysis uses the same internal "
                "development cohort as the primary Phase 3 analysis."
            ),
            (
                "The 8,970 overlapping prediction windows arise "
                "from only 92 patients and are not independent "
                "observations."
            ),
            (
                "The calibration curves are descriptive internal "
                "out-of-fold estimates, not independent confirmation."
            ),
        ],
    }

    safe_report = json_safe(report)
    assert_public_metadata(safe_report)

    render_calibration_svg(
        calibration,
        args.figure_output,
    )
    write_json(args.json_output, safe_report)
    write_bins_csv(args.csv_output, calibration)

    print("Post-hoc calibration reporting completed.")
    print(f"Patients: {patient_count}")
    print(f"Windows: {len(rows)}")
    print(f"JSON report: {args.json_output}")
    print(f"Calibration-bin CSV: {args.csv_output}")
    print(f"Calibration figure: {args.figure_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
