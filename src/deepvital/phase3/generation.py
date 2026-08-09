"""Deterministic private input generation for frozen Phase 3 sensitivities."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from deepvital.features.windows import build_stay_windows, window_columns
from deepvital.phase3.prefreeze import BP_SOURCE_CODES
from deepvital.preprocessing.hourly import floor_hour, parse_utc
from deepvital.windows.builder import stream_hourly_stays

VARIABLES = (
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "diastolic_bp",
    "mean_arterial_pressure",
    "oxygen_saturation",
    "temperature",
    "oxygen_flow",
)
FUTURE_MAP_COLUMNS = tuple(f"future_map_h{hour}" for hour in range(1, 7))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def filter_bp_source_rows(
    rows: Sequence[Mapping[str, Any]], alternative: str
) -> list[dict[str, Any]]:
    """Apply the frozen BP source rule before within-hour median aggregation."""
    if alternative not in {"invasive_preferred", "non_invasive_only"}:
        raise ValueError("Unapproved BP-source alternative")
    invasive = {
        "systolic_bp": set(BP_SOURCE_CODES["invasive_systolic_bp"]),
        "mean_arterial_pressure": set(
            BP_SOURCE_CODES["invasive_mean_arterial_pressure"]
        ),
    }
    non_invasive = {
        "systolic_bp": set(BP_SOURCE_CODES["non_invasive_systolic_bp"]),
        "mean_arterial_pressure": set(
            BP_SOURCE_CODES["non_invasive_mean_arterial_pressure"]
        ),
    }
    grouped: defaultdict[tuple[str, str, str, str, str], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        variable = str(row["normalized_variable"])
        if variable not in invasive:
            passthrough.append(dict(row))
            continue
        hour = floor_hour(parse_utc(str(row["observation_time"]))).isoformat()
        key = (
            str(row["subject_id"]),
            str(row["hadm_id"]),
            str(row["stay_id"]),
            hour,
            variable,
        )
        grouped[key].append(row)
    selected = list(passthrough)
    for key in sorted(grouped):
        variable = key[-1]
        candidates = grouped[key]
        invasive_rows = [
            row for row in candidates if str(row["observation_code"]) in invasive[variable]
        ]
        non_invasive_rows = [
            row
            for row in candidates
            if str(row["observation_code"]) in non_invasive[variable]
        ]
        chosen = (
            non_invasive_rows
            if alternative == "non_invasive_only"
            else invasive_rows or non_invasive_rows
        )
        selected.extend(dict(row) for row in chosen)
    return sorted(
        selected,
        key=lambda row: (
            str(row["subject_id"]),
            str(row["hadm_id"]),
            str(row["stay_id"]),
            str(row["observation_time"]),
            str(row["observation_code"]),
            float(row["numeric_value"]),
        ),
    )


def write_canonical_rows_exclusively(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write a deterministic private canonical variant without overwriting it."""
    if not rows:
        raise ValueError("Cannot write an empty canonical BP-source variant")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_phase3_sensitivity_windows(
    hourly_input: Path,
    output: Path,
    *,
    include_incomplete_future_map: bool,
    config_root: Path,
) -> None:
    """Build deterministic eligible windows and optionally retain future MAP values."""
    windowing = _read_json(config_root / "windowing.yaml")
    labeling = _read_json(config_root / "labeling.yaml")
    missingness = _read_json(config_root / "missingness.yaml")
    rows: list[dict[str, Any]] = []
    for hourly_rows in stream_hourly_stays(hourly_input):
        windows, _ = build_stay_windows(
            hourly_rows,
            list(VARIABLES),
            input_hours=windowing["observation_window_hours"],
            horizon_hours=windowing["prediction_horizon_hours"],
            map_variable=labeling["map_variable"],
            threshold=labeling["threshold"],
            consecutive_hours=labeling["consecutive_low_hours"],
            require_complete_future_map=not include_incomplete_future_map,
            minimum_total_observed_cells=missingness[
                "minimum_total_observed_cells_per_window"
            ],
            minimum_observed_hours_by_variable=missingness[
                "minimum_observed_hours_by_variable"
            ],
        )
        by_time = {str(row["hour"]): index for index, row in enumerate(hourly_rows)}
        for window in windows:
            if include_incomplete_future_map:
                prediction_index = by_time[str(window["prediction_time"])]
                for future_hour, column in enumerate(FUTURE_MAP_COLUMNS, start=1):
                    window[column] = hourly_rows[prediction_index + future_hour][
                        "mean_arterial_pressure_observed_value"
                    ]
            rows.append(window)
    fields = window_columns(list(VARIABLES), windowing["observation_window_hours"])
    if include_incomplete_future_map:
        fields.extend(FUTURE_MAP_COLUMNS)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_canonical_rows(path: Path) -> list[dict[str, str]]:
    """Read an authorized local canonical development table for deterministic filtering."""
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
