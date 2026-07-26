"""Closed trailing-window tabular features."""

from __future__ import annotations

import math
import statistics
from typing import Any


def _slope(values: list[float | None]) -> float | None:
    points = [(index, value) for index, value in enumerate(values) if value is not None]
    if len(points) < 2:
        return None
    mean_x = statistics.mean(point[0] for point in points)
    mean_y = statistics.mean(point[1] for point in points)
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    if denominator == 0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator


def trailing_features(history: list[dict[str, Any]], variable: str) -> dict[str, Any]:
    """Compute features from the supplied past-and-current history only."""
    values = [row[f"{variable}_value"] for row in history]
    real_values = [
        row[f"{variable}_observed_value"]
        for row in history
        if row[f"{variable}_observed_value"] is not None
    ]
    available = [value for value in values if value is not None]
    current = values[-1]
    previous = values[-2] if len(values) >= 2 else None
    change = (
        current - previous if current is not None and previous is not None else None
    )
    return {
        f"{variable}_current": current,
        f"{variable}_previous": previous,
        f"{variable}_change": change,
        f"{variable}_rolling_mean": (
            statistics.mean(available) if available else None
        ),
        f"{variable}_rolling_median": (
            statistics.median(available) if available else None
        ),
        f"{variable}_rolling_min": min(available) if available else None,
        f"{variable}_rolling_max": max(available) if available else None,
        f"{variable}_rolling_std": (
            statistics.stdev(available) if len(available) >= 2 else None
        ),
        f"{variable}_rolling_slope": _slope(values),
        f"{variable}_observed_count": len(real_values),
        f"{variable}_proportion_missing": 1.0 - len(real_values) / len(history),
        f"{variable}_hours_since_last_observation": history[-1][
            f"{variable}_hours_since"
        ],
    }


def derived_features(current: dict[str, Any]) -> dict[str, Any]:
    systolic = current.get("systolic_bp_value")
    diastolic = current.get("diastolic_bp_value")
    heart_rate = current.get("heart_rate_value")
    pulse_pressure = (
        systolic - diastolic
        if systolic is not None and diastolic is not None
        else None
    )
    shock_index = (
        heart_rate / systolic
        if heart_rate is not None and systolic is not None and systolic > 0
        else None
    )
    if shock_index is not None and not math.isfinite(shock_index):
        shock_index = None
    return {
        "pulse_pressure": pulse_pressure,
        "pulse_pressure_missing": int(pulse_pressure is None),
        "shock_index": shock_index,
        "shock_index_missing": int(shock_index is None),
    }
