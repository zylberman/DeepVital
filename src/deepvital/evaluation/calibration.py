"""Calibration slope/intercept and reliability curve summaries."""

from __future__ import annotations

import math


def calibration_intercept_slope(y, p) -> tuple[float, float]:
    x = [math.log(min(max(v, 1e-6), 1 - 1e-6) / (1 - min(max(v, 1e-6), 1 - 1e-6))) for v in p]
    a, b = 0.0, 1.0
    for _ in range(30):
        q = [1 / (1 + math.exp(-max(min(a + b * value, 700), -700))) for value in x]
        g0 = sum(label - pred for label, pred in zip(y, q))
        g1 = sum((label - pred) * value for label, pred, value in zip(y, q, x))
        # A tiny ridge keeps the descriptive fit finite under perfect separation.
        h00 = -sum(pred * (1 - pred) for pred in q) - 1e-6
        h01 = -sum(pred * (1 - pred) * value for pred, value in zip(q, x))
        h11 = -sum(pred * (1 - pred) * value * value for pred, value in zip(q, x)) - 1e-6
        determinant = h00 * h11 - h01 * h01
        if abs(determinant) < 1e-12:
            return math.nan, math.nan
        da = (h11 * g0 - h01 * g1) / determinant
        db = (-h01 * g0 + h00 * g1) / determinant
        a = max(min(a - da, 100.0), -100.0)
        b = max(min(b - db, 100.0), -100.0)
        if max(abs(da), abs(db)) < 1e-8:
            break
    return a, b


def calibration_curve(y, p, bins: int = 10) -> list[dict[str, float]]:
    result = []
    for index in range(bins):
        lo, hi = index / bins, (index + 1) / bins
        members = [(a, b) for a, b in zip(y, p) if lo <= b <= hi if index == bins - 1 or b < hi]
        if members:
            result.append({"bin": index, "count": len(members), "mean_predicted": sum(v for _, v in members) / len(members), "observed": sum(a for a, _ in members) / len(members)})
    return result
