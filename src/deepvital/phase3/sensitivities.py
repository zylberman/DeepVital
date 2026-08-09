"""Frozen Phase 3 sensitivity definitions, independent of canonical data access."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from statistics import mean
from typing import Any

from deepvital.phase3.prefreeze import (
    BP_SOURCE_CODES,
    future_map_label_bounds,
    raw_map_mean_6h,
)

MAP_THRESHOLDS = (60.0, 65.0, 70.0)
CONSECUTIVE_HOURS = (1, 2, 3)
BP_SOURCE_ALTERNATIVES = ("invasive_preferred", "non_invasive_only")
BENCHMARK_MISSINGNESS_POLICIES = ("neutral_score_0.5", "complete_case")
EVALUATION_WEIGHTING = ("window_weighted", "patient_equal")


def outcome_sensitivity_grid(
    future_map: Sequence[float | None], *, require_complete: bool = True
) -> dict[str, int | None]:
    """Apply the frozen strict 3x3 threshold/duration grid."""
    from deepvital.labeling.hypotension import sustained_hypotension_label

    return {
        f"map_lt_{int(threshold)}_{hours}_consecutive": sustained_hypotension_label(
            list(future_map),
            threshold=threshold,
            consecutive_hours=hours,
            require_complete=require_complete,
        )
        for threshold in MAP_THRESHOLDS
        for hours in CONSECUTIVE_HOURS
    }


def incomplete_future_map_sensitivity(
    future_map: Sequence[float | None], *, threshold: float, consecutive_hours: int
) -> dict[str, int]:
    """Return both prespecified incomplete-future-MAP identified bounds."""
    lower, upper = future_map_label_bounds(
        future_map,
        threshold=threshold,
        consecutive_hours=consecutive_hours,
    )
    return {"missing_as_not_low": lower, "missing_as_low": upper}


def select_bp_source_values(
    measurements: Sequence[Mapping[str, Any]], *, alternative: str, variable: str
) -> list[float]:
    """Select within-hour values under one frozen BP-source alternative."""
    if alternative not in BP_SOURCE_ALTERNATIVES:
        raise ValueError("Unapproved BP-source alternative")
    if variable not in {"systolic_bp", "mean_arterial_pressure"}:
        raise ValueError("BP-source sensitivity applies only to systolic BP and MAP")
    invasive_key = (
        "invasive_systolic_bp"
        if variable == "systolic_bp"
        else "invasive_mean_arterial_pressure"
    )
    non_invasive_key = (
        "non_invasive_systolic_bp"
        if variable == "systolic_bp"
        else "non_invasive_mean_arterial_pressure"
    )
    invasive = [
        float(row["value"])
        for row in measurements
        if str(row["code"]) in BP_SOURCE_CODES[invasive_key]
        and math.isfinite(float(row["value"]))
    ]
    non_invasive = [
        float(row["value"])
        for row in measurements
        if str(row["code"]) in BP_SOURCE_CODES[non_invasive_key]
        and math.isfinite(float(row["value"]))
    ]
    if alternative == "non_invasive_only":
        return non_invasive
    return invasive if invasive else non_invasive


def aggregate_bp_source_hour(
    measurements: Sequence[Mapping[str, Any]], *, alternative: str, variable: str
) -> float | None:
    """Apply the existing median aggregation after frozen source selection."""
    from statistics import median

    values = select_bp_source_values(
        measurements, alternative=alternative, variable=variable
    )
    return median(values) if values else None


def benchmark_missingness_indices(
    availability: Sequence[bool], policy: str
) -> list[int]:
    """Select all windows for neutral scoring or calculable complete cases only."""
    if policy not in BENCHMARK_MISSINGNESS_POLICIES:
        raise ValueError("Unapproved benchmark-missingness policy")
    return (
        list(range(len(availability)))
        if policy == "neutral_score_0.5"
        else [index for index, available in enumerate(availability) if available]
    )


def evaluation_weights(subjects: Sequence[str], policy: str) -> list[float]:
    """Return window weights under either frozen evaluation policy."""
    if policy not in EVALUATION_WEIGHTING:
        raise ValueError("Unapproved evaluation-weighting policy")
    if policy == "window_weighted":
        return [1.0] * len(subjects)
    counts = Counter(subjects)
    return [1.0 / counts[subject] for subject in subjects]


def missingness_charting_summary(
    rows: Sequence[Mapping[str, Any]], variables: Sequence[str]
) -> dict[str, Any]:
    """Return identifier-free descriptive missingness/charting summaries."""
    summaries: dict[str, Any] = {}
    for variable in variables:
        proportions = [
            float(row[f"{variable}_proportion_missing"])
            for row in rows
            if row.get(f"{variable}_proportion_missing") not in (None, "")
        ]
        current_missing = [
            int(row[f"{variable}_h0_missing"])
            for row in rows
            if row.get(f"{variable}_h0_missing") not in (None, "")
        ]
        hours_since = [
            float(row[f"{variable}_hours_since_last_observation"])
            for row in rows
            if row.get(f"{variable}_hours_since_last_observation") not in (None, "")
        ]
        summaries[variable] = {
            "windows": len(rows),
            "mean_proportion_missing": mean(proportions) if proportions else None,
            "mean_observed_hours": (
                mean(12.0 * (1.0 - value) for value in proportions)
                if proportions
                else None
            ),
            "current_missing_windows": sum(current_missing),
            "mean_hours_since_last_observation": (
                mean(hours_since) if hours_since else None
            ),
        }
    return summaries


def missingness_charting_report(
    rows: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    variables: Sequence[str],
) -> dict[str, Any]:
    """Summarize charting by registered outer fold and outcome without identifiers."""
    assignments = manifest["patient_assignments"]
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for outer_fold in range(1, 6):
        for outcome in (0, 1):
            key = f"outer_fold_{outer_fold}_outcome_{outcome}"
            groups[key] = [
                row
                for row in rows
                if int(assignments[str(row["subject_id"])]["outer_fold"])
                == outer_fold
                and int(row["label"]) == outcome
            ]
    windows_per_patient = Counter(str(row["subject_id"]) for row in rows)
    window_counts = list(windows_per_patient.values())
    measurement_columns = [
        f"{variable}_{tag}_measurement_count"
        for variable in variables
        for tag in (
            "hm11",
            "hm10",
            "hm9",
            "hm8",
            "hm7",
            "hm6",
            "hm5",
            "hm4",
            "hm3",
            "hm2",
            "hm1",
            "h0",
        )
    ]
    measurement_values = [
        float(row[column])
        for row in rows
        for column in measurement_columns
        if row.get(column) not in (None, "")
    ]
    return {
        "by_outer_fold_and_outcome": {
            key: missingness_charting_summary(group, variables)
            for key, group in groups.items()
        },
        "measurements_per_patient_hour_mean": (
            mean(measurement_values) if measurement_values else None
        ),
        "unavailable_map_mean_6h_windows": sum(
            raw_map_mean_6h(row) is None for row in rows
        ),
        "windows_per_patient": {
            "minimum": min(window_counts) if window_counts else None,
            "mean": mean(window_counts) if window_counts else None,
            "maximum": max(window_counts) if window_counts else None,
        },
    }


def frozen_sensitivity_definitions() -> dict[str, Any]:
    """Expose the complete closed sensitivity registry for report validation."""
    return {
        "outcome_grid": [
            {"map_threshold": threshold, "consecutive_hours": hours}
            for threshold in MAP_THRESHOLDS
            for hours in CONSECUTIVE_HOURS
        ],
        "incomplete_future_map": ["missing_as_not_low", "missing_as_low"],
        "bp_source_alternatives": list(BP_SOURCE_ALTERNATIVES),
        "benchmark_missingness": list(BENCHMARK_MISSINGNESS_POLICIES),
        "evaluation_weighting": list(EVALUATION_WEIGHTING),
        "missingness_charting_frequency": True,
    }
