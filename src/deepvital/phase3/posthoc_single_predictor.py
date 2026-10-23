"""Post-hoc single-predictor models using the frozen Phase 3 folds."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from deepvital.evaluation.metrics import (
    average_precision,
    evaluate_probabilities,
    roc_auc,
    select_thresholds,
)
from deepvital.phase3.implementation import (
    C_GRID,
    _manifest_partitions,
    _platt_apply,
    _platt_fit,
)
from deepvital.phase3.prefreeze import (
    OUTER_FOLDS,
    PHASE3_SEED,
    raw_map_mean_6h,
)

ALLOWED_SINGLE_PREDICTORS = (
    "map_mean_6h",
    "mean_arterial_pressure_current",
)

EVALUATION_DESIGN = (
    "patient-grouped nested cross-validation internal validation"
)


def _validate_predictor(predictor: str) -> None:
    """Reject predictors outside the reviewer-requested comparison."""
    if predictor not in ALLOWED_SINGLE_PREDICTORS:
        allowed = ", ".join(ALLOWED_SINGLE_PREDICTORS)
        raise ValueError(
            f"Unsupported single predictor: {predictor}. "
            f"Allowed predictors: {allowed}"
        )


def _finite_float(value: Any) -> float | None:
    """Convert a value to a finite float or return None."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    return result if math.isfinite(result) else None


def single_predictor_value(
    row: Mapping[str, Any],
    predictor: str,
) -> float | None:
    """Derive one predictor without reading future outcome information."""
    _validate_predictor(predictor)

    if predictor == "map_mean_6h":
        return raw_map_mean_6h(row)

    return _finite_float(row.get("mean_arterial_pressure_current"))


def single_predictor_matrix(
    rows: Sequence[Mapping[str, Any]],
    predictor: str,
) -> list[list[float]]:
    """Build a one-column matrix for the requested predictor."""
    _validate_predictor(predictor)

    matrix: list[list[float]] = []
    for row in rows:
        value = single_predictor_value(row, predictor)
        matrix.append([
            math.nan if value is None else float(value)
        ])

    return matrix


def build_single_predictor_candidate(
    predictor: str,
    c_value: float,
) -> Any:
    """Build one logistic model with frozen Phase 3 settings."""
    _validate_predictor(predictor)

    if c_value not in C_GRID:
        raise ValueError(
            f"C must be one of the closed values {C_GRID}"
        )

    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline(
        [
            (
                "preprocessing",
                Pipeline(
                    [
                        (
                            "median_imputer",
                            SimpleImputer(strategy="median"),
                        ),
                        (
                            "standard_scaler",
                            StandardScaler(),
                        ),
                    ]
                ),
            ),
            (
                "candidate",
                LogisticRegression(
                    penalty="l2",
                    C=c_value,
                    solver="lbfgs",
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=PHASE3_SEED,
                ),
            ),
        ]
    )


@dataclass
class SinglePredictorOOFResult:
    """Internal out-of-fold predictions without public identifiers."""

    predictor: str
    labels: list[int]
    subjects: list[str]
    raw_probabilities: list[float]
    calibrated_probabilities: list[float]
    outer_folds: list[int]
    fold_records: list[dict[str, Any]]


def run_single_predictor_nested_cv(
    rows: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    predictor: str,
) -> SinglePredictorOOFResult:
    """Fit one predictor with the frozen patient-grouped nested procedure."""
    import numpy as np

    _validate_predictor(predictor)

    if not rows:
        raise ValueError("At least one row is required")

    x = np.asarray(
        single_predictor_matrix(rows, predictor),
        dtype=float,
    )
    labels = [int(row["label"]) for row in rows]
    subjects = [str(row["subject_id"]) for row in rows]

    if set(labels) != {0, 1}:
        raise ValueError(
            "Nested validation requires both outcome classes"
        )

    number_of_rows = len(rows)
    raw_output = [math.nan] * number_of_rows
    calibrated_output = [math.nan] * number_of_rows
    outer_fold_output = [0] * number_of_rows
    prediction_counts: Counter[int] = Counter()
    fold_records: list[dict[str, Any]] = []

    label_array = np.asarray(labels, dtype=int)

    for outer_fold in range(1, OUTER_FOLDS + 1):
        (
            outer_train,
            outer_valid,
            inner_train,
            inner_valid,
        ) = _manifest_partitions(
            subjects,
            manifest,
            outer_fold,
        )

        if not outer_train or not outer_valid:
            raise ValueError(
                f"Outer fold {outer_fold} is empty"
            )

        c_records: dict[float, dict[str, Any]] = {}

        for c_value in C_GRID:
            inner_fold_auprcs: list[float] = []
            inner_predictions: dict[int, float] = {}

            for training, validation in zip(
                inner_train,
                inner_valid,
                strict=True,
            ):
                model = build_single_predictor_candidate(
                    predictor,
                    c_value,
                )
                model.fit(
                    x[training],
                    label_array[training],
                )
                scores = model.predict_proba(
                    x[validation]
                )[:, 1]

                validation_labels = [
                    labels[index]
                    for index in validation
                ]
                inner_fold_auprcs.append(
                    average_precision(
                        validation_labels,
                        scores,
                    )
                )
                inner_predictions.update(
                    {
                        index: float(score)
                        for index, score in zip(
                            validation,
                            scores,
                            strict=True,
                        )
                    }
                )

            ordered_outer_train = sorted(outer_train)
            c_records[c_value] = {
                "mean_inner_fold_auprc": (
                    sum(inner_fold_auprcs)
                    / len(inner_fold_auprcs)
                ),
                "predictions": [
                    inner_predictions[index]
                    for index in ordered_outer_train
                ],
                "indices": ordered_outer_train,
            }

        selected_c = max(
            C_GRID,
            key=lambda value: (
                c_records[value]["mean_inner_fold_auprc"],
                -value,
            ),
        )
        selected = c_records[selected_c]

        inner_labels = [
            labels[index]
            for index in selected["indices"]
        ]
        inner_raw = selected["predictions"]

        platt_model = _platt_fit(
            inner_raw,
            inner_labels,
        )
        thresholds = select_thresholds(
            inner_labels,
            inner_raw,
        )

        final_model = build_single_predictor_candidate(
            predictor,
            selected_c,
        )
        final_model.fit(
            x[outer_train],
            label_array[outer_train],
        )

        outer_raw = [
            float(value)
            for value in final_model.predict_proba(
                x[outer_valid]
            )[:, 1]
        ]
        outer_calibrated = _platt_apply(
            platt_model,
            outer_raw,
        )

        for position, index in enumerate(outer_valid):
            raw_output[index] = outer_raw[position]
            calibrated_output[index] = (
                outer_calibrated[position]
            )
            outer_fold_output[index] = outer_fold
            prediction_counts[index] += 1

        outer_labels = [
            labels[index]
            for index in outer_valid
        ]
        outer_training_subjects = {
            subjects[index]
            for index in outer_train
        }
        outer_validation_subjects = {
            subjects[index]
            for index in outer_valid
        }
        overlap = (
            outer_training_subjects
            & outer_validation_subjects
        )

        if overlap:
            raise AssertionError(
                "Patient overlap across outer fold"
            )

        raw_auprc = average_precision(
            outer_labels,
            outer_raw,
        )
        calibrated_auprc = average_precision(
            outer_labels,
            outer_calibrated,
        )

        fold_records.append(
            {
                "outer_fold": outer_fold,
                "selected_C": selected_c,
                "inner_mean_auprc_by_C": {
                    str(value): c_records[value][
                        "mean_inner_fold_auprc"
                    ]
                    for value in C_GRID
                },
                "threshold_selection": "inner_oof_only",
                "youden_threshold": thresholds["youden"],
                "calibration_method": "platt_logistic",
                "calibration_training_scope": (
                    "outer_training_inner_oof_only"
                ),
                "platt_intercept": float(
                    platt_model.intercept_[0]
                ),
                "platt_slope": float(
                    platt_model.coef_[0][0]
                ),
                "outer_training_patients": len(
                    outer_training_subjects
                ),
                "outer_validation_patients": len(
                    outer_validation_subjects
                ),
                "outer_validation_windows": len(
                    outer_valid
                ),
                "patient_overlap": len(overlap),
                "raw_auprc": raw_auprc,
                "calibrated_auprc": calibrated_auprc,
                "calibrated_minus_raw_auprc": (
                    calibrated_auprc - raw_auprc
                ),
                "raw_auroc": roc_auc(
                    outer_labels,
                    outer_raw,
                ),
                "calibrated_auroc": roc_auc(
                    outer_labels,
                    outer_calibrated,
                ),
            }
        )

    if (
        len(prediction_counts) != number_of_rows
        or set(prediction_counts.values()) != {1}
    ):
        raise AssertionError(
            "Every window must receive exactly one "
            "outer-fold prediction"
        )

    if any(
        not math.isfinite(value)
        for value in raw_output
    ):
        raise AssertionError(
            "All raw OOF probabilities must be finite"
        )

    if any(
        not math.isfinite(value)
        for value in calibrated_output
    ):
        raise AssertionError(
            "All calibrated OOF probabilities must be finite"
        )

    if any(
        outer_fold == 0
        for outer_fold in outer_fold_output
    ):
        raise AssertionError(
            "Every row must have one outer-fold assignment"
        )

    return SinglePredictorOOFResult(
        predictor=predictor,
        labels=labels,
        subjects=subjects,
        raw_probabilities=raw_output,
        calibrated_probabilities=calibrated_output,
        outer_folds=outer_fold_output,
        fold_records=fold_records,
    )


def summarize_single_predictor_oof(
    result: SinglePredictorOOFResult,
) -> dict[str, Any]:
    """Create aggregate pooled and fold-level discrimination results."""
    raw_metrics = evaluate_probabilities(
        result.labels,
        result.raw_probabilities,
    )
    calibrated_metrics = evaluate_probabilities(
        result.labels,
        result.calibrated_probabilities,
    )

    raw_fold_auprcs = [
        float(record["raw_auprc"])
        for record in result.fold_records
    ]
    calibrated_fold_auprcs = [
        float(record["calibrated_auprc"])
        for record in result.fold_records
    ]

    return {
        "analysis_status": "post_hoc_exploratory",
        "evaluation_design": EVALUATION_DESIGN,
        "predictor": result.predictor,
        "model": "l2_logistic_regression",
        "number_of_patients": len(set(result.subjects)),
        "number_of_windows": len(result.labels),
        "positive_windows": sum(result.labels),
        "prevalence": (
            sum(result.labels) / len(result.labels)
        ),
        "pooled": {
            "raw_metrics": raw_metrics,
            "calibrated_metrics": calibrated_metrics,
            "calibrated_minus_raw_auprc": (
                calibrated_metrics["auprc"]
                - raw_metrics["auprc"]
            ),
        },
        "fold_distribution": {
            "raw_auprc": raw_fold_auprcs,
            "calibrated_auprc": calibrated_fold_auprcs,
            "raw_auprc_mean": (
                sum(raw_fold_auprcs)
                / len(raw_fold_auprcs)
            ),
            "calibrated_auprc_mean": (
                sum(calibrated_fold_auprcs)
                / len(calibrated_fold_auprcs)
            ),
            "raw_auprc_min": min(raw_fold_auprcs),
            "raw_auprc_max": max(raw_fold_auprcs),
            "calibrated_auprc_min": min(
                calibrated_fold_auprcs
            ),
            "calibrated_auprc_max": max(
                calibrated_fold_auprcs
            ),
        },
        "folds": result.fold_records,
    }
