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
from deepvital.models.pipelines import candidate_feature_names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports/internal_nested_cross_validation.json",
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
    report = grouped_nested_cross_validation(
        x,
        y,
        subjects,
        factories,
        outer_folds=args.outer_folds,
        inner_folds=args.inner_folds,
        seed=config["random_seed"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in ("evaluation_name", "patients", "windows")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
