"""Scikit-learn baseline constructors with train-only preprocessing."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_baseline_models(config: Mapping[str, Any], seed: int) -> dict[str, Any]:
    """Build unfitted models with preprocessing enclosed in each pipeline.

    Keeping imputation and scaling beside the estimator makes it difficult to fit
    either transformation on validation or holdout rows by accident.
    """
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import GaussianNB
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    models = config["models"]
    return {
        "dummy_prevalence": DummyClassifier(strategy=models["dummy_prevalence"]["strategy"]),
        "logistic_regression": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=models["logistic_regression"]["C"],
                        class_weight=models["logistic_regression"]["class_weight"],
                        max_iter=models["logistic_regression"]["max_iter"],
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "gaussian_nb": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    GaussianNB(
                        var_smoothing=models["gaussian_naive_bayes"]["var_smoothing"]
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            learning_rate=models["hist_gradient_boosting"]["learning_rate"],
            max_iter=models["hist_gradient_boosting"]["max_iter"],
            max_leaf_nodes=models["hist_gradient_boosting"]["max_leaf_nodes"],
            l2_regularization=models["hist_gradient_boosting"]["l2_regularization"],
            class_weight=models["hist_gradient_boosting"].get("class_weight"),
            random_state=seed,
        ),
    }
