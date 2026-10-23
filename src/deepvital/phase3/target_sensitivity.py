from typing import Any

from deepvital.evaluation.metrics import evaluate_with_thresholds
from deepvital.phase3.implementation import OOFResult

TARGET_THRESHOLD_KEY = "sensitivity_0.8"


def summarize_target_sensitivity(
    result: OOFResult,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    records_by_fold = {
        int(record["outer_fold"]): record
        for record in result.fold_records
    }

    row_folds = [
        int(manifest["patient_assignments"][subject]["outer_fold"])
        for subject in result.subjects
    ]

    candidate_thresholds = [
        float(
            records_by_fold[fold]["candidate_threshold"][
                TARGET_THRESHOLD_KEY
            ]
        )
        for fold in row_folds
    ]

    benchmark_thresholds = [
        float(
            records_by_fold[fold]["benchmark_threshold"][
                TARGET_THRESHOLD_KEY
            ]
        )
        for fold in row_folds
    ]

    candidate_metrics = evaluate_with_thresholds(
        result.labels,
        result.raw_candidate,
        candidate_thresholds,
        probability_output=True,
    )

    benchmark_metrics = evaluate_with_thresholds(
        result.labels,
        result.benchmark,
        benchmark_thresholds,
        probability_output=False,
    )

    fold_results = []

    for fold in sorted(records_by_fold):
        indices = [
            index
            for index, row_fold in enumerate(row_folds)
            if row_fold == fold
        ]

        candidate_fold_threshold = candidate_thresholds[indices[0]]
        benchmark_fold_threshold = benchmark_thresholds[indices[0]]

        fold_results.append(
            {
                "outer_fold": fold,
                "patients": len(
                    {result.subjects[index] for index in indices}
                ),
                "windows": len(indices),
                "positive_windows": sum(
                    result.labels[index] for index in indices
                ),
                "candidate_threshold": candidate_fold_threshold,
                "benchmark_threshold": benchmark_fold_threshold,
                "candidate_metrics": evaluate_with_thresholds(
                    [result.labels[index] for index in indices],
                    [result.raw_candidate[index] for index in indices],
                    [candidate_fold_threshold] * len(indices),
                    probability_output=True,
                ),
                "benchmark_metrics": evaluate_with_thresholds(
                    [result.labels[index] for index in indices],
                    [result.benchmark[index] for index in indices],
                    [benchmark_fold_threshold] * len(indices),
                    probability_output=False,
                ),
            }
        )

    return {
        "analysis_role": (
            "post_hoc_reviewer_requested_internal_validation"
        ),
        "target_sensitivity": 0.80,
        "threshold_selection": (
            "inner_oof_predictions_from_outer_training_patients_only"
        ),
        "evaluation": "corresponding_outer_fold_only",
        "patients": len(set(result.subjects)),
        "windows": len(result.labels),
        "positive_windows": sum(result.labels),
        "candidate_metrics": candidate_metrics,
        "benchmark_metrics": benchmark_metrics,
        "folds": fold_results,
    }
