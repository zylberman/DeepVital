#!/usr/bin/env python3
"""Fit Phase 2 baselines on train and lock selection using validation only."""

from __future__ import annotations

import json

try:
    from scripts.phase_2_common import (
        ROOT,
        phase_1b_gate,
        read_json,
        write_json,
        write_metrics,
    )
except ModuleNotFoundError:  # Direct execution places scripts/ on sys.path.
    from phase_2_common import ROOT, phase_1b_gate, read_json, write_json, write_metrics

from deepvital.evaluation.calibration import calibration_intercept_slope
from deepvital.evaluation.metrics import evaluate_probabilities, select_thresholds
from deepvital.models.baseline_models import build_baseline_models
from deepvital.models.clinical_baselines import predict_clinical_benchmarks
from deepvital.models.pipelines import load_split


def select_model(
    validation_metrics: dict[str, dict[str, float]],
    primary_metric: str,
    secondary_metric: str,
) -> str:
    """Select deterministically from validation metrics without reading test data."""
    if primary_metric not in {"auprc", "auroc"}:
        raise ValueError(f"Unsupported primary selection metric: {primary_metric}")
    if secondary_metric not in {"brier_score", "log_loss"}:
        raise ValueError(f"Unsupported secondary selection metric: {secondary_metric}")
    return min(
        validation_metrics,
        key=lambda name: (
            -validation_metrics[name][primary_metric],
            validation_metrics[name][secondary_metric],
            name,
        ),
    )


def main() -> int:
    import joblib

    prior_lock_path = ROOT / "models/baselines/model_selection.json"
    prior_test_evaluations = 0
    if prior_lock_path.exists():
        prior = read_json(prior_lock_path)
        prior_test_evaluations = int(prior.get("test_evaluation_count", prior.get("test_accessed") is True))
    gate = phase_1b_gate()
    model_config = read_json(ROOT / "configs/modeling_baselines.yaml")
    evaluation_config = read_json(ROOT / "configs/evaluation.yaml")
    dataset = ROOT / "data/processed/modeling_windows.csv"
    x_train, y_train, features, _train_rows = load_split(dataset, "train")
    x_validation, y_validation, validation_features, validation_rows = load_split(dataset, "validation")
    assert features == validation_features
    prevalence = sum(y_train) / len(y_train)
    predictions: dict[str, list[float]] = {}
    models = build_baseline_models(model_config, model_config["random_seed"])
    model_dir = ROOT / "models/baselines"
    model_dir.mkdir(parents=True, exist_ok=True)
    for name, model in models.items():
        model.fit(x_train, y_train)
        predictions[name] = model.predict_proba(x_validation)[:, 1].tolist()
        joblib.dump(model, model_dir / f"{name}.joblib")
    for row in validation_rows:
        for name, value in predict_clinical_benchmarks(
            row, prevalence, model_config["clinical_benchmarks"]
        ).items():
            predictions.setdefault(name, []).append(value)

    threshold_map = {
        name: select_thresholds(
            y_validation, scores, evaluation_config["thresholds"]["target_sensitivity"]
        )
        for name, scores in predictions.items()
    }
    metric_rows = []
    selection_metrics = {}
    for name, scores in predictions.items():
        calibration = calibration_intercept_slope(y_validation, scores)
        base = evaluate_probabilities(y_validation, scores)
        selection_metrics[name] = base
        for threshold_name, threshold in threshold_map[name].items():
            values = evaluate_probabilities(y_validation, scores, threshold)
            values.update(
                {
                    "split": "validation",
                    "model": name,
                    "threshold_name": threshold_name,
                    "calibration_intercept": calibration[0],
                    "calibration_slope": calibration[1],
                }
            )
            metric_rows.append(
                {key: values[key] for key in ("split", "model", "threshold_name", "threshold", "prevalence", "auroc", "auprc", "brier_score", "log_loss", "calibration_intercept", "calibration_slope", "sensitivity", "specificity", "ppv", "npv", "f1", "tp", "fp", "tn", "fn")}
            )
    primary_metric = evaluation_config["primary_model_selection_metric"]
    secondary_metric = evaluation_config["secondary_model_selection_metric"]
    selected = select_model(selection_metrics, primary_metric, secondary_metric)
    simple_names = {
        name
        for name in selection_metrics
        if name.startswith("map_") or name == "last_map"
    }
    simple_map = select_model(
        {name: selection_metrics[name] for name in simple_names},
        primary_metric,
        secondary_metric,
    )
    lock = {
        "dataset_name": "development_holdout_v1",
        "evaluation_role": "development",
        "confirmatory_holdout": False,
        "status": "locked_before_test",
        "phase_1b_gate": gate,
        "random_seed": model_config["random_seed"],
        "train_windows": len(y_train),
        "validation_windows": len(y_validation),
        "training_prevalence": prevalence,
        "feature_count": len(features),
        "feature_names": features,
        "selected_model": selected,
        "best_simple_map_benchmark": simple_map,
        "selection_rule": (
            f"highest validation {primary_metric.upper()}, then lowest "
            f"{secondary_metric}, then model name"
        ),
        "thresholds": threshold_map,
        "test_accessed": False,
        "test_evaluation_count": prior_test_evaluations,
    }
    write_metrics(ROOT / "reports/validation_metrics.csv", metric_rows)
    write_json(ROOT / "reports/thresholds.json", threshold_map)
    write_json(model_dir / "model_selection.json", lock)
    (ROOT / "docs/MODEL_SELECTION.md").write_text(
        "# Phase 2 model selection lock\n\n"
        "This record was created from train and validation only, before test evaluation.\n\n"
        f"- Selected model: `{selected}`\n"
        f"- Best simple MAP benchmark: `{simple_map}`\n"
        f"- Predictors: {len(features)} prespecified current/trailing features\n"
        "- Rule: highest validation AUPRC, then lowest Brier score, then model name.\n"
        "- Thresholds: fixed 0.5, validation Youden index, and validation target sensitivity near 0.80.\n"
        "- Imputation/scaling: fitted within each applicable training pipeline only.\n"
        "- Test set: not read by this command.\n",
        encoding="utf-8",
    )
    print(json.dumps({"gate": gate["status"], "selected_model": selected, "validation_windows": len(y_validation)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
