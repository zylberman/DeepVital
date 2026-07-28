"""Phase 1B hourly dataset and future-label build orchestration."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from deepvital.features.windows import build_stay_windows, window_columns
from deepvital.preprocessing.hourly import (
    aggregate_stay_hourly,
    hourly_columns,
    stream_canonical_stays,
)
from deepvital.splitting.patient_split import (
    aggregate_split_summary,
    assert_patient_disjoint,
    assign_patient_splits,
)


def assert_accounting_identities(
    counts: dict[str, int], variable_count: int
) -> dict[str, bool]:
    """Fail fast when Phase 1B cohort accounting does not reconcile."""
    identities = {
        "hourly_cell_partition": counts["hourly_rows"] * variable_count
        == counts["hourly_observed_cells"]
        + counts["forward_filled_cells"]
        + counts["unfilled_missing_cells"],
        "candidate_window_partition": counts["candidate_windows"]
        == counts["windows_created"]
        + counts["windows_excluded_incomplete_future_map"]
        + counts.get("windows_excluded_minimum_observed_data", 0),
        "label_partition": counts["windows_created"]
        == counts["positive_windows"] + counts["negative_windows"],
    }
    failed = [name for name, passed in identities.items() if not passed]
    if failed:
        raise ValueError(f"Phase 1B accounting identity failed: {', '.join(failed)}")
    return identities


def build_phase_1b_dataset(
    canonical_path: Path,
    hourly_output: Path,
    windows_output: Path,
    quality_report: Path,
    config: dict[str, Any],
    splitting_config: dict[str, Any] | None = None,
    split_manifest: Path | None = None,
    split_report: Path | None = None,
) -> dict[str, Any]:
    """Build private CSV artifacts and an aggregate-only quality report."""
    variables = list(config["variables"])
    outcome = config["outcome"]
    hourly_output.parent.mkdir(parents=True, exist_ok=True)
    windows_output.parent.mkdir(parents=True, exist_ok=True)
    quality_report.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    patient_tokens: set[str] = set()
    admission_tokens: set[str] = set()
    stay_count = 0
    all_window_rows: list[dict[str, Any]] = []

    with hourly_output.open("w", encoding="utf-8", newline="") as hourly_handle:
        hourly_writer = csv.DictWriter(
            hourly_handle, fieldnames=hourly_columns(variables)
        )
        hourly_writer.writeheader()

        for stay in stream_canonical_stays(canonical_path):
            stay_count += 1
            patient_tokens.add(stay.subject_id)
            admission_tokens.add(stay.hadm_id)
            hourly_rows, hourly_quality = aggregate_stay_hourly(
                stay, variables, config["forward_fill_max_hours"]
            )
            hourly_writer.writerows(hourly_rows)
            counts.update(
                {
                    key: value
                    for key, value in hourly_quality.items()
                    if key != "variable_counts"
                }
            )
            windows, window_quality = build_stay_windows(
                hourly_rows=hourly_rows,
                variables=variables,
                input_hours=config["input_window_hours"],
                horizon_hours=config["prediction_horizon_hours"],
                map_variable=outcome["variable"],
                threshold=outcome["threshold"],
                consecutive_hours=outcome["consecutive_hours"],
                require_complete_future_map=outcome[
                    "require_complete_future_map"
                ],
            )
            window_rows = list(windows)
            all_window_rows.extend(window_rows)
            counts.update(window_quality)

    split_summary = None
    if splitting_config is not None:
        assignments = assign_patient_splits(
            patient_tokens,
            splitting_config["proportions"],
            splitting_config["seed"],
        )
        for row in all_window_rows:
            row["split"] = assignments[row["subject_id"]]
        assert_patient_disjoint(all_window_rows)
        split_summary = aggregate_split_summary(all_window_rows)
        assigned_counts = Counter(assignments.values())
        for split, summary in split_summary.items():
            summary["patients_with_windows"] = summary["patients"]
            summary["patients"] = assigned_counts[split]
        if split_manifest is None or split_report is None:
            raise ValueError("Split manifest and aggregate split report are required")
        split_manifest.parent.mkdir(parents=True, exist_ok=True)
        split_manifest.write_text(
            json.dumps(
                {
                    "seed": splitting_config["seed"],
                    "proportions": splitting_config["proportions"],
                    "patient_assignments": assignments,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        split_report.parent.mkdir(parents=True, exist_ok=True)
        split_report.write_text(
            json.dumps(
                {
                    "seed": splitting_config["seed"],
                    "proportions": splitting_config["proportions"],
                    "patient_overlap_count": 0,
                    "splits": split_summary,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    with windows_output.open("w", encoding="utf-8", newline="") as windows_handle:
        windows_writer = csv.DictWriter(
            windows_handle,
            fieldnames=window_columns(variables, config["input_window_hours"]),
        )
        windows_writer.writeheader()
        windows_writer.writerows(all_window_rows)

    windows_created = counts["windows_created"]
    identities = assert_accounting_identities(counts, len(variables))
    report = {
        "configuration": {
            "hourly_aggregation": config["hourly_aggregation"],
            "forward_fill_max_hours": config["forward_fill_max_hours"],
            "input_window_hours": config["input_window_hours"],
            "prediction_horizon_hours": config["prediction_horizon_hours"],
            "map_threshold": outcome["threshold"],
            "consecutive_low_map_hours": outcome["consecutive_hours"],
            "require_complete_future_map": outcome["require_complete_future_map"],
        },
        "entities": {
            "patients": len(patient_tokens),
            "hospital_admissions": len(admission_tokens),
            "icu_stays": stay_count,
        },
        "counts": dict(sorted(counts.items())),
        "accounting_identities": identities,
        "event_prevalence": (
            counts["positive_windows"] / windows_created if windows_created else None
        ),
    }
    if split_summary is not None:
        report["patient_splitting"] = {
            "seed": splitting_config["seed"],
            "patient_overlap_count": 0,
            "assigned_patients": sum(
                summary["patients"] for summary in split_summary.values()
            ),
        }
    quality_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
