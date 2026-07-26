"""Stay-bounded hourly aggregation and missing-data representation."""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def floor_hour(value: datetime) -> datetime:
    return value.replace(minute=0, second=0, microsecond=0)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class CanonicalStay:
    subject_id: str
    hadm_id: str
    stay_id: str
    rows: list[dict[str, str]]


def stream_canonical_stays(path: Path) -> Iterator[CanonicalStay]:
    """Stream a canonical CSV grouped by its deterministic stay ordering."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        current_key: tuple[str, str, str] | None = None
        rows: list[dict[str, str]] = []
        for row in reader:
            key = (row["subject_id"], row["hadm_id"], row["stay_id"])
            if current_key is not None and key != current_key:
                yield CanonicalStay(*current_key, rows)
                rows = []
            current_key = key
            rows.append(row)
        if current_key is not None:
            yield CanonicalStay(*current_key, rows)


def _hour_range(start: datetime, end: datetime) -> Iterator[datetime]:
    current = start
    while current <= end:
        yield current
        current += timedelta(hours=1)


def aggregate_stay_hourly(
    stay: CanonicalStay,
    variables: list[str],
    forward_fill_max_hours: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Aggregate by hourly median and add bounded forward-only missing-data fields."""
    grouped: defaultdict[tuple[datetime, str], list[float]] = defaultdict(list)
    for row in stay.rows:
        variable = row["normalized_variable"]
        if variable not in variables:
            continue
        hour = floor_hour(parse_utc(row["observation_time"]))
        grouped[(hour, variable)].append(float(row["normalized_value"]))
    if not grouped:
        return [], {"canonical_rows": len(stay.rows), "duplicate_values_collapsed": 0}

    start = min(hour for hour, _ in grouped)
    end = max(hour for hour, _ in grouped)
    last_real_value: dict[str, float] = {}
    last_real_hour: dict[str, datetime] = {}
    hourly_rows: list[dict[str, Any]] = []
    aggregated_cells = 0
    imputed_cells = 0
    missing_cells = 0

    for hour in _hour_range(start, end):
        output: dict[str, Any] = {
            "subject_id": stay.subject_id,
            "hadm_id": stay.hadm_id,
            "stay_id": stay.stay_id,
            "hour": utc_text(hour),
        }
        for variable in variables:
            values = grouped.get((hour, variable), [])
            observed_value: float | None
            if values:
                observed_value = float(statistics.median(values))
                last_real_value[variable] = observed_value
                last_real_hour[variable] = hour
                value = observed_value
                missing_indicator = 0
                hours_since: int | None = 0
                aggregated_cells += 1
            else:
                observed_value = None
                previous_hour = last_real_hour.get(variable)
                hours_since = (
                    int((hour - previous_hour).total_seconds() // 3600)
                    if previous_hour is not None
                    else None
                )
                if hours_since is not None and hours_since <= forward_fill_max_hours:
                    value = last_real_value[variable]
                    imputed_cells += 1
                else:
                    value = None
                    missing_cells += 1
                missing_indicator = 1
            output[f"{variable}_observed_value"] = observed_value
            output[f"{variable}_value"] = value
            output[f"{variable}_missing"] = missing_indicator
            output[f"{variable}_hours_since"] = hours_since
        hourly_rows.append(output)

    return hourly_rows, {
        "canonical_rows": len(stay.rows),
        "hourly_rows": len(hourly_rows),
        "hourly_observed_cells": aggregated_cells,
        "duplicate_values_collapsed": len(stay.rows) - aggregated_cells,
        "forward_filled_cells": imputed_cells,
        "unfilled_missing_cells": missing_cells,
    }


def hourly_columns(variables: list[str]) -> list[str]:
    columns = ["subject_id", "hadm_id", "stay_id", "hour"]
    for variable in variables:
        columns.extend(
            [
                f"{variable}_observed_value",
                f"{variable}_value",
                f"{variable}_missing",
                f"{variable}_hours_since",
            ]
        )
    return columns
