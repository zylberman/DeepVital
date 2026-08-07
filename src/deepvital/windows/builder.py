"""Build labeled windows, patient splits, and aggregate-only reports."""

from __future__ import annotations

import csv
import json
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from deepvital.features.windows import build_stay_windows, window_columns
from deepvital.splitting.patient_split import (
    aggregate_split_summary,
    assert_patient_disjoint,
    assign_patient_splits,
)


def _parse_cell(value: str) -> Any:
    if value == "":
        return None
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def stream_hourly_stays(path: Path) -> Iterator[list[dict[str, Any]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        current_key: tuple[str, str, str] | None = None
        rows: list[dict[str, Any]] = []
        for raw in reader:
            text_fields = {"subject_id", "hadm_id", "stay_id", "hour"}
            row = {
                key: value if key in text_fields else _parse_cell(value)
                for key, value in raw.items()
            }
            key = (str(row["subject_id"]), str(row["hadm_id"]), str(row["stay_id"]))
            if current_key is not None and key != current_key:
                yield rows
                rows = []
            current_key = key
            rows.append(row)
        if rows:
            yield rows


def build_modeling_dataset(
    hourly_input: Path,
    windows_output: Path,
    split_manifest: Path,
    report_dir: Path,
    variables: list[str],
    missingness_config: dict[str, Any],
    windowing_config: dict[str, Any],
    labeling_config: dict[str, Any],
    splitting_config: dict[str, Any],
) -> dict[str, Any]:
    all_windows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    patients: set[str] = set()
    admissions: set[str] = set()
    stays = 0

    for hourly_rows in stream_hourly_stays(hourly_input.with_suffix(".csv")):
        stays += 1
        patients.add(str(hourly_rows[0]["subject_id"]))
        admissions.add(str(hourly_rows[0]["hadm_id"]))
        windows, quality = build_stay_windows(
            hourly_rows,
            variables,
            input_hours=windowing_config["observation_window_hours"],
            horizon_hours=windowing_config["prediction_horizon_hours"],
            map_variable=labeling_config["map_variable"],
            threshold=labeling_config["threshold"],
            consecutive_hours=labeling_config["consecutive_low_hours"],
            require_complete_future_map=labeling_config[
                "require_all_future_map_hours_observed"
            ],
            minimum_total_observed_cells=missingness_config[
                "minimum_total_observed_cells_per_window"
            ],
            minimum_observed_hours_by_variable=missingness_config[
                "minimum_observed_hours_by_variable"
            ],
        )
        all_windows.extend(windows)
        counts.update(quality)

    assignments = assign_patient_splits(
        patients,
        splitting_config["proportions"],
        splitting_config["seed"],
    )
    for row in all_windows:
        row["split"] = assignments[str(row["subject_id"])]
    assert_patient_disjoint(all_windows)
    split_summary = aggregate_split_summary(all_windows)
    assigned_counts = Counter(assignments.values())
    for split, summary in split_summary.items():
        summary["patients_with_windows"] = summary["patients"]
        summary["patients"] = assigned_counts[split]

    windows_output = windows_output.with_suffix(".csv")
    windows_output.parent.mkdir(parents=True, exist_ok=True)
    fields = window_columns(variables, windowing_config["observation_window_hours"])
    with windows_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_windows)

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

    report_dir.mkdir(parents=True, exist_ok=True)
    eligible = counts["windows_created"]
    label_distribution = {
        "positive": counts["positive_windows"],
        "negative": counts["negative_windows"],
        "total": eligible,
        "event_prevalence": (
            counts["positive_windows"] / eligible if eligible else None
        ),
    }
    exclusions = {
        "insufficient_12_hour_history": counts[
            "prediction_times_excluded_insufficient_history"
        ],
        "incomplete_future_horizon": counts[
            "prediction_times_excluded_incomplete_future_horizon"
        ],
        "insufficient_future_map_assessment": counts[
            "windows_excluded_incomplete_future_map"
        ],
        "minimum_observed_data": counts[
            "windows_excluded_minimum_observed_data"
        ],
        "prediction_time_outside_icu_period": 0,
        "invalid_or_missing_icu_key": 0,
        "label_indeterminate_other": 0,
    }
    windowing_quality = {
        "candidate_prediction_times": counts["candidate_windows"],
        "eligible_windows": eligible,
        "exclusions": exclusions,
        "sequence_representation": {
            "hours": windowing_config["observation_window_hours"],
            "ordering": "oldest_to_current",
            "future_predictor_columns": 0,
        },
    }
    cohort_flow = {
        "canonical_patients": len(patients),
        "canonical_admissions": len(admissions),
        "icu_stays_processed": stays,
        "candidate_prediction_times": counts["candidate_windows"],
        "eligible_windows": eligible,
        "positive_windows": counts["positive_windows"],
        "negative_windows": counts["negative_windows"],
        "event_prevalence": label_distribution["event_prevalence"],
        "exclusions": exclusions,
    }
    reports = {
        "windowing_quality.json": windowing_quality,
        "label_distribution.json": label_distribution,
        "cohort_flow.json": cohort_flow,
        "split_summary.json": {
            "seed": splitting_config["seed"],
            "proportions": splitting_config["proportions"],
            "splits": split_summary,
            "patient_overlap_count": 0,
        },
    }
    for filename, content in reports.items():
        (report_dir / filename).write_text(
            json.dumps(content, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {
        "counts": dict(counts),
        "label_distribution": label_distribution,
        "split_summary": split_summary,
        "cohort_flow": cohort_flow,
    }
