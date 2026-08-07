#!/usr/bin/env python3
"""Run development-only patient-grouped nested cross-validation."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepvital.evaluation.nested_cv import grouped_nested_cross_validation
from deepvital.models.baseline_models import build_baseline_models
from deepvital.models.clinical_baselines import (
    clinical_benchmark_availability,
    predict_clinical_benchmarks,
)
from deepvital.models.pipelines import candidate_feature_names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports/internal_nested_cross_validation.json",
    )
    parser.add_argument(
        "--comparison-output",
        type=Path,
        default=ROOT / "reports/internal_nested_model_comparison.csv",
    )
    parser.add_argument(
        "--paired-comparison-output",
        type=Path,
        default=ROOT / "reports/internal_nested_paired_comparisons.csv",
    )
    parser.add_argument("--outer-folds", type=int, default=5)
    parser.add_argument("--inner-folds", type=int, default=3)
    args = parser.parse_args()
    config = json.loads(
        (ROOT / "configs/modeling_baselines.yaml").read_text(encoding="utf-8")
    )
    with args.dataset.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        features = candidate_feature_names(reader.fieldnames or [])
        rows = list(reader)
    x = [
        [float(row[name]) if row.get(name, "") not in {"", None} else math.nan for name in features]
        for row in rows
    ]
    y = [int(row["label"]) for row in rows]
    subjects = [row["subject_id"] for row in rows]
    specifications = [
        ("logistic_regression_c0.1", "logistic_regression", "C", 0.1),
        ("logistic_regression_c1.0", "logistic_regression", "C", 1.0),
        ("gaussian_nb_smoothing1e-10", "gaussian_naive_bayes", "var_smoothing", 1e-10),
        ("gaussian_nb_smoothing1e-9", "gaussian_naive_bayes", "var_smoothing", 1e-9),
        ("hist_gradient_boosting_lr0.03", "hist_gradient_boosting", "learning_rate", 0.03),
        ("hist_gradient_boosting_lr0.05", "hist_gradient_boosting", "learning_rate", 0.05),
    ]

    def factory(model_name: str, parameter: str, value: float):
        def build():
            candidate_config = copy.deepcopy(config)
            candidate_config["models"][model_name][parameter] = value
            key = "gaussian_nb" if model_name == "gaussian_naive_bayes" else model_name
            return build_baseline_models(
                candidate_config, candidate_config["random_seed"]
            )[key]

        return build

    factories = {
        name: factory(model_name, parameter, value)
        for name, model_name, parameter, value in specifications
    }
    clinical_names = (
        "constant_prevalence",
        "last_map",
        "map_mean_6h",
        "map_min_6h",
        "map_slope",
        "shock_index",
        "modified_shock_index",
    )

    def benchmark_provider(name: str):
        def score(train_indices, validation_indices):
            prevalence = sum(y[int(index)] for index in train_indices) / len(
                train_indices
            )
            scores = []
            availability = []
            for index in validation_indices:
                row = rows[int(index)]
                scores.append(
                    predict_clinical_benchmarks(
                        row, prevalence, config["clinical_benchmarks"]
                    )[name]
                )
                availability.append(clinical_benchmark_availability(row)[name])
            return scores, availability

        return score

    benchmarks = {name: benchmark_provider(name) for name in clinical_names}
    benchmark_metadata = {
        name: {
            "prediction_output_type": (
                "probability" if name == "constant_prevalence" else "ranking_score"
            ),
            "probability_calibrated": False,
            "calibration_method": "none",
            "calibration_training_scope": (
                "corresponding_training_fold_only"
                if name == "constant_prevalence"
                else "not_applicable"
            ),
            "score_range": [0.0, 1.0],
        }
        for name in clinical_names
    }
    report = grouped_nested_cross_validation(
        x,
        y,
        subjects,
        factories,
        benchmarks,
        benchmark_metadata,
        outer_folds=args.outer_folds,
        inner_folds=args.inner_folds,
        seed=config["random_seed"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    comparison_fields = [
        "model",
        "prediction_output_type",
        "probability_calibrated",
        "calibration_method",
        "calibration_training_scope",
        "auroc",
        "auprc",
        "brier_score",
        "log_loss",
        "sensitivity",
        "specificity",
        "ppv",
        "npv",
        "auroc_ci95",
        "auprc_ci95",
        "brier_score_ci95",
        "number_of_patients",
        "number_of_windows",
        "threshold_policy",
        "uncalculable_windows",
        "patients_with_uncalculable_windows",
    ]
    args.comparison_output.parent.mkdir(parents=True, exist_ok=True)
    with args.comparison_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=comparison_fields)
        writer.writeheader()
        for row in report["development_model_comparison"]:
            output_row = {key: row[key] for key in comparison_fields if key in row}
            output_row.update(
                {
                    key: row["inner_selected_fold_thresholds"][key]
                    for key in ("sensitivity", "specificity", "ppv", "npv")
                }
            )
            output_row["uncalculable_windows"] = row["availability_analysis"][
                "uncalculable_windows"
            ]
            output_row["patients_with_uncalculable_windows"] = row[
                "availability_analysis"
            ]["patients_with_uncalculable_windows"]
            for metric in ("auroc", "auprc", "brier_score"):
                interval = row["bootstrap_ci"].get(metric)
                output_row[f"{metric}_ci95"] = (
                    f"{interval['lower']:.6f}–{interval['upper']:.6f}"
                    if interval
                    else "not_applicable"
                )
            writer.writerow(output_row)
    paired_rows = report["paired_patient_bootstrap_vs_nested_ml"]
    with args.paired_comparison_output.open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(paired_rows[0]))
        writer.writeheader()
        writer.writerows(paired_rows)
    print(json.dumps({key: report[key] for key in ("evaluation_name", "patients", "windows")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
