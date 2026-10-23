"""Run the reviewer-requested target-sensitivity post-hoc analysis."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

from deepvital.phase3.implementation import (
    discrimination_delta,
    load_frozen_manifest,
    run_frozen_nested_cv,
    validate_frozen_config,
)
from deepvital.phase3.target_sensitivity import (
    summarize_target_sensitivity,
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
    ROOT / "reports/phase3_posthoc_target_sensitivity.json"
)
DEFAULT_SUMMARY_OUTPUT = (
    ROOT / "reports/phase3_posthoc_target_sensitivity_summary.csv"
)
DEFAULT_FOLD_OUTPUT = (
    ROOT / "reports/phase3_posthoc_target_sensitivity_folds.csv"
)


def parse_args() -> argparse.Namespace:
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
        "--summary-output",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
    )
    parser.add_argument(
        "--fold-output",
        type=Path,
        default=DEFAULT_FOLD_OUTPUT,
    )
    parser.add_argument(
        "--confirm-posthoc-analysis",
        action="store_true",
        help=(
            "Explicitly authorize reconstruction of internal OOF "
            "predictions and creation of aggregate post-hoc reports."
        ),
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read private modeling windows without printing row-level data."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_new_outputs(*paths: Path) -> None:
    """Refuse to overwrite an existing post-hoc analysis."""
    existing = [path for path in paths if path.exists()]
    if existing:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"Refusing to overwrite existing output files: {names}"
        )


def json_safe(value: Any) -> Any:
    """Replace non-finite values before strict JSON serialization."""
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
    """Write a new aggregate JSON report without overwriting."""
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


def metric_row(
    strategy: str,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Flatten one aggregate operating-point result."""
    return {
        "strategy": strategy,
        "target_sensitivity": 0.80,
        "threshold_policy": metrics["threshold_policy"],
        "sensitivity": metrics["sensitivity"],
        "specificity": metrics["specificity"],
        "ppv": metrics["ppv"],
        "npv": metrics["npv"],
        "f1": metrics["f1"],
        "tp": metrics["tp"],
        "fp": metrics["fp"],
        "tn": metrics["tn"],
        "fn": metrics["fn"],
    }


def write_summary_csv(
    path: Path,
    results: dict[str, Any],
) -> None:
    """Write one aggregate row per strategy."""
    rows = [
        metric_row(
            "18_predictor_logistic_candidate",
            results["candidate_metrics"],
        ),
        metric_row(
            "six_hour_mean_map_comparator",
            results["benchmark_metrics"],
        ),
    ]
    fieldnames = list(rows[0])

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_fold_csv(
    path: Path,
    folds: list[dict[str, Any]],
) -> None:
    """Write aggregate operating-point results for each outer fold."""
    fieldnames = [
        "outer_fold",
        "strategy",
        "patients",
        "windows",
        "positive_windows",
        "threshold",
        "sensitivity",
        "specificity",
        "ppv",
        "npv",
        "f1",
        "tp",
        "fp",
        "tn",
        "fn",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for fold in folds:
            for strategy, threshold_key, metrics_key in (
                (
                    "18_predictor_logistic_candidate",
                    "candidate_threshold",
                    "candidate_metrics",
                ),
                (
                    "six_hour_mean_map_comparator",
                    "benchmark_threshold",
                    "benchmark_metrics",
                ),
            ):
                metrics = fold[metrics_key]
                writer.writerow(
                    {
                        "outer_fold": fold["outer_fold"],
                        "strategy": strategy,
                        "patients": fold["patients"],
                        "windows": fold["windows"],
                        "positive_windows": fold[
                            "positive_windows"
                        ],
                        "threshold": fold[threshold_key],
                        "sensitivity": metrics["sensitivity"],
                        "specificity": metrics["specificity"],
                        "ppv": metrics["ppv"],
                        "npv": metrics["npv"],
                        "f1": metrics["f1"],
                        "tp": metrics["tp"],
                        "fp": metrics["fp"],
                        "tn": metrics["tn"],
                        "fn": metrics["fn"],
                    }
                )


def main() -> int:
    args = parse_args()

    if not args.confirm_posthoc_analysis:
        raise SystemExit(
            "Analysis not executed. Pass --confirm-posthoc-analysis "
            "only after code review and synthetic testing."
        )

    assert_new_outputs(
        args.json_output,
        args.summary_output,
        args.fold_output,
    )

    config = json.loads(
        args.config.read_text(encoding="utf-8")
    )
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
        raise ValueError(
            "Canonical eligible-window count mismatch"
        )

    patient_count = len(
        {str(row["subject_id"]) for row in rows}
    )
    if patient_count != expected_patients:
        raise ValueError(
            "Canonical eligible-patient count mismatch"
        )

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

    results = summarize_target_sensitivity(oof, manifest)

    report = {
        "analysis": {
            "name": (
                "target-sensitivity operating-point analysis"
            ),
            "role": (
                "reviewer-requested post-hoc internal validation"
            ),
            "validation_description": (
                "patient-grouped nested cross-validation "
                "internal validation"
            ),
            "prespecified_operating_point": True,
            "post_hoc_reporting": True,
            "confirmatory": False,
            "external_validation": False,
            "target_sensitivity": 0.80,
            "model_refitted": True,
            "primary_phase3_decision_changed": False,
            "interpretation": (
                "Thresholds were selected from inner out-of-fold "
                "predictions and evaluated only in the corresponding "
                "outer fold."
            ),
        },
        "input_validation": {
            "dataset_fingerprint": actual_fingerprint,
            "expected_dataset_fingerprint": (
                expected_fingerprint
            ),
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
            "matched_with_absolute_tolerance_1e_minus_12": (
                True
            ),
        },
        "results": results,
        "limitations": [
            (
                "This analysis uses the same internal development "
                "cohort as the primary Phase 3 analysis."
            ),
            (
                "The target sensitivity was applied during inner "
                "threshold selection; outer-fold sensitivity is not "
                "expected to equal exactly 0.80."
            ),
            (
                "Overlapping windows from the same patient remain "
                "correlated."
            ),
            (
                "This analysis is not external or confirmatory "
                "validation."
            ),
        ],
    }

    safe_report = json_safe(report)
    assert_public_metadata(safe_report)

    write_json(args.json_output, safe_report)
    write_summary_csv(args.summary_output, results)
    write_fold_csv(args.fold_output, results["folds"])

    print("Post-hoc target-sensitivity analysis completed.")
    print(f"Patients: {patient_count}")
    print(f"Windows: {len(rows)}")
    print(f"JSON report: {args.json_output}")
    print(f"Summary CSV: {args.summary_output}")
    print(f"Fold CSV: {args.fold_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
