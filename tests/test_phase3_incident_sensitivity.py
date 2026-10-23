from __future__ import annotations

import pytest

from deepvital.phase3.implementation import OOFResult
from deepvital.phase3.incident_sensitivity import (
    RECENT_MAP_TAGS,
    cohort_masks,
    evaluate_oof_subset,
    recent_hypotension_flags,
    summarize_recent_hypotension,
)


def synthetic_row(
    *,
    label: int,
    current_map: float = 70.0,
    previous_map: float = 70.0,
) -> dict[str, object]:
    row: dict[str, object] = {
        "subject_id": f"synthetic-{label}-{current_map}-{previous_map}",
        "label": label,
    }

    for tag in RECENT_MAP_TAGS:
        row[f"mean_arterial_pressure_{tag}_value"] = 70.0
        row[f"mean_arterial_pressure_{tag}_observed"] = 1

    row["mean_arterial_pressure_hm1_value"] = previous_map
    row["mean_arterial_pressure_h0_value"] = current_map
    return row


def test_forward_filled_map_is_not_counted_as_observed_hypotension() -> None:
    row = synthetic_row(label=1, current_map=60.0)
    row["mean_arterial_pressure_h0_observed"] = 0

    flags = recent_hypotension_flags(row)

    assert flags["current_map_observed"] is False
    assert flags["current_hypotension"] is False
    assert flags["recent_hypotension"] is False
    assert flags["complete_recent_assessment"] is False


def test_map_equal_to_65_is_not_hypotension() -> None:
    row = synthetic_row(label=1, current_map=65.0)

    flags = recent_hypotension_flags(row)

    assert flags["current_hypotension"] is False
    assert flags["current_observed_normotension"] is True
    assert flags["no_observed_recent_hypotension"] is True


def test_positive_window_accounting_and_masks() -> None:
    rows = [
        synthetic_row(label=1, current_map=64.0),
        synthetic_row(label=1, current_map=70.0, previous_map=64.0),
        synthetic_row(label=1, current_map=70.0),
        synthetic_row(label=0, current_map=70.0),
    ]

    summary = summarize_recent_hypotension(rows)
    masks = cohort_masks(rows)

    assert summary["positive_windows"] == 3
    assert (
        summary[
            "positive_windows_with_current_observed_hypotension"
        ]
        == 1
    )
    assert (
        summary[
            "positive_windows_with_any_observed_hypotension_t_minus_5_to_t"
        ]
        == 2
    )
    assert masks["no_observed_recent_hypotension"] == [
        False,
        False,
        True,
        True,
    ]


def synthetic_oof_result() -> OOFResult:
    return OOFResult(
        labels=[0, 1, 0, 1, 0, 1, 0, 1],
        subjects=["a", "a", "b", "b", "c", "c", "d", "d"],
        raw_candidate=[0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6],
        calibrated_candidate=[
            0.1,
            0.9,
            0.2,
            0.8,
            0.3,
            0.7,
            0.4,
            0.6,
        ],
        benchmark=[0.4, 0.6, 0.7, 0.3, 0.2, 0.8, 0.5, 0.1],
        candidate_thresholds=[0.5] * 8,
        benchmark_thresholds=[0.5] * 8,
        fold_records=[],
    )


def test_subset_evaluation_is_reproducible() -> None:
    result = synthetic_oof_result()
    mask = [True] * len(result.labels)

    first = evaluate_oof_subset(
        result,
        mask,
        bootstrap_replicates=50,
        seed=20260726,
    )
    second = evaluate_oof_subset(
        result,
        mask,
        bootstrap_replicates=50,
        seed=20260726,
    )

    assert first == second
    assert first["number_of_patients"] == 4
    assert first["number_of_windows"] == 8
    assert set(first["paired_differences"]) == {
        "delta_auprc",
        "delta_auroc",
    }


def test_subset_evaluation_rejects_misaligned_mask() -> None:
    with pytest.raises(ValueError, match="does not align"):
        evaluate_oof_subset(
            synthetic_oof_result(),
            [True],
            bootstrap_replicates=10,
        )
