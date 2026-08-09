"""Frozen Phase 3 model, validation, inference, and decision contracts."""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deepvital.evaluation.bootstrap import paired_patient_bootstrap
from deepvital.evaluation.calibration import calibration_intercept_slope
from deepvital.evaluation.metrics import (
    average_precision,
    evaluate_probabilities,
    evaluate_with_thresholds,
    roc_auc,
    select_thresholds,
)
from deepvital.phase3.prefreeze import (
    INNER_FOLDS,
    LOCKED_FEATURES,
    OUTER_FOLDS,
    PHASE3_SEED,
    derive_locked_features,
    fold_manifest_fingerprint,
    map_mean_6h_benchmark_score,
)

CONTINUOUS_FEATURES = LOCKED_FEATURES[:13]
BINARY_FEATURES = LOCKED_FEATURES[13:]
C_GRID = (0.1, 1.0)
ADVANCEMENT_MARGIN = 0.02
PATIENT_EQUAL_ROBUSTNESS_FLOOR = -0.02
BP_SOURCE_ROBUSTNESS_FLOOR = -0.02
APPROVED_MODEL_NAME = "l2_logistic_regression"


def load_frozen_manifest(path: Path, expected_fingerprint: str) -> dict[str, Any]:
    """Consume, never regenerate, the private manifest after fingerprint verification."""
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    actual = fold_manifest_fingerprint(manifest)
    if actual != expected_fingerprint:
        raise ValueError("Private fold-manifest fingerprint mismatch")
    return manifest


def validate_frozen_config(config: Mapping[str, Any]) -> None:
    """Reject any configuration that differs from the frozen protocol."""
    expected_sections = {
        "candidate": {
            "model": "logistic_regression",
            "penalty": "l2",
            "solver": "lbfgs",
            "class_weight": "balanced",
            "max_iter": 1000,
            "C_values": [0.1, 1.0],
        },
        "benchmark": {
            "name": "map_mean_6h",
            "risk_center_map": 65.0,
            "risk_scale_map": 10.0,
            "uncalculable_primary_score": 0.5,
        },
        "validation": {
            "primary_metric": "delta_auprc",
            "bootstrap_replicates": 1000,
            "bootstrap_confidence": 0.95,
            "advancement_margin": ADVANCEMENT_MARGIN,
            "patient_equal_robustness_floor": -0.02,
            "bp_source_robustness_floor": -0.02,
        },
        "calibration": {
            "method": "platt_logistic",
            "training_scope": "outer_training_inner_oof_only",
        },
        "thresholds": {
            "primary": "youden",
            "secondary": "target_sensitivity_0.80",
            "target_sensitivity": 0.8,
            "youden_tie_break": "higher_threshold",
        },
        "sensitivities": {
            "map_thresholds": [60.0, 65.0, 70.0],
            "consecutive_hours": [1, 2, 3],
            "future_map_missing_bounds": [
                "missing_as_not_low",
                "missing_as_low",
            ],
            "bp_source_alternatives": [
                "invasive_preferred",
                "non_invasive_only",
            ],
            "invasive_systolic_codes": ["220050", "225309"],
            "invasive_map_codes": ["220052", "225312"],
            "non_invasive_systolic_codes": ["220179"],
            "non_invasive_map_codes": ["220181"],
            "benchmark_missingness": ["neutral_score_0.5", "complete_case"],
            "evaluation_weighting": ["window_weighted", "patient_equal"],
        },
    }
    mismatches = [
        section
        for section, expected in expected_sections.items()
        if config.get(section) != expected
    ]
    fold = config.get("fold_manifest", {})
    if (fold.get("seed"), fold.get("outer_folds"), fold.get("inner_folds")) != (
        PHASE3_SEED,
        OUTER_FOLDS,
        INNER_FOLDS,
    ):
        mismatches.append("fold_manifest")
    if mismatches:
        raise ValueError("Frozen Phase 3 configuration mismatch: " + ", ".join(mismatches))


def build_locked_candidate(c_value: float) -> Any:
    """Build the sole approved candidate with training-only preprocessing."""
    if c_value not in C_GRID:
        raise ValueError(f"C must be one of the closed values {C_GRID}")
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    continuous_indices = list(range(len(CONTINUOUS_FEATURES)))
    binary_indices = list(range(len(CONTINUOUS_FEATURES), len(LOCKED_FEATURES)))
    preprocessing = ColumnTransformer(
        [
            (
                "continuous",
                Pipeline(
                    [
                        ("median_imputer", SimpleImputer(strategy="median")),
                        ("standard_scaler", StandardScaler()),
                    ]
                ),
                continuous_indices,
            ),
            ("binary_missingness", "passthrough", binary_indices),
        ],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocessing", preprocessing),
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


def locked_matrix(rows: Sequence[Mapping[str, Any]]) -> list[list[float]]:
    """Create an exact 18-column matrix and reject malformed binary indicators."""
    matrix = []
    for row in rows:
        values = derive_locked_features(row)
        if tuple(values) != LOCKED_FEATURES:
            raise AssertionError("Locked feature order changed")
        matrix.append([
            math.nan if values[name] is None else float(values[name])
            for name in LOCKED_FEATURES
        ])
    return matrix


def _manifest_partitions(
    subjects: Sequence[str], manifest: Mapping[str, Any], outer_fold: int
) -> tuple[list[int], list[int], list[list[int]], list[list[int]]]:
    assignments = manifest["patient_assignments"]
    unknown = set(subjects) - set(assignments)
    if unknown:
        raise ValueError("Dataset contains patients absent from private fold manifest")
    outer_train = [
        index
        for index, subject in enumerate(subjects)
        if int(assignments[subject]["outer_fold"]) != outer_fold
    ]
    outer_valid = [
        index
        for index, subject in enumerate(subjects)
        if int(assignments[subject]["outer_fold"]) == outer_fold
    ]
    inner_train: list[list[int]] = []
    inner_valid: list[list[int]] = []
    for inner_fold in range(1, INNER_FOLDS + 1):
        validation = [
            index
            for index in outer_train
            if int(
                assignments[subjects[index]][
                    "inner_validation_fold_by_outer_training_fold"
                ][str(outer_fold)]
            )
            == inner_fold
        ]
        training = [index for index in outer_train if index not in set(validation)]
        if {subjects[index] for index in training} & {
            subjects[index] for index in validation
        }:
            raise AssertionError("Patient overlap across inner fold")
        inner_train.append(training)
        inner_valid.append(validation)
    if {subjects[index] for index in outer_train} & {
        subjects[index] for index in outer_valid
    }:
        raise AssertionError("Patient overlap across outer fold")
    return outer_train, outer_valid, inner_train, inner_valid


def _platt_fit(scores: Sequence[float], labels: Sequence[int]) -> Any:
    """Fit the sole allowed calibration model on inner OOF scores."""
    if len(set(labels)) < 2:
        raise ValueError("Platt calibration requires both outcome classes")
    import numpy as np
    from sklearn.linear_model import LogisticRegression

    model = LogisticRegression(penalty=None, solver="lbfgs", max_iter=1000)
    model.fit(np.asarray(scores).reshape(-1, 1), labels)
    return model


def _platt_apply(model: Any, scores: Sequence[float]) -> list[float]:
    import numpy as np

    return [
        float(value)
        for value in model.predict_proba(np.asarray(scores).reshape(-1, 1))[:, 1]
    ]


@dataclass
class OOFResult:
    """In-memory development predictions; patient identifiers are never public output."""

    labels: list[int]
    subjects: list[str]
    raw_candidate: list[float]
    calibrated_candidate: list[float]
    benchmark: list[float]
    candidate_thresholds: list[float]
    benchmark_thresholds: list[float]
    fold_records: list[dict[str, Any]]


def run_frozen_nested_cv(
    rows: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any]
) -> OOFResult:
    """Run exactly the registered 5x3 nested procedure on supplied rows."""
    import numpy as np

    x = np.asarray(locked_matrix(rows), dtype=float)
    labels = [int(row["label"]) for row in rows]
    subjects = [str(row["subject_id"]) for row in rows]
    n_rows = len(rows)
    outputs = {
        "raw": [math.nan] * n_rows,
        "calibrated": [math.nan] * n_rows,
        "benchmark": [math.nan] * n_rows,
        "candidate_threshold": [math.nan] * n_rows,
        "benchmark_threshold": [math.nan] * n_rows,
    }
    counts: Counter[int] = Counter()
    fold_records = []
    for outer_fold in range(1, OUTER_FOLDS + 1):
        outer_train, outer_valid, inner_train, inner_valid = _manifest_partitions(
            subjects, manifest, outer_fold
        )
        c_records: dict[float, dict[str, Any]] = {}
        for c_value in C_GRID:
            fold_auprcs = []
            inner_predictions: dict[int, float] = {}
            for training, validation in zip(inner_train, inner_valid, strict=True):
                model = build_locked_candidate(c_value)
                model.fit(x[training], np.asarray(labels)[training])
                scores = model.predict_proba(x[validation])[:, 1]
                fold_auprcs.append(
                    average_precision([labels[index] for index in validation], scores)
                )
                inner_predictions.update(
                    {index: float(score) for index, score in zip(validation, scores)}
                )
            ordered_train = sorted(outer_train)
            c_records[c_value] = {
                "mean_inner_fold_auprc": sum(fold_auprcs) / len(fold_auprcs),
                "predictions": [inner_predictions[index] for index in ordered_train],
                "indices": ordered_train,
            }
        selected_c = max(
            C_GRID, key=lambda value: (c_records[value]["mean_inner_fold_auprc"], -value)
        )
        selected = c_records[selected_c]
        inner_y = [labels[index] for index in selected["indices"]]
        inner_raw = selected["predictions"]
        platt = _platt_fit(inner_raw, inner_y)
        candidate_thresholds = select_thresholds(inner_y, inner_raw)
        inner_benchmark = [
            map_mean_6h_benchmark_score(rows[index]) for index in selected["indices"]
        ]
        benchmark_thresholds = select_thresholds(inner_y, inner_benchmark)
        model = build_locked_candidate(selected_c)
        model.fit(x[outer_train], np.asarray(labels)[outer_train])
        outer_raw = [float(value) for value in model.predict_proba(x[outer_valid])[:, 1]]
        outer_calibrated = _platt_apply(platt, outer_raw)
        for position, index in enumerate(outer_valid):
            outputs["raw"][index] = outer_raw[position]
            outputs["calibrated"][index] = outer_calibrated[position]
            outputs["benchmark"][index] = map_mean_6h_benchmark_score(rows[index])
            outputs["candidate_threshold"][index] = candidate_thresholds["youden"]
            outputs["benchmark_threshold"][index] = benchmark_thresholds["youden"]
            counts[index] += 1
        fold_records.append(
            {
                "outer_fold": outer_fold,
                "selected_C": selected_c,
                "inner_mean_auprc_by_C": {
                    str(value): c_records[value]["mean_inner_fold_auprc"]
                    for value in C_GRID
                },
                "candidate_threshold": candidate_thresholds,
                "benchmark_threshold": benchmark_thresholds,
                "calibration_method": "platt_logistic",
                "calibration_training_scope": "outer_training_inner_oof_only",
                "outer_training_patients": len({subjects[index] for index in outer_train}),
                "outer_validation_patients": len(
                    {subjects[index] for index in outer_valid}
                ),
                "outer_validation_windows": len(outer_valid),
                "patient_overlap": 0,
            }
        )
    if len(counts) != n_rows or set(counts.values()) != {1}:
        raise AssertionError("Every eligible window must receive exactly one OOF prediction")
    if any(not math.isfinite(value) for values in outputs.values() for value in values):
        raise AssertionError("All OOF outputs must be finite")
    return OOFResult(
        labels,
        subjects,
        outputs["raw"],
        outputs["calibrated"],
        outputs["benchmark"],
        outputs["candidate_threshold"],
        outputs["benchmark_threshold"],
        fold_records,
    )


def summarize_oof(result: OOFResult, bootstrap_replicates: int = 1000) -> dict[str, Any]:
    """Calculate only the frozen aggregate comparisons from OOF predictions."""
    paired = paired_patient_bootstrap(
        result.subjects,
        result.labels,
        {
            "logistic_regression": result.raw_candidate,
            "map_mean_6h": result.benchmark,
        },
        "map_mean_6h",
        {"logistic_regression"},
        bootstrap_replicates,
        PHASE3_SEED,
    )
    comparisons = {row["metric"]: row for row in paired}
    intercept, slope = calibration_intercept_slope(
        result.labels, result.calibrated_candidate
    )
    return {
        "primary": comparisons["delta_auprc"],
        "secondary_delta_auroc": comparisons["delta_auroc"],
        "raw_candidate_metrics": evaluate_with_thresholds(
            result.labels,
            result.raw_candidate,
            result.candidate_thresholds,
            probability_output=True,
        ),
        "calibrated_candidate_metrics": evaluate_probabilities(
            result.labels, result.calibrated_candidate
        ),
        "benchmark_metrics": evaluate_with_thresholds(
            result.labels,
            result.benchmark,
            result.benchmark_thresholds,
            probability_output=False,
        ),
        "calibration": {"intercept": intercept, "slope": slope},
        "folds": result.fold_records,
    }


def advancement_decision(
    *,
    delta_auprc: float,
    delta_auprc_ci_lower: float,
    oof_accounting_valid: bool,
    primary_protocol_deviation: bool,
    patient_equal_delta_auprc: float,
    bp_source_delta_auprcs: Mapping[str, float],
    sensitivities_disclosed: bool,
    threshold_reproducible: bool,
) -> dict[str, Any]:
    """Expose every frozen advancement and robustness criterion independently."""
    criteria = {
        "delta_auprc_at_least_0.02": delta_auprc >= ADVANCEMENT_MARGIN,
        "paired_ci_lower_above_zero": delta_auprc_ci_lower > 0.0,
        "oof_accounting_valid": oof_accounting_valid,
        "no_primary_protocol_deviation": not primary_protocol_deviation,
    }
    robustness = {
        "patient_equal_delta_not_below_minus_0.02": (
            patient_equal_delta_auprc >= PATIENT_EQUAL_ROBUSTNESS_FLOOR
        ),
        "all_bp_source_deltas_not_below_minus_0.02": all(
            value >= BP_SOURCE_ROBUSTNESS_FLOOR
            for value in bp_source_delta_auprcs.values()
        ),
        "sensitivities_and_failures_disclosed": sensitivities_disclosed,
        "threshold_and_score_semantics_reproducible": threshold_reproducible,
    }
    primary_pass = all(criteria.values())
    robustness_pass = all(robustness.values())
    return {
        "primary_criteria": {
            name: {"status": "PASS" if passed else "FAIL", "passed": passed}
            for name, passed in criteria.items()
        },
        "robustness_criteria": {
            name: {"status": "PASS" if passed else "FAIL", "passed": passed}
            for name, passed in robustness.items()
        },
        "primary_advancement_passed": primary_pass,
        "robustness_review_passed": robustness_pass,
        "decision": (
            "logistic_regression_advances"
            if primary_pass and robustness_pass
            else "retain_map_mean_6h_or_no_strategy_ready"
        ),
    }


def patient_equal_delta_auprc(result: OOFResult) -> float:
    """Return candidate-minus-benchmark AUPRC with total patient weight one."""
    from deepvital.evaluation.bootstrap import patient_equal_weights

    weights = patient_equal_weights(result.subjects)
    return average_precision(
        result.labels, result.raw_candidate, weights
    ) - average_precision(result.labels, result.benchmark, weights)


def discrimination_delta(labels: Sequence[int], candidate: Sequence[float], benchmark: Sequence[float]) -> dict[str, float]:
    """Return the two frozen candidate-minus-benchmark discrimination differences."""
    return {
        "delta_auprc": average_precision(labels, candidate)
        - average_precision(labels, benchmark),
        "delta_auroc": roc_auc(labels, candidate) - roc_auc(labels, benchmark),
    }
