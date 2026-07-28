"""Retrospective feature-window construction without future predictors."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from typing import Any

from deepvital.features.temporal import derived_features, trailing_features
from deepvital.labeling.hypotension import sustained_hypotension_label


def window_columns(variables: list[str], input_hours: int) -> list[str]:
    columns = [
        "window_id",
        "subject_id",
        "hadm_id",
        "stay_id",
        "prediction_time",
        "split",
        "label",
    ]
    for offset in range(-(input_hours - 1), 1):
        tag = f"m{abs(offset)}" if offset < 0 else "0"
        for variable in variables:
            columns.extend(
                [
                    f"{variable}_h{tag}_value",
                    f"{variable}_h{tag}_observed",
                    f"{variable}_h{tag}_measurement_count",
                    f"{variable}_h{tag}_missing",
                    f"{variable}_h{tag}_hours_since",
                    f"{variable}_h{tag}_forward_filled",
                ]
            )
    for variable in variables:
        columns.extend(
            [
                f"{variable}_current",
                f"{variable}_previous",
                f"{variable}_change",
                f"{variable}_rolling_mean",
                f"{variable}_rolling_median",
                f"{variable}_rolling_min",
                f"{variable}_rolling_max",
                f"{variable}_rolling_std",
                f"{variable}_rolling_slope",
                f"{variable}_observed_count",
                f"{variable}_proportion_missing",
                f"{variable}_hours_since_last_observation",
            ]
        )
    columns.extend(
        [
            "pulse_pressure",
            "pulse_pressure_missing",
            "shock_index",
            "shock_index_missing",
        ]
    )
    return columns


def build_stay_windows(
    hourly_rows: list[dict[str, Any]],
    variables: list[str],
    input_hours: int,
    horizon_hours: int,
    map_variable: str,
    threshold: float,
    consecutive_hours: int,
    require_complete_future_map: bool,
    minimum_total_observed_cells: int = 0,
    minimum_observed_hours_by_variable: dict[str, int] | None = None,
) -> tuple[Iterator[dict[str, Any]], dict[str, int]]:
    """Build windows entirely within one already-isolated ICU stay."""
    output: list[dict[str, Any]] = []
    candidate_count = 0
    incomplete_count = 0
    insufficient_observed_count = 0
    positive_count = 0
    minimum_by_variable = minimum_observed_hours_by_variable or {}
    first_prediction_index = input_hours - 1
    last_prediction_index = len(hourly_rows) - horizon_hours - 1

    for prediction_index in range(first_prediction_index, last_prediction_index + 1):
        candidate_count += 1
        future_map = [
            hourly_rows[prediction_index + future_offset][
                f"{map_variable}_observed_value"
            ]
            for future_offset in range(1, horizon_hours + 1)
        ]
        label = sustained_hypotension_label(
            future_map,
            threshold=threshold,
            consecutive_hours=consecutive_hours,
            require_complete=require_complete_future_map,
        )
        if label is None:
            incomplete_count += 1
            continue
        current = hourly_rows[prediction_index]
        history_start = prediction_index - input_hours + 1
        history = hourly_rows[history_start : prediction_index + 1]
        total_observed = sum(
            int(source.get(f"{variable}_observed", 1 - source[f"{variable}_missing"]))
            for source in history
            for variable in variables
        )
        observed_by_variable = {
            variable: sum(
                int(source.get(f"{variable}_observed", 1 - source[f"{variable}_missing"]))
                for source in history
            )
            for variable in variables
        }
        if total_observed < minimum_total_observed_cells or any(
            observed_by_variable.get(variable, 0) < minimum
            for variable, minimum in minimum_by_variable.items()
        ):
            insufficient_observed_count += 1
            continue
        window_key = "|".join(
            [
                current["subject_id"],
                current["hadm_id"],
                current["stay_id"],
                current["hour"],
            ]
        )
        row: dict[str, Any] = {
            "window_id": hashlib.sha256(window_key.encode("utf-8")).hexdigest(),
            "subject_id": current["subject_id"],
            "hadm_id": current["hadm_id"],
            "stay_id": current["stay_id"],
            "prediction_time": current["hour"],
            "split": "",
            "label": label,
        }
        for history_index in range(history_start, prediction_index + 1):
            offset = history_index - prediction_index
            tag = f"m{abs(offset)}" if offset < 0 else "0"
            source = hourly_rows[history_index]
            for variable in variables:
                row[f"{variable}_h{tag}_value"] = source[f"{variable}_value"]
                row[f"{variable}_h{tag}_observed"] = source.get(
                    f"{variable}_observed", 1 - source[f"{variable}_missing"]
                )
                row[f"{variable}_h{tag}_measurement_count"] = source.get(
                    f"{variable}_measurement_count",
                    1 - source[f"{variable}_missing"],
                )
                row[f"{variable}_h{tag}_missing"] = source[f"{variable}_missing"]
                row[f"{variable}_h{tag}_hours_since"] = source[
                    f"{variable}_hours_since"
                ]
                row[f"{variable}_h{tag}_forward_filled"] = source.get(
                    f"{variable}_forward_filled",
                    int(
                        source[f"{variable}_missing"] == 1
                        and source[f"{variable}_value"] is not None
                    ),
                )
        for variable in variables:
            row.update(trailing_features(history, variable))
        row.update(derived_features(current))
        output.append(row)
        positive_count += label

    return iter(output), {
        "candidate_windows": candidate_count,
        "prediction_times_excluded_insufficient_history": min(
            input_hours - 1, len(hourly_rows)
        ),
        "prediction_times_excluded_incomplete_future_horizon": min(
            horizon_hours, max(0, len(hourly_rows) - input_hours + 1)
        ),
        "windows_excluded_incomplete_future_map": incomplete_count,
        "windows_excluded_minimum_observed_data": insufficient_observed_count,
        "windows_created": len(output),
        "positive_windows": positive_count,
        "negative_windows": len(output) - positive_count,
    }
