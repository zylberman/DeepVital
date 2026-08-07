"""Deterministic patient-cluster bootstrap utilities."""

from __future__ import annotations

import math
import random
from collections import defaultdict

from .metrics import average_precision, evaluate_probabilities, roc_auc


def _applicable_score_metrics(y, scores, probability: bool) -> dict[str, float]:
    values = {"auroc": roc_auc(y, scores), "auprc": average_precision(y, scores)}
    if probability:
        probability_values = evaluate_probabilities(y, scores)
        values.update(
            {
                "brier_score": probability_values["brier_score"],
                "log_loss": probability_values["log_loss"],
            }
        )
    return values


def resample_patient_indices(subjects: list[str], rng: random.Random) -> list[int]:
    """Sample patients with replacement and include all their windows per draw."""
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, subject in enumerate(subjects):
        grouped[subject].append(index)
    patients = sorted(grouped)
    sampled = [rng.choice(patients) for _ in patients]
    return [index for patient in sampled for index in grouped[patient]]


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(v for v in values if math.isfinite(v))
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * probability
    lower, upper = int(position), min(int(position) + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def patient_bootstrap(
    subjects: list[str],
    y: list[int],
    predictions: dict[str, list[float]],
    thresholds: dict[str, float],
    replicates: int,
    seed: int,
    confidence: float = 0.95,
    reference_model: str = "last_map",
    probability_models: set[str] | None = None,
) -> dict:
    """Return patient-cluster confidence intervals and paired metric differences."""
    rng = random.Random(seed)
    probability_models = probability_models or set(predictions)
    model_metrics = {
        name: (
            ("auroc", "auprc", "brier_score", "log_loss")
            if name in probability_models
            else ("auroc", "auprc")
        )
        for name in predictions
    }
    draws = {
        name: {metric: [] for metric in model_metrics[name]} for name in predictions
    }
    differences = {
        name: {
            metric: []
            for metric in set(model_metrics[name]) & set(model_metrics[reference_model])
        }
        for name in predictions
        if name != reference_model and reference_model in predictions
    }
    valid = rejected = 0
    for _ in range(replicates):
        indices = resample_patient_indices(subjects, rng)
        sample_y = [y[i] for i in indices]
        if len(set(sample_y)) < 2:
            rejected += 1
            continue
        valid += 1
        sample_metrics = {}
        for name, scores in predictions.items():
            sample_scores = [scores[i] for i in indices]
            values = _applicable_score_metrics(
                sample_y, sample_scores, name in probability_models
            )
            sample_metrics[name] = values
            for metric in model_metrics[name]:
                draws[name][metric].append(values[metric])
        for name, metric_differences in differences.items():
            for metric in metric_differences:
                metric_differences[metric].append(
                    sample_metrics[name][metric] - sample_metrics[reference_model][metric]
                )
    alpha = (1 - confidence) / 2
    summarize = lambda values: {
        "lower": percentile(values, alpha),
        "median": percentile(values, 0.5),
        "upper": percentile(values, 1 - alpha),
    }
    return {
        "unit": "patient",
        "seed": seed,
        "requested_replicates": replicates,
        "valid_replicates": valid,
        "rejected_single_class_replicates": rejected,
        "confidence_level": confidence,
        "reference_model": reference_model,
        "models": {
            name: {metric: summarize(values) for metric, values in by_metric.items()}
            for name, by_metric in draws.items()
        },
        "paired_differences_vs_reference": {
            name: {metric: summarize(values) for metric, values in by_metric.items()}
            for name, by_metric in differences.items()
        },
    }


def patient_equal_weights(subjects: list[str]) -> list[float]:
    counts: dict[str, int] = defaultdict(int)
    for subject in subjects:
        counts[subject] += 1
    return [1.0 / counts[subject] for subject in subjects]


def paired_patient_bootstrap(
    subjects: list[str],
    y: list[int],
    predictions: dict[str, list[float]],
    reference_model: str,
    probability_models: set[str],
    replicates: int,
    seed: int,
    confidence: float = 0.95,
) -> list[dict[str, float | int | str | None]]:
    """Compare OOF scores on identical patient-cluster bootstrap samples."""
    if reference_model not in predictions:
        raise ValueError("Paired-bootstrap reference model is missing")
    metrics = ("auroc", "auprc", "brier_score", "log_loss")
    observed = {
        name: _applicable_score_metrics(y, scores, name in probability_models)
        for name, scores in predictions.items()
    }
    rng = random.Random(seed)
    differences: dict[tuple[str, str], list[float]] = {
        (name, metric): []
        for name in predictions
        if name != reference_model
        for metric in metrics
        if metric in {"auroc", "auprc"}
        or {name, reference_model} <= probability_models
    }
    for _ in range(replicates):
        indices = resample_patient_indices(subjects, rng)
        sample_y = [y[index] for index in indices]
        if len(set(sample_y)) < 2:
            continue
        reference = _applicable_score_metrics(
            sample_y,
            [predictions[reference_model][index] for index in indices],
            reference_model in probability_models,
        )
        for name in predictions:
            if name == reference_model:
                continue
            comparison = _applicable_score_metrics(
                sample_y,
                [predictions[name][index] for index in indices],
                name in probability_models,
            )
            for metric in metrics:
                key = (name, metric)
                if key in differences:
                    value = comparison[metric] - reference[metric]
                    if math.isfinite(value):
                        differences[key].append(value)
    alpha = (1 - confidence) / 2
    rows: list[dict[str, float | int | str | None]] = []
    for (name, metric), values in sorted(differences.items()):
        observed_difference = observed[name][metric] - observed[reference_model][metric]
        rows.append(
            {
                "comparison_model": name,
                "reference_model": reference_model,
                "metric": {
                    "auroc": "delta_auroc",
                    "auprc": "delta_auprc",
                    "brier_score": "delta_brier",
                    "log_loss": "delta_log_loss",
                }[metric],
                "observed_difference": observed_difference,
                "ci_95_lower": percentile(values, alpha),
                "ci_95_upper": percentile(values, 1 - alpha),
                "proportion_bootstrap_difference_above_zero": (
                    sum(value > 0 for value in values) / len(values) if values else None
                ),
                "number_of_valid_bootstraps": len(values),
                "difference_definition": "comparison_minus_reference",
                "favorable_direction": (
                    "positive" if metric in {"auroc", "auprc"} else "negative"
                ),
            }
        )
    return rows
