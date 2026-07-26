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


def build_phase_1b_dataset(
    canonical_path: Path,
    hourly_output: Path,
    windows_output: Path,
    quality_report: Path,
    config: dict[str, Any],
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

    with hourly_output.open("w", encoding="utf-8", newline="") as hourly_handle, (
        windows_output.open("w", encoding="utf-8", newline="")
    ) as windows_handle:
        hourly_writer = csv.DictWriter(
            hourly_handle, fieldnames=hourly_columns(variables)
        )
        windows_writer = csv.DictWriter(
            windows_handle,
            fieldnames=window_columns(variables, config["input_window_hours"]),
        )
        hourly_writer.writeheader()
        windows_writer.writeheader()

        for stay in stream_canonical_stays(canonical_path):
            stay_count += 1
            patient_tokens.add(stay.subject_id)
            admission_tokens.add(stay.hadm_id)
            hourly_rows, hourly_quality = aggregate_stay_hourly(
                stay, variables, config["forward_fill_max_hours"]
            )
            hourly_writer.writerows(hourly_rows)
            counts.update(hourly_quality)
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
            windows_writer.writerows(window_rows)
            counts.update(window_quality)

    windows_created = counts["windows_created"]
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
        "event_prevalence": (
            counts["positive_windows"] / windows_created if windows_created else None
        ),
    }
    quality_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
