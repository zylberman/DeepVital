"""Run reviewer-requested fitted single-predictor comparisons."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections.abc import Mapping, Sequence
from numbers import Integral, Real
from pathlib import Path
from typing import Any

from deepvital.evaluation.bootstrap import paired_patient_bootstrap
from deepvital.evaluation.metrics import (
    average_precision,
    evaluate_probabilities,
    roc_auc,
)
from deepvital.phase3.implementation import (
    discrimination_delta,
    load_frozen_manifest,
    run_frozen_nested_cv,
    validate_frozen_config,
)
from deepvital.phase3.posthoc_single_predictor import (
    ALLOWED_SINGLE_PREDICTORS,
    SinglePredictorOOFResult,
    run_single_predictor_nested_cv,
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
    ROOT / "reports/phase3_posthoc_single_predictor.json"
)
DEFAULT_SUMMARY_OUTPUT = (
    ROOT / "reports/phase3_posthoc_single_predictor_summary.csv"
)
DEFAULT_FOLD_OUTPUT = (
    ROOT / "reports/phase3_posthoc_single_predictor_fold_metrics.csv"
)

SUMMARY_FIELDS = [
    "strategy",
    "predictor_count",
    "score_variant",
    "score_semantics",
    "number_of_patients",
    "number_of_windows",
    "positive_windows",
    "prevalence",
    "auprc",
    "auroc",
    "brier_score",
    "log_loss",
    "mean_fold_auprc",
    "minimum_fold_auprc",
    "maximum_fold_auprc",
    "pooled_minus_mean_fold_auprc",
]

FOLD_FIELDS = [
    "strategy",
    "predictor_count",
    "score_variant",
    "outer_fold",
    "number_of_patients",
    "number_of_windows",
    "positive_windows",
    "prevalence",
    "auprc",
    "auroc",
    "brier_score",
    "log_loss",
    "selected_C",
    "calibration_method",
    "calibration_training_scope",
    "platt_intercept",
    "platt_slope",
    "patient_overlap",
]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments without running the analysis."""
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
            "Explicitly authorize model refitting on the internal "
            "development cohort and creation of new aggregate reports."
        ),
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read private rows without printing row-level information."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_new_outputs(*paths: Path) -> None:
    """Refuse to overwrite any existing analysis report."""
    existing = [path for path in paths if path.exists()]
    if existing:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"Refusing to overwrite existing output files: {names}"
        )


def json_safe(value: Any) -> Any:
    """Convert numeric values for strict JSON serialization."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, Mapping):
        return {
            str(key): json_safe(child)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [json_safe(child) for child in value]
    return value


def score_metrics(
    labels: Sequence[int],
    scores: Sequence[float],
    *,
    probability_output: bool,
) -> dict[str, float | None]:
    """Evaluate probability outputs or discrimination-only scores."""
    if probability_output:
        return evaluate_probabilities(labels, scores)

    return {
        "prevalence": sum(labels) / len(labels),
        "auprc": average_precision(labels, scores),
        "auroc": roc_auc(labels, scores),
        "brier_score": None,
        "log_loss": None,
    }


def fold_metric_rows(
    *,
    strategy: str,
    predictor_count: int,
    score_variant: str,
    labels: list[int],
    subjects: list[str],
    scores: list[float],
    manifest: Mapping[str, Any],
    probability_output: bool,
    fold_records: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Return aggregate discrimination results for each outer fold."""
    records_by_fold = {
        int(record["outer_fold"]): record
        for record in fold_records
    }
    assignments = manifest["patient_assignments"]
    rows: list[dict[str, Any]] = []

    for outer_fold in range(1, 6):
        indices = [
            index
            for index, subject in enumerate(subjects)
            if int(assignments[subject]["outer_fold"])
            == outer_fold
        ]
        fold_labels = [labels[index] for index in indices]
        fold_scores = [scores[index] for index in indices]
        metrics = score_metrics(
            fold_labels,
            fold_scores,
            probability_output=probability_output,
        )
        record = records_by_fold.get(outer_fold, {})

        rows.append(
            {
                "strategy": strategy,
                "predictor_count": predictor_count,
                "score_variant": score_variant,
                "outer_fold": outer_fold,
                "number_of_patients": len(
                    {subjects[index] for index in indices}
                ),
                "number_of_windows": len(indices),
                "positive_windows": sum(fold_labels),
                "prevalence": (
                    sum(fold_labels) / len(fold_labels)
                ),
                "auprc": metrics["auprc"],
                "auroc": metrics["auroc"],
                "brier_score": metrics.get("brier_score"),
                "log_loss": metrics.get("log_loss"),
                "selected_C": record.get("selected_C"),
                "calibration_method": (
                    "platt_logistic"
                    if score_variant
                    == "platt_calibrated_probability"
                    else None
                ),
                "calibration_training_scope": (
                    record.get("calibration_training_scope")
                    if score_variant
                    == "platt_calibrated_probability"
                    else None
                ),
                "platt_intercept": (
                    record.get("platt_intercept")
                    if score_variant
                    == "platt_calibrated_probability"
                    else None
                ),
                "platt_slope": (
                    record.get("platt_slope")
                    if score_variant
                    == "platt_calibrated_probability"
                    else None
                ),
                "patient_overlap": record.get(
                    "patient_overlap",
                    0,
                ),
            }
        )

    return rows


def summary_row(
    *,
    strategy: str,
    predictor_count: int,
    score_variant: str,
    score_semantics: str,
    labels: list[int],
    subjects: list[str],
    scores: list[float],
    probability_output: bool,
    fold_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize pooled OOF results and the fold distribution."""
    metrics = score_metrics(
        labels,
        scores,
        probability_output=probability_output,
    )
    auprcs = [
        float(row["auprc"])
        for row in fold_rows
        if row["strategy"] == strategy
        and row["score_variant"] == score_variant
    ]
    mean_fold_auprc = sum(auprcs) / len(auprcs)

    return {
        "strategy": strategy,
        "predictor_count": predictor_count,
        "score_variant": score_variant,
        "score_semantics": score_semantics,
        "number_of_patients": len(set(subjects)),
        "number_of_windows": len(labels),
        "positive_windows": sum(labels),
        "prevalence": sum(labels) / len(labels),
        "auprc": metrics["auprc"],
        "auroc": metrics["auroc"],
        "brier_score": metrics.get("brier_score"),
        "log_loss": metrics.get("log_loss"),
        "mean_fold_auprc": mean_fold_auprc,
        "minimum_fold_auprc": min(auprcs),
        "maximum_fold_auprc": max(auprcs),
        "pooled_minus_mean_fold_auprc": (
            float(metrics["auprc"]) - mean_fold_auprc
        ),
    }


def ensure_aligned(
    reference_labels: Sequence[int],
    reference_subjects: Sequence[str],
    result: SinglePredictorOOFResult,
) -> None:
    """Ensure every strategy evaluates the same ordered windows."""
    if list(result.labels) != list(reference_labels):
        raise AssertionError(
            "Single-predictor labels do not align with Phase 3"
        )
    if list(result.subjects) != list(reference_subjects):
        raise AssertionError(
            "Single-predictor patients do not align with Phase 3"
        )


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a new strict aggregate JSON report."""
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
    """Represent unavailable values as empty CSV fields."""
    if value is None:
        return ""
    if isinstance(value, Real):
        number = float(value)
        return number if math.isfinite(number) else ""
    return value


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: Sequence[Mapping[str, Any]],
) -> None:
    """Write a new aggregate CSV without overwriting."""
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: csv_value(row.get(field))
                    for field in fieldnames
                }
            )


def main() -> int:
    """Run the protected reviewer-requested analysis."""
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

    expected_fingerprint = config[
        "canonical_cohort"
    ]["expected_fingerprint"]
    actual_fingerprint = fingerprint_file(args.dataset)
    if actual_fingerprint != expected_fingerprint:
        raise ValueError(
            "Canonical modeling dataset fingerprint mismatch"
        )

    manifest = load_frozen_manifest(
        ROOT / config["fold_manifest"]["path"],
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

    primary = run_frozen_nested_cv(rows, manifest)
    original_report = json.loads(
        args.original_report.read_text(encoding="utf-8")
    )

    reproduced = discrimination_delta(
        primary.labels,
        primary.raw_candidate,
        primary.benchmark,
    )
    reproduced_candidate_auprc = average_precision(
        primary.labels,
        primary.raw_candidate,
    )
    reproduced_benchmark_auprc = average_precision(
        primary.labels,
        primary.benchmark,
    )

    expected_delta = float(
        original_report["primary"]["observed_difference"]
    )
    expected_candidate_auprc = float(
        original_report["raw_candidate_metrics"]["auprc"]
    )
    expected_benchmark_auprc = float(
        original_report["benchmark_metrics"]["auprc"]
    )

    reproduction_checks = {
        "delta_auprc": math.isclose(
            reproduced["delta_auprc"],
            expected_delta,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "candidate_auprc": math.isclose(
            reproduced_candidate_auprc,
            expected_candidate_auprc,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "benchmark_auprc": math.isclose(
            reproduced_benchmark_auprc,
            expected_benchmark_auprc,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
    }
    if not all(reproduction_checks.values()):
        raise RuntimeError(
            "Reconstructed Phase 3 results do not match "
            "the existing aggregate report"
        )

    fitted_results = {
        predictor: run_single_predictor_nested_cv(
            rows,
            manifest,
            predictor,
        )
        for predictor in ALLOWED_SINGLE_PREDICTORS
    }
    for result in fitted_results.values():
        ensure_aligned(
            primary.labels,
            primary.subjects,
            result,
        )

    fitted_map = fitted_results["map_mean_6h"]
    fitted_current = fitted_results[
        "mean_arterial_pressure_current"
    ]

    specifications = [
        {
            "strategy": "fixed_map_mean_6h_score",
            "predictor_count": 1,
            "score_variant": "ranking_score",
            "score_semantics": "uncalibrated_ranking_score",
            "scores": primary.benchmark,
            "probability_output": False,
            "fold_records": (),
        },
        {
            "strategy": "fitted_map_mean_6h_logistic",
            "predictor_count": 1,
            "score_variant": "raw_probability",
            "score_semantics": "model_probability",
            "scores": fitted_map.raw_probabilities,
            "probability_output": True,
            "fold_records": fitted_map.fold_records,
        },
        {
            "strategy": "fitted_map_mean_6h_logistic",
            "predictor_count": 1,
            "score_variant": (
                "platt_calibrated_probability"
            ),
            "score_semantics": "recalibrated_probability",
            "scores": fitted_map.calibrated_probabilities,
            "probability_output": True,
            "fold_records": fitted_map.fold_records,
        },
        {
            "strategy": "fitted_current_map_logistic",
            "predictor_count": 1,
            "score_variant": "raw_probability",
            "score_semantics": "model_probability",
            "scores": fitted_current.raw_probabilities,
            "probability_output": True,
            "fold_records": fitted_current.fold_records,
        },
        {
            "strategy": "fitted_current_map_logistic",
            "predictor_count": 1,
            "score_variant": (
                "platt_calibrated_probability"
            ),
            "score_semantics": "recalibrated_probability",
            "scores": fitted_current.calibrated_probabilities,
            "probability_output": True,
            "fold_records": fitted_current.fold_records,
        },
        {
            "strategy": "candidate_18_predictor_logistic",
            "predictor_count": 18,
            "score_variant": "raw_probability",
            "score_semantics": "model_probability",
            "scores": primary.raw_candidate,
            "probability_output": True,
            "fold_records": primary.fold_records,
        },
        {
            "strategy": "candidate_18_predictor_logistic",
            "predictor_count": 18,
            "score_variant": (
                "platt_calibrated_probability"
            ),
            "score_semantics": "recalibrated_probability",
            "scores": primary.calibrated_candidate,
            "probability_output": True,
            "fold_records": primary.fold_records,
        },
    ]

    all_fold_rows: list[dict[str, Any]] = []
    for specification in specifications:
        all_fold_rows.extend(
            fold_metric_rows(
                strategy=specification["strategy"],
                predictor_count=specification[
                    "predictor_count"
                ],
                score_variant=specification[
                    "score_variant"
                ],
                labels=primary.labels,
                subjects=primary.subjects,
                scores=specification["scores"],
                manifest=manifest,
                probability_output=specification[
                    "probability_output"
                ],
                fold_records=specification[
                    "fold_records"
                ],
            )
        )

    summary_rows = [
        summary_row(
            strategy=specification["strategy"],
            predictor_count=specification[
                "predictor_count"
            ],
            score_variant=specification["score_variant"],
            score_semantics=specification[
                "score_semantics"
            ],
            labels=primary.labels,
            subjects=primary.subjects,
            scores=specification["scores"],
            probability_output=specification[
                "probability_output"
            ],
            fold_rows=all_fold_rows,
        )
        for specification in specifications
    ]

    bootstrap_replicates = int(
        config["validation"]["bootstrap_replicates"]
    )
    seed = int(config["fold_manifest"]["seed"])

    raw_probability_models = {
        "candidate_18_predictor_logistic": (
            primary.raw_candidate
        ),
        "fitted_map_mean_6h_logistic": (
            fitted_map.raw_probabilities
        ),
        "fitted_current_map_logistic": (
            fitted_current.raw_probabilities
        ),
    }

    comparisons_vs_fitted_map = paired_patient_bootstrap(
        primary.subjects,
        primary.labels,
        raw_probability_models,
        reference_model="fitted_map_mean_6h_logistic",
        probability_models=set(raw_probability_models),
        replicates=bootstrap_replicates,
        seed=seed,
    )
    comparisons_vs_current_map = paired_patient_bootstrap(
        primary.subjects,
        primary.labels,
        {
            "candidate_18_predictor_logistic": (
                primary.raw_candidate
            ),
            "fitted_current_map_logistic": (
                fitted_current.raw_probabilities
            ),
        },
        reference_model="fitted_current_map_logistic",
        probability_models={
            "candidate_18_predictor_logistic",
            "fitted_current_map_logistic",
        },
        replicates=bootstrap_replicates,
        seed=seed,
    )
    fitted_vs_fixed_map = paired_patient_bootstrap(
        primary.subjects,
        primary.labels,
        {
            "fitted_map_mean_6h_logistic": (
                fitted_map.raw_probabilities
            ),
            "fixed_map_mean_6h_score": primary.benchmark,
        },
        reference_model="fixed_map_mean_6h_score",
        probability_models={
            "fitted_map_mean_6h_logistic",
        },
        replicates=bootstrap_replicates,
        seed=seed,
    )

    report = {
        "analysis": {
            "name": (
                "fitted single-predictor comparator analysis"
            ),
            "role": (
                "reviewer-requested post-hoc internal "
                "development analysis"
            ),
            "prespecified": False,
            "confirmatory": False,
            "evaluation_design": (
                "patient-grouped nested cross-validation "
                "internal validation"
            ),
            "outer_folds": 5,
            "inner_folds": 3,
            "model_selection_metric": (
                "mean inner-fold AUPRC"
            ),
            "calibration_scope": (
                "outer-training inner-OOF predictions only"
            ),
            "purpose": (
                "Compare the frozen 18-predictor candidate "
                "against fitted MAP-only models evaluated "
                "under the same nested procedure."
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
        "original_phase3_reproduction": {
            "checks": reproduction_checks,
            "expected_candidate_auprc": (
                expected_candidate_auprc
            ),
            "reproduced_candidate_auprc": (
                reproduced_candidate_auprc
            ),
            "expected_benchmark_auprc": (
                expected_benchmark_auprc
            ),
            "reproduced_benchmark_auprc": (
                reproduced_benchmark_auprc
            ),
            "expected_delta_auprc": expected_delta,
            "reproduced_delta_auprc": (
                reproduced["delta_auprc"]
            ),
        },
        "pooled_results": summary_rows,
        "fold_results": all_fold_rows,
        "paired_patient_cluster_bootstrap": {
            "replicates": bootstrap_replicates,
            "seed": seed,
            "comparisons_vs_fitted_map_mean_6h": (
                comparisons_vs_fitted_map
            ),
            "comparisons_vs_fitted_current_map": (
                comparisons_vs_current_map
            ),
            "fitted_map_mean_6h_vs_fixed_score": (
                fitted_vs_fixed_map
            ),
        },
        "interpretation_constraints": [
            (
                "This analysis was requested after the primary "
                "Phase 3 results were available."
            ),
            (
                "The fitted one-predictor models are post-hoc "
                "comparators and do not replace the original "
                "prespecified comparator."
            ),
            (
                "Overlapping windows from the same patient are "
                "correlated and do not represent independent "
                "observations."
            ),
            (
                "Patient-cluster bootstrap retains patient-level "
                "clustering but cannot increase the number of "
                "independent patients."
            ),
            (
                "Pooled OOF AUPRC combines predictions from five "
                "separately fitted outer-fold models."
            ),
            (
                "Fold-specific Platt transformations can preserve "
                "within-fold ordering while changing ordering "
                "between folds in the pooled result."
            ),
        ],
    }

    safe_report = json_safe(report)
    assert_public_metadata(safe_report)

    write_json(args.json_output, safe_report)
    write_csv(
        args.summary_output,
        SUMMARY_FIELDS,
        summary_rows,
    )
    write_csv(
        args.fold_output,
        FOLD_FIELDS,
        all_fold_rows,
    )

    print("Post-hoc internal comparison completed.")
    print(f"Patients: {patient_count}")
    print(f"Windows: {len(rows)}")
    print(f"JSON report: {args.json_output}")
    print(f"Summary CSV: {args.summary_output}")
    print(f"Fold CSV: {args.fold_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
