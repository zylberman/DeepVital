from __future__ import annotations

import json
from dataclasses import replace

from deepvital.phase3.implementation import OOFResult
from deepvital.phase3.target_sensitivity import (
    summarize_target_sensitivity,
)


def synthetic_result() -> tuple[OOFResult, dict]:
    subjects = [
        "synthetic-a",
        "synthetic-a",
        "synthetic-b",
        "synthetic-b",
    ]

    result = OOFResult(
        labels=[1, 0, 1, 0],
        subjects=subjects,
        raw_candidate=[0.80, 0.40, 0.70, 0.20],
        calibrated_candidate=[0.80, 0.40, 0.70, 0.20],
        benchmark=[0.90, 0.30, 0.60, 0.10],
        candidate_thresholds=[0.50] * 4,
        benchmark_thresholds=[0.50] * 4,
        fold_records=[
            {
                "outer_fold": 1,
                "candidate_threshold": {
                    "youden": 0.50,
                    "sensitivity_0.8": 0.75,
                },
                "benchmark_threshold": {
                    "youden": 0.50,
                    "sensitivity_0.8": 0.85,
                },
            },
            {
                "outer_fold": 2,
                "candidate_threshold": {
                    "youden": 0.50,
                    "sensitivity_0.8": 0.65,
                },
                "benchmark_threshold": {
                    "youden": 0.50,
                    "sensitivity_0.8": 0.55,
                },
            },
        ],
    )

    manifest = {
        "patient_assignments": {
            "synthetic-a": {"outer_fold": 1},
            "synthetic-b": {"outer_fold": 2},
        }
    }

    return result, manifest


def test_thresholds_are_mapped_from_each_outer_fold() -> None:
    result, manifest = synthetic_result()

    report = summarize_target_sensitivity(result, manifest)

    assert report["folds"][0]["candidate_threshold"] == 0.75
    assert report["folds"][0]["benchmark_threshold"] == 0.85
    assert report["folds"][1]["candidate_threshold"] == 0.65
    assert report["folds"][1]["benchmark_threshold"] == 0.55


def test_aggregate_confusion_matrices_include_every_window() -> None:
    result, manifest = synthetic_result()

    report = summarize_target_sensitivity(result, manifest)

    for name in ("candidate_metrics", "benchmark_metrics"):
        metrics = report[name]
        evaluated = (
            metrics["tp"]
            + metrics["fp"]
            + metrics["tn"]
            + metrics["fn"]
        )
        assert evaluated == 4


def test_synthetic_example_has_expected_metrics() -> None:
    result, manifest = synthetic_result()

    report = summarize_target_sensitivity(result, manifest)

    assert report["candidate_metrics"]["sensitivity"] == 1.0
    assert report["candidate_metrics"]["specificity"] == 1.0
    assert report["benchmark_metrics"]["sensitivity"] == 1.0
    assert report["benchmark_metrics"]["specificity"] == 1.0


def test_report_is_reproducible() -> None:
    result, manifest = synthetic_result()

    first = summarize_target_sensitivity(result, manifest)
    second = summarize_target_sensitivity(result, manifest)

    assert first == second


def test_outer_labels_do_not_change_selected_thresholds() -> None:
    result, manifest = synthetic_result()

    original = summarize_target_sensitivity(result, manifest)
    changed_result = replace(result, labels=[0, 1, 0, 1])
    changed = summarize_target_sensitivity(changed_result, manifest)

    original_thresholds = [
        (
            fold["candidate_threshold"],
            fold["benchmark_threshold"],
        )
        for fold in original["folds"]
    ]
    changed_thresholds = [
        (
            fold["candidate_threshold"],
            fold["benchmark_threshold"],
        )
        for fold in changed["folds"]
    ]

    assert changed_thresholds == original_thresholds


def test_public_report_contains_no_patient_identifiers() -> None:
    result, manifest = synthetic_result()

    report_text = json.dumps(
        summarize_target_sensitivity(result, manifest)
    )

    assert "synthetic-a" not in report_text
    assert "synthetic-b" not in report_text
