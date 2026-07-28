"""Transparent clinical scores computed only from the trailing predictor window."""

from __future__ import annotations

import math
from collections.abc import Mapping
from statistics import mean


def _number(row: Mapping[str, str], name: str) -> float | None:
    value = row.get(name, "")
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-min(value, 700.0)))
    exp_value = math.exp(max(value, -700.0))
    return exp_value / (1.0 + exp_value)


def safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Return a ratio, treating absent and non-positive denominators as missing."""
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _values(row: Mapping[str, str], variable: str, hours: int) -> list[float]:
    tags = [f"hm{i}" for i in range(hours - 1, 0, -1)] + ["h0"]
    return [
        value
        for tag in tags
        if (value := _number(row, f"{variable}_{tag}_value")) is not None
    ]


def predict_clinical_benchmarks(
    row: Mapping[str, str],
    training_prevalence: float,
    config: Mapping[str, float],
) -> dict[str, float]:
    """Return aggregate-safe risks; missing scores receive a neutral 0.5 risk."""
    center = float(config.get("risk_center_map", 65.0))
    scale = float(config.get("risk_scale_map", 10.0))
    current = _number(row, "mean_arterial_pressure_current")
    previous = _number(row, "mean_arterial_pressure_previous")
    change = _number(row, "mean_arterial_pressure_change")
    slope = _number(row, "mean_arterial_pressure_rolling_slope")
    map3, map6 = _values(row, "mean_arterial_pressure", 3), _values(
        row, "mean_arterial_pressure", 6
    )
    hr = _number(row, "heart_rate_current")
    sbp = _number(row, "systolic_bp_current")
    shock = safe_ratio(hr, sbp)
    modified = safe_ratio(hr, current)

    def low_map(value: float | None) -> float:
        return 0.5 if value is None else _sigmoid((center - value) / scale)

    predictions = {
        "constant_prevalence": float(training_prevalence),
        "last_map": low_map(current),
        "map_current": low_map(current),
        "map_previous": low_map(previous),
        "map_min_3h": low_map(min(map3) if map3 else None),
        "map_min_6h": low_map(min(map6) if map6 else None),
        "map_mean_3h": low_map(mean(map3) if map3 else None),
        "map_mean_6h": low_map(mean(map6) if map6 else None),
        "map_change": 0.5 if change is None else _sigmoid(-change / scale),
        "map_slope": 0.5 if slope is None else _sigmoid(-slope / scale),
        "shock_index": (
            0.5
            if shock is None
            else _sigmoid(
                (shock - float(config.get("shock_index_center", 0.7)))
                / float(config.get("shock_index_scale", 0.15))
            )
        ),
        "modified_shock_index": (
            0.5
            if modified is None
            else _sigmoid(
                (modified - float(config.get("modified_shock_index_center", 0.9)))
                / float(config.get("modified_shock_index_scale", 0.2))
            )
        ),
    }
    for threshold in config.get("fixed_map_thresholds", [60, 65, 70]):
        predictions[f"map_threshold_{int(threshold)}"] = float(
            current is not None and current < float(threshold)
        )
    return predictions
