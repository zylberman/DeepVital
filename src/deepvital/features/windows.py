"""Retrospective feature-window construction without future predictors."""

from __future__ import annotations

from typing import Any, Iterator

from deepvital.labeling.hypotension import sustained_hypotension_label


def window_columns(variables: list[str], input_hours: int) -> list[str]:
    columns = ["subject_id", "hadm_id", "stay_id", "prediction_time", "label"]
    for offset in range(-(input_hours - 1), 1):
        tag = f"m{abs(offset)}" if offset < 0 else "0"
        for variable in variables:
            columns.extend(
                [
                    f"{variable}_h{tag}_value",
                    f"{variable}_h{tag}_missing",
                    f"{variable}_h{tag}_hours_since",
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
) -> tuple[Iterator[dict[str, Any]], dict[str, int]]:
    """Build windows entirely within one already-isolated ICU stay."""
    output: list[dict[str, Any]] = []
    candidate_count = 0
    incomplete_count = 0
    positive_count = 0
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
        row: dict[str, Any] = {
            "subject_id": current["subject_id"],
            "hadm_id": current["hadm_id"],
            "stay_id": current["stay_id"],
            "prediction_time": current["hour"],
            "label": label,
        }
        history_start = prediction_index - input_hours + 1
        for history_index in range(history_start, prediction_index + 1):
            offset = history_index - prediction_index
            tag = f"m{abs(offset)}" if offset < 0 else "0"
            source = hourly_rows[history_index]
            for variable in variables:
                row[f"{variable}_h{tag}_value"] = source[f"{variable}_value"]
                row[f"{variable}_h{tag}_missing"] = source[f"{variable}_missing"]
                row[f"{variable}_h{tag}_hours_since"] = source[
                    f"{variable}_hours_since"
                ]
        output.append(row)
        positive_count += label

    return iter(output), {
        "candidate_windows": candidate_count,
        "windows_excluded_incomplete_future_map": incomplete_count,
        "windows_created": len(output),
        "positive_windows": positive_count,
    }
