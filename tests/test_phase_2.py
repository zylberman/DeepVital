"""Synthetic-only checks for Phase 2 leakage controls and evaluation logic."""

from __future__ import annotations

import math
import random
from pathlib import Path

from deepvital.evaluation.bootstrap import (
    patient_bootstrap,
    patient_equal_weights,
    resample_patient_indices,
)
from deepvital.evaluation.calibration import (
    calibration_curve,
    calibration_intercept_slope,
)
from deepvital.evaluation.metrics import (
    average_precision,
    evaluate_probabilities,
    roc_auc,
    select_thresholds,
)
from deepvital.models.clinical_baselines import predict_clinical_benchmarks, safe_ratio
from deepvital.models.pipelines import FORBIDDEN, candidate_feature_names
from scripts.train_baseline_models import select_model

CONFIG = {
    "risk_center_map": 65,
    "risk_scale_map": 10,
    "fixed_map_thresholds": [60, 65, 70],
    "shock_index_center": 0.7,
    "shock_index_scale": 0.15,
    "modified_shock_index_center": 0.9,
    "modified_shock_index_scale": 0.2,
}


def test_candidate_features_exclude_identifiers_label_and_future():
    fields = list(FORBIDDEN) + [
        "heart_rate_current",
        "heart_rate_h0_missing",
        "mean_arterial_pressure_future",
    ]
    selected = candidate_feature_names(fields)
    assert selected == ["heart_rate_current", "heart_rate_h0_missing"]


def test_clinical_risk_increases_as_current_map_falls():
    low = predict_clinical_benchmarks({"mean_arterial_pressure_current": "55"}, 0.2, CONFIG)
    high = predict_clinical_benchmarks({"mean_arterial_pressure_current": "85"}, 0.2, CONFIG)
    assert low["last_map"] > high["last_map"]


def test_fixed_map_benchmarks_are_explicit():
    result = predict_clinical_benchmarks({"mean_arterial_pressure_current": "64"}, 0.2, CONFIG)
    assert result["map_threshold_60"] == 0
    assert result["map_threshold_65"] == 1


def test_modified_shock_index_invalid_denominator_is_missing_neutral():
    result = predict_clinical_benchmarks(
        {"heart_rate_current": "90", "mean_arterial_pressure_current": "0"}, 0.2, CONFIG
    )
    assert result["modified_shock_index"] == 0.5
    assert safe_ratio(90, 0) is None


def test_map_rolling_benchmarks_only_read_historical_tags():
    row = {
        "mean_arterial_pressure_hm2_value": "70",
        "mean_arterial_pressure_hm1_value": "60",
        "mean_arterial_pressure_h0_value": "50",
        "mean_arterial_pressure_hp1_value": "5",
    }
    result = predict_clinical_benchmarks(row, 0.2, CONFIG)
    expected = 1 / (1 + math.exp(-(65 - 50) / 10))
    assert result["map_min_3h"] == expected


def test_auc_and_average_precision_perfect():
    assert roc_auc([0, 1], [0.1, 0.9]) == 1
    assert average_precision([0, 1], [0.1, 0.9]) == 1


def test_average_precision_for_constant_score_equals_prevalence():
    assert average_precision([0, 0, 0, 1], [0.2, 0.2, 0.2, 0.2]) == 0.25


def test_metrics_confusion_accounting():
    result = evaluate_probabilities([0, 0, 1, 1], [0.1, 0.8, 0.2, 0.9], 0.5)
    assert result["tp"] + result["fp"] + result["tn"] + result["fn"] == 4
    assert result["sensitivity"] == result["specificity"] == 0.5


def test_threshold_selection_has_all_protocol_thresholds():
    result = select_thresholds([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9], 0.8)
    assert set(result) == {"fixed_0.5", "youden", "sensitivity_0.8"}


def test_patient_resampling_keeps_all_windows_for_each_draw():
    subjects = ["a", "a", "b", "b", "b"]
    indices = resample_patient_indices(subjects, random.Random(2))
    for subject in set(subjects):
        included = [i for i in indices if subjects[i] == subject]
        assert len(included) % subjects.count(subject) == 0


def test_patient_bootstrap_is_deterministic_and_records_rejections():
    args = (["a", "a", "b", "b"], [0, 1, 0, 1], {"last_map": [0.1, 0.9, 0.2, 0.8]}, {"last_map": 0.5})
    first = patient_bootstrap(*args, replicates=10, seed=7)
    second = patient_bootstrap(*args, replicates=10, seed=7)
    assert first == second
    assert first["valid_replicates"] + first["rejected_single_class_replicates"] == 10


def test_patient_equal_weights_give_each_patient_equal_total():
    subjects = ["a", "a", "b"]
    weights = patient_equal_weights(subjects)
    assert sum(weights[:2]) == weights[2] == 1


def test_calibration_curve_contains_only_aggregates():
    curve = calibration_curve([0, 1, 1], [0.1, 0.7, 0.9], bins=5)
    assert all(set(row) == {"bin", "count", "mean_predicted", "observed"} for row in curve)


def test_calibration_fit_returns_finite_values():
    intercept, slope = calibration_intercept_slope(
        [0, 0, 1, 1], [0.1, 0.3, 0.7, 0.9]
    )
    assert math.isfinite(intercept) and math.isfinite(slope)


def test_bootstrap_summary_contains_no_individual_identifiers():
    result = patient_bootstrap(
        ["synthetic-a", "synthetic-a", "synthetic-b", "synthetic-b"],
        [0, 1, 0, 1],
        {"last_map": [0.1, 0.8, 0.2, 0.9]},
        {"last_map": 0.5},
        5,
        3,
    )
    text = str(result)
    assert "synthetic-a" not in text and "synthetic-b" not in text


def test_model_selection_uses_validation_metrics_and_deterministic_name_tie_break():
    validation = {
        "z_model": {"auprc": 0.7, "brier_score": 0.2},
        "a_model": {"auprc": 0.7, "brier_score": 0.2},
        "better_brier": {"auprc": 0.7, "brier_score": 0.1},
    }
    assert select_model(validation, "auprc", "brier_score") == "better_brier"
    del validation["better_brier"]
    assert select_model(validation, "auprc", "brier_score") == "a_model"


def test_locked_threshold_is_applied_unchanged_to_test_probabilities():
    validation_threshold = select_thresholds([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])[
        "youden"
    ]
    result = evaluate_probabilities([0, 1], [0.4, 0.6], validation_threshold)
    assert result["threshold"] == validation_threshold


def test_expected_phase_2_reports_have_aggregate_schemas():
    root = Path(__file__).resolve().parents[1]
    expected_headers = {
        "reports/validation_metrics.csv": {"split", "model", "threshold_name", "auprc"},
        "reports/test_metrics.csv": {"split", "model", "threshold_name", "auprc"},
        "reports/model_comparison.csv": {"model", "selected", "auprc"},
        "reports/windows_per_patient.csv": {"split", "statistic", "value"},
    }
    import csv

    for relative_path, required in expected_headers.items():
        with (root / relative_path).open(newline="", encoding="utf-8") as handle:
            header = set(next(csv.reader(handle)))
        assert required <= header
