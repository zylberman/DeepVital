"""Run the reviewer-requested post-hoc recent-hypotension sensitivity analysis."""

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
from deepvital.phase3.incident_sensitivity import (
    cohort_accounting,
    cohort_masks,
    evaluate_oof_subset,
    summarize_recent_hypotension,
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
DEFAULT_ORIGINAL_REPORT = ROOT / "reports/phase3_incremental_value.json"
DEFAULT_JSON_OUTPUT = (
    ROOT / "reports/phase3_posthoc_recent_hypotension_sensitivity.json"
)
DEFAULT_CSV_OUTPUT = (
    ROOT / "reports/phase3_posthoc_recent_hypotension_sensitivity.csv"
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
        "--csv-output",
        type=Path,
        default=DEFAULT_CSV_OUTPUT,
    )
    parser.add_argument(
        "--confirm-posthoc-analysis",
        action="store_true",
        help=(
            "Explicitly authorize reconstruction of internal OOF predictions "
            "and creation of new aggregate reports."
        ),
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read the private canonical windows without printing row-level values."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def json_safe(value: Any) -> Any:
    """Replace non-finite floats before strict JSON serialization."""
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


def assert_new_outputs(*paths: Path) -> None:
    """Prevent accidental overwriting of an existing analysis."""
    existing = [path for path in paths if path.exists()]
    if existing:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"Refusing to overwrite existing output files: {names}"
        )


def add_positive_proportions(
    accounting: dict[str, Any],
) -> dict[str, Any]:
    """Add proportions using positive windows as the denominator."""
    output = dict(accounting)
    denominator = int(output["positive_windows"])

    count_keys = (
        "positive_windows_with_current_observed_hypotension",
        "positive_windows_with_any_observed_hypotension_t_minus_5_to_t",
        "positive_windows_without_any_observed_map_t_minus_5_to_t",
        "positive_windows_with_complete_recent_map_assessment",
    )

    for key in count_keys:
        proportion_key = key.replace(
            "positive_windows_",
            "proportion_of_positive_windows_",
        )
        output[proportion_key] = (
            int(output[key]) / denominator
            if denominator
            else math.nan
        )

    return output


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a new aggregate JSON report without overwriting."""
    with path.open("x", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        handle.write("\n")


def csv_value(value: Any) -> Any:
    """Represent unavailable numeric results as empty CSV fields."""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def write_csv(
    path: Path,
    cohort_results: dict[str, dict[str, Any]],
) -> None:
    """Write one aggregate row per sensitivity cohort."""
    fieldnames = [
        "cohort",
        "number_of_patients",
        "number_of_windows",
        "positive_windows",
        "prevalence",
        "candidate_auprc",
        "benchmark_auprc",
        "delta_auprc",
        "delta_auprc_ci_95_lower",
        "delta_auprc_ci_95_upper",
        "candidate_auroc",
        "benchmark_auroc",
        "delta_auroc",
        "delta_auroc_ci_95_lower",
        "delta_auroc_ci_95_upper",
        "candidate_sensitivity",
        "candidate_specificity",
        "benchmark_sensitivity",
        "benchmark_specificity",
    ]

    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for cohort, result in cohort_results.items():
            candidate = result["candidate_metrics"]
            benchmark = result["benchmark_metrics"]
            delta_auprc = result["paired_differences"]["delta_auprc"]
            delta_auroc = result["paired_differences"]["delta_auroc"]

            row = {
                "cohort": cohort,
                "number_of_patients": result["number_of_patients"],
                "number_of_windows": result["number_of_windows"],
                "positive_windows": result["positive_windows"],
                "prevalence": result["prevalence"],
                "candidate_auprc": candidate["auprc"],
                "benchmark_auprc": benchmark["auprc"],
                "delta_auprc": delta_auprc["observed_difference"],
                "delta_auprc_ci_95_lower": delta_auprc["ci_95_lower"],
                "delta_auprc_ci_95_upper": delta_auprc["ci_95_upper"],
                "candidate_auroc": candidate["auroc"],
                "benchmark_auroc": benchmark["auroc"],
                "delta_auroc": delta_auroc["observed_difference"],
                "delta_auroc_ci_95_lower": delta_auroc["ci_95_lower"],
                "delta_auroc_ci_95_upper": delta_auroc["ci_95_upper"],
                "candidate_sensitivity": candidate["sensitivity"],
                "candidate_specificity": candidate["specificity"],
                "benchmark_sensitivity": benchmark["sensitivity"],
                "benchmark_specificity": benchmark["specificity"],
            }
            writer.writerow(
                {
                    key: csv_value(value)
                    for key, value in row.items()
                }
            )


def main() -> int:
    args = parse_args()

    if not args.confirm_posthoc_analysis:
        raise SystemExit(
            "Analysis not executed. Pass --confirm-posthoc-analysis "
            "only after code review and synthetic testing."
        )

    assert_new_outputs(args.json_output, args.csv_output)

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
        config["canonical_cohort"]["expected_patients_with_windows"]
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

    masks = {
        "all_eligible_windows": [True] * len(rows),
        **cohort_masks(rows),
    }

    accounting = cohort_accounting(rows, masks)
    bootstrap_replicates = int(
        config["validation"]["bootstrap_replicates"]
    )
    seed = int(config["fold_manifest"]["seed"])

    cohort_results = {
        name: evaluate_oof_subset(
            oof,
            mask,
            bootstrap_replicates=bootstrap_replicates,
            seed=seed,
        )
        for name, mask in masks.items()
    }

    report = {
        "analysis": {
            "name": (
                "recent observed hypotension post-hoc "
                "sensitivity analysis"
            ),
            "role": (
                "reviewer-requested internal sensitivity analysis"
            ),
            "validation_description": (
                "patient-grouped nested cross-validation "
                "internal validation"
            ),
            "prespecified": False,
            "confirmatory": False,
            "map_threshold_mm_hg": 65.0,
            "recent_period": "t-5 through t inclusive",
            "hypotension_rule": (
                "at least one observed hourly MAP strictly below "
                "65 mmHg"
            ),
            "forward_filled_values_used_as_hypotension_evidence": False,
            "model_reselected_for_subgroups": False,
            "threshold_reselected_for_subgroups": False,
            "interpretation": (
                "Post-hoc assessment of persistence versus forecasting; "
                "not independent validation."
            ),
        },
        "input_validation": {
            "dataset_fingerprint": actual_fingerprint,
            "expected_dataset_fingerprint": expected_fingerprint,
            "number_of_patients": patient_count,
            "number_of_windows": len(rows),
            "fold_manifest_fingerprint": config[
                "fold_manifest"
            ]["expected_fingerprint"],
        },
        "original_primary_reproduction": {
            "expected_delta_auprc": expected_delta,
            "reproduced_delta_auprc": reproduced_delta,
            "absolute_difference": abs(
                expected_delta - reproduced_delta
            ),
            "matched_with_absolute_tolerance_1e_minus_12": True,
        },
        "reviewer_requested_positive_window_accounting": (
            add_positive_proportions(
                summarize_recent_hypotension(rows)
            )
        ),
        "cohort_accounting": accounting,
        "cohort_results": cohort_results,
        "limitations": [
            (
                "The analysis was requested after inspection of the "
                "primary Phase 3 results."
            ),
            (
                "Overlapping windows from the same patient remain "
                "correlated."
            ),
            (
                "Patient-cluster bootstrap preserves patient-level "
                "clustering but does not create independent events."
            ),
            (
                "The no-observed-recent-hypotension cohort may contain "
                "hours with missing MAP."
            ),
            (
                "The complete-recent-normotension cohort is stricter "
                "but may select more intensively monitored periods."
            ),
        ],
    }

    safe_report = json_safe(report)
    assert_public_metadata(safe_report)

    write_json(args.json_output, safe_report)
    write_csv(args.csv_output, cohort_results)

    print("Post-hoc internal sensitivity analysis completed.")
    print(f"Patients: {patient_count}")
    print(f"Windows: {len(rows)}")
    print(f"JSON report: {args.json_output}")
    print(f"CSV report: {args.csv_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
