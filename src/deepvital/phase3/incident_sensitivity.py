"""Post-hoc sensitivity analysis excluding recent observed hypotension."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from deepvital.evaluation.bootstrap import paired_patient_bootstrap
from deepvital.evaluation.metrics import evaluate_with_thresholds
from deepvital.phase3.implementation import OOFResult
from deepvital.phase3.prefreeze import PHASE3_SEED

MAP_THRESHOLD = 65.0
RECENT_MAP_TAGS = ("hm5", "hm4", "hm3", "hm2", "hm1", "h0")


def observed_map_value(
    row: Mapping[str, Any],
    tag: str,
) -> float | None:
    """Return an hourly MAP only when it represents a real observation."""
    observed_column = f"mean_arterial_pressure_{tag}_observed"
    value_column = f"mean_arterial_pressure_{tag}_value"

    observed = str(row.get(observed_column, "")).strip().lower()
    if observed not in {"1", "1.0", "true"}:
        return None

    try:
        value = float(row.get(value_column, ""))
    except (TypeError, ValueError):
        return None

    return value if math.isfinite(value) else None


def recent_hypotension_flags(
    row: Mapping[str, Any],
    threshold: float = MAP_THRESHOLD,
) -> dict[str, bool | int]:
    """Classify current and recent observed hypotension without using future MAP."""
    current_map = observed_map_value(row, "h0")
    recent_maps = [
        value
        for tag in RECENT_MAP_TAGS
        if (value := observed_map_value(row, tag)) is not None
    ]

    current_hypotension = (
        current_map is not None and current_map < threshold
    )
    recent_hypotension = any(value < threshold for value in recent_maps)

    return {
        "current_map_observed": current_map is not None,
        "current_hypotension": current_hypotension,
        "recent_observation_count": len(recent_maps),
        "any_recent_map_observed": bool(recent_maps),
        "recent_hypotension": recent_hypotension,
        "complete_recent_assessment": len(recent_maps) == len(RECENT_MAP_TAGS),
        "current_observed_normotension": (
            current_map is not None and current_map >= threshold
        ),
        "no_observed_recent_hypotension": (
            bool(recent_maps) and not recent_hypotension
        ),
        "complete_recent_normotension": (
            len(recent_maps) == len(RECENT_MAP_TAGS)
            and not recent_hypotension
        ),
    }


def cohort_masks(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, list[bool]]:
    """Build reviewer-requested sensitivity cohorts."""
    flags = [recent_hypotension_flags(row) for row in rows]
    return {
        "current_observed_normotension": [
            bool(item["current_observed_normotension"]) for item in flags
        ],
        "no_observed_recent_hypotension": [
            bool(item["no_observed_recent_hypotension"]) for item in flags
        ],
        "complete_recent_normotension": [
            bool(item["complete_recent_normotension"]) for item in flags
        ],
    }


def summarize_recent_hypotension(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return aggregate-only accounting for the reviewer question."""
    flags = [recent_hypotension_flags(row) for row in rows]
    labels = [int(row["label"]) for row in rows]
    positive_indices = [
        index for index, label in enumerate(labels) if label == 1
    ]

    def positive_count(flag: str) -> int:
        return sum(
            bool(flags[index][flag])
            for index in positive_indices
        )

    return {
        "all_windows": len(rows),
        "positive_windows": len(positive_indices),
        "positive_windows_with_current_observed_hypotension": (
            positive_count("current_hypotension")
        ),
        "positive_windows_with_any_observed_hypotension_t_minus_5_to_t": (
            positive_count("recent_hypotension")
        ),
        "positive_windows_without_any_observed_map_t_minus_5_to_t": (
            sum(
                not bool(flags[index]["any_recent_map_observed"])
                for index in positive_indices
            )
        ),
        "positive_windows_with_complete_recent_map_assessment": (
            positive_count("complete_recent_assessment")
        ),
    }


def cohort_accounting(
    rows: Sequence[Mapping[str, Any]],
    masks: Mapping[str, Sequence[bool]],
) -> dict[str, dict[str, int | float]]:
    """Count windows, patients, and outcomes without exposing identifiers."""
    output: dict[str, dict[str, int | float]] = {}

    for name, mask in masks.items():
        if len(mask) != len(rows):
            raise ValueError("Cohort mask does not align with rows")

        indices = [index for index, keep in enumerate(mask) if keep]
        positives = sum(int(rows[index]["label"]) for index in indices)
        patients = {
            str(rows[index]["subject_id"])
            for index in indices
        }

        output[name] = {
            "number_of_windows": len(indices),
            "number_of_patients": len(patients),
            "positive_windows": positives,
            "prevalence": positives / len(indices) if indices else math.nan,
        }

    return output


def evaluate_oof_subset(
    result: OOFResult,
    mask: Sequence[bool],
    *,
    bootstrap_replicates: int = 1000,
    seed: int = PHASE3_SEED,
) -> dict[str, Any]:
    """Evaluate frozen OOF predictions after applying a post-hoc cohort mask."""
    if len(mask) != len(result.labels):
        raise ValueError("Cohort mask does not align with OOF predictions")

    indices = [index for index, keep in enumerate(mask) if keep]
    if not indices:
        raise ValueError("Sensitivity cohort is empty")

    labels = [result.labels[index] for index in indices]
    if set(labels) != {0, 1}:
        raise ValueError("Sensitivity cohort must contain both outcome classes")

    subjects = [result.subjects[index] for index in indices]
    candidate = [result.raw_candidate[index] for index in indices]
    benchmark = [result.benchmark[index] for index in indices]
    candidate_thresholds = [
        result.candidate_thresholds[index] for index in indices
    ]
    benchmark_thresholds = [
        result.benchmark_thresholds[index] for index in indices
    ]

    paired = paired_patient_bootstrap(
        subjects,
        labels,
        {
            "logistic_regression": candidate,
            "map_mean_6h": benchmark,
        },
        reference_model="map_mean_6h",
        probability_models={"logistic_regression"},
        replicates=bootstrap_replicates,
        seed=seed,
    )

    paired_by_metric = {
        str(row["metric"]): row
        for row in paired
    }

    return {
        "number_of_windows": len(indices),
        "number_of_patients": len(set(subjects)),
        "positive_windows": sum(labels),
        "prevalence": sum(labels) / len(labels),
        "candidate_metrics": evaluate_with_thresholds(
            labels,
            candidate,
            candidate_thresholds,
            probability_output=True,
        ),
        "benchmark_metrics": evaluate_with_thresholds(
            labels,
            benchmark,
            benchmark_thresholds,
            probability_output=False,
        ),
        "paired_differences": paired_by_metric,
    }
