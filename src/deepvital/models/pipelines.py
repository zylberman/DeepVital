"""Phase 2 feature loading and leakage guards."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable
from pathlib import Path

VITALS = (
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "diastolic_bp",
    "mean_arterial_pressure",
    "oxygen_saturation",
    "temperature",
    "oxygen_flow",
)
SUMMARY_SUFFIXES = (
    "current",
    "previous",
    "change",
    "rolling_mean",
    "rolling_median",
    "rolling_min",
    "rolling_max",
    "rolling_std",
    "rolling_slope",
    "observed_count",
    "proportion_missing",
    "hours_since_last_observation",
)
FORBIDDEN = {
    "window_id",
    "subject_id",
    "hadm_id",
    "stay_id",
    "prediction_time",
    "split",
    "label",
}


def candidate_feature_names(fieldnames: Iterable[str]) -> list[str]:
    """Select prespecified current/trailing predictors and exclude identifiers."""
    available = set(fieldnames)
    wanted = [f"{v}_{s}" for v in VITALS for s in SUMMARY_SUFFIXES]
    wanted += [
        f"{v}_h0_{s}"
        for v in VITALS
        for s in ("observed", "measurement_count", "missing", "hours_since", "forward_filled")
    ]
    wanted += ["pulse_pressure", "pulse_pressure_missing", "shock_index", "shock_index_missing"]
    selected = [name for name in wanted if name in available]
    assert not (set(selected) & FORBIDDEN)
    assert all("_future" not in name and "_hp" not in name for name in selected)
    return selected


def _float(value: str | None) -> float:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return math.nan
    return result if math.isfinite(result) else math.nan


def load_split(
    path: Path, split: str
) -> tuple[list[list[float]], list[int], list[str], list[dict[str, str]]]:
    """Stream the CSV and retain only one explicitly requested partition."""
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        features = candidate_feature_names(reader.fieldnames or [])
        for row in reader:
            if row["split"] == split:
                rows.append(row)
    matrix = [[_float(row.get(name)) for name in features] for row in rows]
    labels = [int(row["label"]) for row in rows]
    return matrix, labels, features, rows
