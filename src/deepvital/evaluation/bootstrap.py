"""Deterministic patient-cluster bootstrap utilities."""

from __future__ import annotations

import math
import random
from collections import defaultdict

from .metrics import evaluate_probabilities


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
) -> dict:
    """Return patient-cluster confidence intervals and paired metric differences."""
    rng = random.Random(seed)
    metrics = ("auroc", "auprc", "brier_score")
    draws = {name: {metric: [] for metric in metrics} for name in predictions}
    differences = {
        name: {metric: [] for metric in metrics}
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
            values = evaluate_probabilities(
                sample_y,
                [scores[i] for i in indices],
                thresholds.get(name, 0.5),
            )
            sample_metrics[name] = values
            for metric in metrics:
                draws[name][metric].append(values[metric])
        for name in differences:
            for metric in metrics:
                differences[name][metric].append(
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
