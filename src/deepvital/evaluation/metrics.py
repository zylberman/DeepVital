"""Dependency-free binary discrimination and threshold metrics."""

from __future__ import annotations

import math
from collections.abc import Sequence


def _weighted_pairs(
    y: Sequence[int], p: Sequence[float], weights: Sequence[float] | None
) -> list[tuple[int, float, float]]:
    w = weights or [1.0] * len(y)
    return [(int(a), float(b), float(c)) for a, b, c in zip(y, p, w)]


def roc_auc(y: Sequence[int], p: Sequence[float], weights=None) -> float:
    rows = _weighted_pairs(y, p, weights)
    positive_weight = sum(w for label, _, w in rows if label == 1)
    negative_weight = sum(w for label, _, w in rows if label == 0)
    denom = positive_weight * negative_weight
    if not denom:
        return math.nan
    wins = negative_below = 0.0
    ordered = sorted(rows, key=lambda item: item[1])
    index = 0
    while index < len(ordered):
        end = index
        tied_positive = tied_negative = 0.0
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            label, _, weight = ordered[end]
            tied_positive += weight if label else 0.0
            tied_negative += weight if not label else 0.0
            end += 1
        wins += tied_positive * (negative_below + 0.5 * tied_negative)
        negative_below += tied_negative
        index = end
    return wins / denom


def average_precision(y: Sequence[int], p: Sequence[float], weights=None) -> float:
    rows = sorted(_weighted_pairs(y, p, weights), key=lambda x: x[1], reverse=True)
    total_positive = sum(w for label, _, w in rows if label == 1)
    if not total_positive:
        return math.nan
    tp = fp = result = 0.0
    index = 0
    while index < len(rows):
        end = index
        added_positive = added_negative = 0.0
        while end < len(rows) and rows[end][1] == rows[index][1]:
            label, _, weight = rows[end]
            added_positive += weight if label else 0.0
            added_negative += weight if not label else 0.0
            end += 1
        tp += added_positive
        fp += added_negative
        result += added_positive * tp / (tp + fp)
        index = end
    return result / total_positive


def evaluate_probabilities(y, p, threshold: float = 0.5, weights=None) -> dict[str, float]:
    rows = _weighted_pairs(y, p, weights)
    total_w = sum(w for _, _, w in rows)
    positive_w = sum(w for label, _, w in rows if label)
    eps = 1e-6
    tp = fp = tn = fn = 0.0
    for label, score, weight in rows:
        predicted = score >= threshold
        if label and predicted:
            tp += weight
        elif label:
            fn += weight
        elif predicted:
            fp += weight
        else:
            tn += weight
    divide = lambda a, b: a / b if b else math.nan
    brier = sum(w * (score - label) ** 2 for label, score, w in rows) / total_w
    log_loss = -sum(
        w
        * (
            label * math.log(min(max(score, eps), 1 - eps))
            + (1 - label) * math.log(min(max(1 - score, eps), 1 - eps))
        )
        for label, score, w in rows
    ) / total_w
    precision, recall = divide(tp, tp + fp), divide(tp, tp + fn)
    return {
        "prevalence": divide(positive_w, total_w),
        "auroc": roc_auc(y, p, weights),
        "auprc": average_precision(y, p, weights),
        "brier_score": brier,
        "log_loss": log_loss,
        "threshold": threshold,
        "sensitivity": recall,
        "specificity": divide(tn, tn + fp),
        "ppv": precision,
        "npv": divide(tn, tn + fn),
        "f1": divide(2 * precision * recall, precision + recall),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def evaluate_with_thresholds(
    y, p, thresholds, *, probability_output: bool = True
) -> dict[str, float]:
    """Evaluate scores using one preregistered threshold per observation.

    Discrimination and probability metrics use the original scores. Classification
    metrics use fold-specific thresholds selected without the evaluated fold.
    """
    if not (len(y) == len(p) == len(thresholds)):
        raise ValueError("Labels, probabilities, and thresholds must align")
    result = (
        evaluate_probabilities(y, p, 0.5)
        if probability_output
        else {
            "prevalence": sum(int(value) for value in y) / len(y),
            "auroc": roc_auc(y, p),
            "auprc": average_precision(y, p),
        }
    )
    tp = fp = tn = fn = 0.0
    for label, score, threshold in zip(y, p, thresholds):
        predicted = float(score) >= float(threshold)
        if label and predicted:
            tp += 1
        elif label:
            fn += 1
        elif predicted:
            fp += 1
        else:
            tn += 1
    divide = lambda numerator, denominator: (
        numerator / denominator if denominator else math.nan
    )
    sensitivity = divide(tp, tp + fn)
    specificity = divide(tn, tn + fp)
    ppv = divide(tp, tp + fp)
    npv = divide(tn, tn + fn)
    result.update(
        {
            "threshold": None,
            "threshold_policy": "fold_specific_inner_cv",
            "sensitivity": sensitivity,
            "specificity": specificity,
            "ppv": ppv,
            "npv": npv,
            "f1": divide(2 * ppv * sensitivity, ppv + sensitivity),
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        }
    )
    return result


def select_thresholds(y, p, target_sensitivity: float = 0.8) -> dict[str, float]:
    candidates = sorted({float(value) for value in p}, reverse=True)
    candidates = [1.0 + 1e-12] + candidates + [0.0]
    def threshold_stats(threshold):
        tp = sum(label == 1 and score >= threshold for label, score in zip(y, p))
        fn = sum(label == 1 and score < threshold for label, score in zip(y, p))
        tn = sum(label == 0 and score < threshold for label, score in zip(y, p))
        fp = sum(label == 0 and score >= threshold for label, score in zip(y, p))
        return {
            "sensitivity": tp / (tp + fn) if tp + fn else math.nan,
            "specificity": tn / (tn + fp) if tn + fp else math.nan,
        }
    evaluated = [(t, threshold_stats(t)) for t in candidates]
    youden = max(
        evaluated,
        key=lambda item: item[1]["sensitivity"] + item[1]["specificity"] - 1,
    )[0]
    eligible = [item for item in evaluated if item[1]["sensitivity"] >= target_sensitivity]
    sensitivity = max(eligible, key=lambda item: (item[1]["specificity"], item[0]))[0]
    return {"fixed_0.5": 0.5, "youden": youden, "sensitivity_0.8": sensitivity}
