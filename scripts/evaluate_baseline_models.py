#!/usr/bin/env python3
"""Apply validation-locked models and thresholds to the developmental holdout."""

from __future__ import annotations

import json

from phase_2_common import (
    ROOT,
    patient_window_distribution,
    read_json,
    write_json,
    write_metrics,
)

from deepvital.evaluation.bootstrap import patient_bootstrap, patient_equal_weights
from deepvital.evaluation.calibration import (
    calibration_curve,
    calibration_intercept_slope,
)
from deepvital.evaluation.metrics import evaluate_probabilities
from deepvital.evaluation.plotting import line_plot
from deepvital.models.clinical_baselines import predict_clinical_benchmarks
from deepvital.models.pipelines import load_split


def _curve(y, p, kind):
    thresholds = sorted(set(p), reverse=True)
    points = []
    for threshold in thresholds:
        m = evaluate_probabilities(y, p, threshold)
        points.append(
            (1 - m["specificity"], m["sensitivity"])
            if kind == "roc"
            else (m["sensitivity"], m["ppv"])
        )
    return points


def main() -> int:
    import joblib

    model_config = read_json(ROOT / "configs/modeling_baselines.yaml")
    evaluation = read_json(ROOT / "configs/evaluation.yaml")
    lock = read_json(ROOT / "models/baselines/model_selection.json")
    # Selection has already happened on validation data. This command only applies
    # the locked candidates and thresholds to the developmental holdout.
    assert lock["status"] == "locked_before_test" and lock["test_accessed"] is False
    dataset = ROOT / "data/processed/modeling_windows.csv"
    x_test, y_test, features, test_rows = load_split(dataset, "test")
    assert features == lock["feature_names"]
    predictions = {}
    for model_path in sorted((ROOT / "models/baselines").glob("*.joblib")):
        model = joblib.load(model_path)
        predictions[model_path.stem] = model.predict_proba(x_test)[:, 1].tolist()
    for row in test_rows:
        for name, value in predict_clinical_benchmarks(
            row, lock["training_prevalence"], model_config["clinical_benchmarks"]
        ).items():
            predictions.setdefault(name, []).append(value)
    metric_rows, comparison_rows = [], []
    weights = patient_equal_weights([row["subject_id"] for row in test_rows])
    for name, scores in predictions.items():
        calibration = calibration_intercept_slope(y_test, scores)
        for threshold_name, threshold in lock["thresholds"][name].items():
            values = evaluate_probabilities(y_test, scores, threshold)
            values.update({"split": "test", "model": name, "threshold_name": threshold_name, "calibration_intercept": calibration[0], "calibration_slope": calibration[1]})
            metric_rows.append({key: values[key] for key in ("split", "model", "threshold_name", "threshold", "prevalence", "auroc", "auprc", "brier_score", "log_loss", "calibration_intercept", "calibration_slope", "sensitivity", "specificity", "ppv", "npv", "f1", "tp", "fp", "tn", "fn")})
        standard = evaluate_probabilities(y_test, scores, lock["thresholds"][name]["youden"])
        equal = evaluate_probabilities(y_test, scores, lock["thresholds"][name]["youden"], weights)
        comparison_rows.append({
            "model": name,
            "selected": name == lock["selected_model"],
            "reference": name == lock["best_simple_map_benchmark"],
            "auroc": standard["auroc"],
            "auprc": standard["auprc"],
            "brier_score": standard["brier_score"],
            "patient_equal_weight_auroc": equal["auroc"],
            "patient_equal_weight_auprc": equal["auprc"],
            "patient_equal_weight_brier_score": equal["brier_score"],
        })
    write_metrics(ROOT / "reports/test_metrics.csv", metric_rows)
    write_metrics(ROOT / "reports/model_comparison.csv", comparison_rows)
    write_metrics(ROOT / "reports/windows_per_patient.csv", patient_window_distribution(test_rows, "test"))
    # Resample patients, not windows. Treating overlapping windows as independent
    # would make the resulting intervals look more precise than the cohort allows.
    bootstrap = patient_bootstrap(
        [row["subject_id"] for row in test_rows],
        y_test,
        predictions,
        {name: lock["thresholds"][name]["youden"] for name in predictions},
        evaluation["bootstrap"]["replicates"],
        evaluation["bootstrap"]["seed"],
        evaluation["bootstrap"]["confidence_level"],
        lock["best_simple_map_benchmark"],
    )
    write_json(ROOT / "reports/bootstrap_summary.json", bootstrap)
    figures = ROOT / "reports/figures"
    selected_names = list(dict.fromkeys([lock["selected_model"], lock["best_simple_map_benchmark"], "constant_prevalence"]))
    line_plot(figures / "roc_curves.png", [_curve(y_test, predictions[name], "roc") for name in selected_names])
    line_plot(figures / "precision_recall_curves.png", [_curve(y_test, predictions[name], "pr") for name in selected_names])
    line_plot(figures / "calibration_curves.png", [[(point["mean_predicted"], point["observed"]) for point in calibration_curve(y_test, predictions[name], evaluation["calibration_bins"])] for name in selected_names])
    line_plot(figures / "risk_distribution.png", [[(i / max(len(values) - 1, 1), value) for i, value in enumerate(sorted(predictions[name]))] for name in selected_names])
    line_plot(figures / "decision_thresholds.png", [[(i / 100, evaluate_probabilities(y_test, predictions[lock["selected_model"]], i / 100)["sensitivity"]) for i in range(101)], [(i / 100, evaluate_probabilities(y_test, predictions[lock["selected_model"]], i / 100)["specificity"]) for i in range(101)]])
    lock["test_accessed"] = True
    lock["status"] = "test_evaluated"
    lock["test_evaluation_count"] = int(lock.get("test_evaluation_count", 0)) + 1
    lock["test_windows"] = len(y_test)
    lock["test_evaluation_status"] = (
        "completed_once"
        if lock["test_evaluation_count"] == 1
        else "rerun_after_metric_correction"
    )
    write_json(ROOT / "models/baselines/model_selection.json", lock)
    print(json.dumps({"selected_model": lock["selected_model"], "test_windows": len(y_test), "bootstrap_valid": bootstrap["valid_replicates"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
