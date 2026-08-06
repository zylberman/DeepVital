"""Patient-grouped nested cross-validation for development-only evaluation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .bootstrap import patient_bootstrap
from .metrics import evaluate_probabilities, select_thresholds

EstimatorFactory = Callable[[], Any]


def grouped_nested_cross_validation(
    x: Sequence[Sequence[float]],
    y: Sequence[int],
    subjects: Sequence[str],
    candidates: Mapping[str, EstimatorFactory],
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
        candidate_records: dict[str, dict[str, Any]] = {}
        for name, factory in sorted(candidates.items()):
            inner_y: list[int] = []
            inner_scores: list[float] = []
            for inner_train_rel, inner_valid_rel in inner.split(
                x_array[outer_train], y_array[outer_train], train_groups
            ):
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
        for subject in set(valid_groups):
            patient_prediction_counts[str(subject)] += 1
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
            }
        )

    if set(patient_prediction_counts.values()) != {1}:
        raise AssertionError("Each patient must occur in exactly one outer fold")
    pooled = evaluate_probabilities(pooled_y, pooled_scores, 0.5)
    bootstrap = patient_bootstrap(
        pooled_subjects,
        pooled_y,
        {"nested_cv_oof": pooled_scores},
        {"nested_cv_oof": 0.5},
        bootstrap_replicates,
        seed,
        reference_model="nested_cv_oof",
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
        "each_patient_predicted_once": True,
        "folds": fold_records,
        "pooled_metrics_at_descriptive_0_5": pooled,
        "patient_cluster_bootstrap": bootstrap,
    }
