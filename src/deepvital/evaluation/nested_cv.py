"""Patient-grouped nested cross-validation for development-only evaluation."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .bootstrap import paired_patient_bootstrap, patient_bootstrap
from .metrics import evaluate_probabilities, evaluate_with_thresholds, select_thresholds

EstimatorFactory = Callable[[], Any]
ScoreProvider = Callable[
    [Sequence[int], Sequence[int]], tuple[Sequence[float], Sequence[bool]]
]


def _score_report(values: Mapping[str, Any], probability: bool) -> dict[str, Any]:
    """Keep probability losses only for interpretable probability outputs."""
    keys = [
        "auroc",
        "auprc",
        "threshold",
        "threshold_policy",
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
    if probability:
        keys.extend(["brier_score", "log_loss"])
    return {key: values[key] for key in keys if key in values}


def grouped_nested_cross_validation(
    x: Sequence[Sequence[float]],
    y: Sequence[int],
    subjects: Sequence[str],
    candidates: Mapping[str, EstimatorFactory],
    benchmarks: Mapping[str, ScoreProvider] | None = None,
    benchmark_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    outer_folds: int = 5,
    inner_folds: int = 3,
    seed: int = 20260726,
    bootstrap_replicates: int = 1000,
) -> dict[str, Any]:
    """Generate each patient's prediction in one outer fold only.

    Candidate and threshold selection use inner out-of-fold predictions from the
    outer-training patients. Applicable imputation and scaling remain inside each
    candidate pipeline and are therefore fitted separately in every training fold.
    """
    import numpy as np
    from sklearn.model_selection import GroupKFold

    if not (len(x) == len(y) == len(subjects)):
        raise ValueError("Features, labels, and patient groups must have equal length")
    unique_subjects = set(subjects)
    if outer_folds < 2 or outer_folds > len(unique_subjects):
        raise ValueError("Invalid number of patient-grouped outer folds")
    x_array, y_array, groups = np.asarray(x), np.asarray(y), np.asarray(subjects)
    outer = GroupKFold(n_splits=outer_folds)
    pooled_y: list[int] = []
    pooled_scores: list[float] = []
    pooled_subjects: list[str] = []
    fold_records: list[dict[str, Any]] = []
    patient_prediction_counts: Counter[str] = Counter()
    window_prediction_counts: Counter[int] = Counter()
    patient_outer_folds: dict[str, set[int]] = defaultdict(set)
    pooled_scores_by_model: dict[str, list[float]] = defaultdict(list)
    pooled_thresholds_by_model: dict[str, list[float]] = defaultdict(list)
    pooled_availability_by_model: dict[str, list[bool]] = defaultdict(list)
    benchmarks = benchmarks or {}
    benchmark_metadata = benchmark_metadata or {}

    for fold, (outer_train, outer_valid) in enumerate(
        outer.split(x_array, y_array, groups), start=1
    ):
        train_groups = groups[outer_train]
        valid_groups = groups[outer_valid]
        if set(train_groups) & set(valid_groups):
            raise AssertionError("Patient overlap across outer fold")
        if inner_folds > len(set(train_groups)):
            raise ValueError("Too few outer-training patients for inner folds")
        inner = GroupKFold(n_splits=inner_folds)
        inner_splits = list(
            inner.split(x_array[outer_train], y_array[outer_train], train_groups)
        )
        candidate_records: dict[str, dict[str, Any]] = {}
        for name, factory in sorted(candidates.items()):
            inner_y: list[int] = []
            inner_scores: list[float] = []
            for inner_train_rel, inner_valid_rel in inner_splits:
                inner_train = outer_train[inner_train_rel]
                inner_valid = outer_train[inner_valid_rel]
                if set(groups[inner_train]) & set(groups[inner_valid]):
                    raise AssertionError("Patient overlap across inner fold")
                model = factory()
                model.fit(x_array[inner_train], y_array[inner_train])
                inner_y.extend(int(value) for value in y_array[inner_valid])
                inner_scores.extend(
                    float(value)
                    for value in model.predict_proba(x_array[inner_valid])[:, 1]
                )
            thresholds = select_thresholds(inner_y, inner_scores)
            metrics = evaluate_probabilities(inner_y, inner_scores, thresholds["youden"])
            candidate_records[name] = {
                "inner_auprc": metrics["auprc"],
                "inner_brier_score": metrics["brier_score"],
                "threshold": thresholds["youden"],
            }
        selected = min(
            candidate_records,
            key=lambda name: (
                -candidate_records[name]["inner_auprc"],
                candidate_records[name]["inner_brier_score"],
                name,
            ),
        )
        model = candidates[selected]()
        model.fit(x_array[outer_train], y_array[outer_train])
        scores = [
            float(value) for value in model.predict_proba(x_array[outer_valid])[:, 1]
        ]
        threshold = candidate_records[selected]["threshold"]
        fold_metrics = evaluate_probabilities(y_array[outer_valid], scores, threshold)
        pooled_scores_by_model["nested_ml_strategy"].extend(scores)
        pooled_thresholds_by_model["nested_ml_strategy"].extend(
            [threshold] * len(scores)
        )

        benchmark_records: dict[str, dict[str, Any]] = {}
        for name, provider in sorted(benchmarks.items()):
            inner_y: list[int] = []
            inner_scores: list[float] = []
            for inner_train_rel, inner_valid_rel in inner_splits:
                inner_train = outer_train[inner_train_rel]
                inner_valid = outer_train[inner_valid_rel]
                inner_y.extend(int(value) for value in y_array[inner_valid])
                provided_scores, _ = provider(inner_train, inner_valid)
                inner_scores.extend(float(value) for value in provided_scores)
            benchmark_threshold = select_thresholds(inner_y, inner_scores)["youden"]
            provided_scores, provided_availability = provider(outer_train, outer_valid)
            outer_scores = [float(value) for value in provided_scores]
            outer_availability = [bool(value) for value in provided_availability]
            if not (
                len(outer_scores) == len(outer_availability) == len(outer_valid)
            ):
                raise ValueError(f"Benchmark {name} returned misaligned scores")
            pooled_scores_by_model[name].extend(outer_scores)
            pooled_availability_by_model[name].extend(outer_availability)
            pooled_thresholds_by_model[name].extend(
                [benchmark_threshold] * len(outer_scores)
            )
            benchmark_probability = (
                benchmark_metadata.get(name, {}).get("prediction_output_type")
                == "probability"
            )
            benchmark_records[name] = {
                "threshold_source": "inner_cross_validation_only",
                "threshold": benchmark_threshold,
                "metrics": _score_report(
                    evaluate_with_thresholds(
                        y_array[outer_valid],
                        outer_scores,
                        [benchmark_threshold] * len(outer_scores),
                        probability_output=benchmark_probability,
                    ),
                    benchmark_probability,
                ),
                "missing_score_policy": "neutral_risk_0.5",
                "unavailable_windows": outer_availability.count(False),
            }
        for subject in set(valid_groups):
            patient_prediction_counts[str(subject)] += 1
            patient_outer_folds[str(subject)].add(fold)
        for index in outer_valid:
            window_prediction_counts[int(index)] += 1
        pooled_y.extend(int(value) for value in y_array[outer_valid])
        pooled_scores.extend(scores)
        pooled_subjects.extend(str(value) for value in valid_groups)
        fold_records.append(
            {
                "fold": fold,
                "selected_candidate": selected,
                "threshold_source": "inner_cross_validation_only",
                "threshold": threshold,
                "patients": len(set(valid_groups)),
                "windows": len(outer_valid),
                "metrics": fold_metrics,
                "inner_selection": candidate_records,
                "clinical_benchmarks": benchmark_records,
            }
        )

    if set(patient_prediction_counts.values()) != {1}:
        raise AssertionError("Each patient must occur in exactly one outer fold")
    if any(len(folds) != 1 for folds in patient_outer_folds.values()):
        raise AssertionError("A patient was assigned to multiple outer folds")
    if len(window_prediction_counts) != len(y) or set(window_prediction_counts.values()) != {1}:
        raise AssertionError("Every eligible window must receive exactly one OOF prediction")
    pooled = evaluate_probabilities(pooled_y, pooled_scores, 0.5)
    comparison = []
    probability_models = {"nested_ml_strategy"} | {
        name
        for name, metadata in benchmark_metadata.items()
        if metadata.get("prediction_output_type") == "probability"
    }
    for name, model_scores in sorted(pooled_scores_by_model.items()):
        inner_threshold_metrics = evaluate_with_thresholds(
            pooled_y,
            model_scores,
            pooled_thresholds_by_model[name],
            probability_output=name in probability_models,
        )
        probability_output = name in probability_models
        descriptive_metrics = evaluate_with_thresholds(
            pooled_y,
            model_scores,
            [0.5] * len(model_scores),
            probability_output=probability_output,
        )
        availability = pooled_availability_by_model.get(name, [True] * len(y))
        available_indices = [index for index, value in enumerate(availability) if value]
        unavailable_patients = {
            pooled_subjects[index]
            for index, value in enumerate(availability)
            if not value
        }
        complete_case = None
        if available_indices:
            complete_case_values = evaluate_with_thresholds(
                [pooled_y[index] for index in available_indices],
                [model_scores[index] for index in available_indices],
                [pooled_thresholds_by_model[name][index] for index in available_indices],
                probability_output=probability_output,
            )
            complete_case = _score_report(complete_case_values, probability_output)
        comparison.append(
            {
                "model": name,
                "prediction_output_type": (
                    "probability" if probability_output else "ranking_score"
                ),
                "probability_calibrated": bool(
                    benchmark_metadata.get(name, {}).get(
                        "probability_calibrated", False
                    )
                ),
                "calibration_method": benchmark_metadata.get(name, {}).get(
                    "calibration_method", "none"
                ),
                "calibration_training_scope": benchmark_metadata.get(name, {}).get(
                    "calibration_training_scope", "not_applicable"
                ),
                "score_range": benchmark_metadata.get(name, {}).get(
                    "score_range", [0.0, 1.0]
                ),
                "risk_direction": "higher_score_higher_predicted_risk",
                "auroc": inner_threshold_metrics["auroc"],
                "auprc": inner_threshold_metrics["auprc"],
                "brier_score": (
                    inner_threshold_metrics["brier_score"]
                    if probability_output
                    else None
                ),
                "log_loss": (
                    inner_threshold_metrics["log_loss"]
                    if probability_output
                    else None
                ),
                "inner_selected_fold_thresholds": {
                    key: inner_threshold_metrics[key]
                    for key in ("sensitivity", "specificity", "ppv", "npv", "f1")
                },
                "threshold_0.5_descriptive": {
                    key: descriptive_metrics[key]
                    for key in ("sensitivity", "specificity", "ppv", "npv", "f1")
                },
                "threshold_policy": inner_threshold_metrics["threshold_policy"],
                "availability_analysis": {
                    "primary_strategy": "neutral_risk_0.5",
                    "availability_indicator_reported": True,
                    "calculable_windows": len(available_indices),
                    "uncalculable_windows": len(y) - len(available_indices),
                    "patients_with_uncalculable_windows": len(unavailable_patients),
                    "complete_case_metrics": complete_case,
                },
                "number_of_patients": len(unique_subjects),
                "number_of_windows": len(y),
            }
        )
    bootstrap = patient_bootstrap(
        pooled_subjects,
        pooled_y,
        dict(pooled_scores_by_model),
        {name: 0.5 for name in pooled_scores_by_model},
        bootstrap_replicates,
        seed,
        reference_model="constant_prevalence",
        probability_models=probability_models,
    )
    for row in comparison:
        row["bootstrap_ci"] = bootstrap["models"][row["model"]]
    paired = paired_patient_bootstrap(
        pooled_subjects,
        pooled_y,
        dict(pooled_scores_by_model),
        "nested_ml_strategy",
        probability_models,
        bootstrap_replicates,
        seed,
    )
    return {
        "evaluation_name": "internal_nested_cross_validation",
        "evaluation_role": "internal_validation",
        "confirmatory_test": False,
        "selection_scope": "inner_patient_grouped_folds",
        "resampling_unit": "patient",
        "outer_folds": outer_folds,
        "inner_folds": inner_folds,
        "patients": len(unique_subjects),
        "windows": len(y),
        "each_patient_assigned_to_one_outer_fold": True,
        "each_window_predicted_once_out_of_fold": True,
        "patient_overlap_between_outer_folds": 0,
        "oof_prediction_count": len(window_prediction_counts),
        "model_selection_status": "not_final",
        "final_threshold_status": "not_frozen",
        "threshold_note": (
            "Each outer fold uses its inner-CV threshold. Pooled threshold-0.5 "
            "metrics are descriptive; no single final threshold exists."
        ),
        "constant_prevalence_note": (
            "Each fold uses its own training prevalence. Within-fold scores are "
            "constant, but pooled AUROC can differ from 0.5 because fold-specific "
            "prevalences are combined; pooled AUROC is not discrimination evidence."
        ),
        "folds": fold_records,
        "pooled_metrics_at_descriptive_0_5": pooled,
        "development_model_comparison": comparison,
        "patient_cluster_bootstrap": bootstrap,
        "paired_patient_bootstrap_vs_nested_ml": paired,
    }
