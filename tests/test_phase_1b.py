import csv
import json
from pathlib import Path

from deepvital.cohort.dataset import build_phase_1b_dataset
from deepvital.features.windows import build_stay_windows
from deepvital.labeling.hypotension import sustained_hypotension_label
from deepvital.preprocessing.hourly import CanonicalStay, aggregate_stay_hourly


VARIABLES = ["heart_rate", "mean_arterial_pressure"]
CONFIG = {
    "variables": VARIABLES,
    "hourly_aggregation": "median",
    "forward_fill_max_hours": 2,
    "input_window_hours": 12,
    "prediction_horizon_hours": 6,
    "outcome": {
        "variable": "mean_arterial_pressure",
        "threshold": 65.0,
        "consecutive_hours": 2,
        "require_complete_future_map": True,
    },
}


def _canonical_row(
    hour: int,
    variable: str,
    value: float,
    stay_id: str = "SYNTHETIC-STAY-A",
) -> dict[str, str]:
    return {
        "subject_id": "SYNTHETIC-SUBJECT",
        "hadm_id": "SYNTHETIC-HADM",
        "stay_id": stay_id,
        "observation_time": f"2020-01-01T{hour:02d}:15:00Z",
        "source_resource": "SyntheticObservation",
        "code_system": "https://synthetic.invalid",
        "observation_code": variable,
        "observation_display": variable,
        "normalized_variable": variable,
        "numeric_value": str(value),
        "original_unit": "synthetic-unit",
        "normalized_value": str(value),
        "normalized_unit": "synthetic-unit",
    }


def _hourly_rows(map_values: list[float | None]) -> list[dict]:
    rows = []
    for hour, map_value in enumerate(map_values):
        rows.append(
            {
                "subject_id": "SYNTHETIC-SUBJECT",
                "hadm_id": "SYNTHETIC-HADM",
                "stay_id": "SYNTHETIC-STAY",
                "hour": f"2020-01-{1 + hour // 24:02d}T{hour % 24:02d}:00:00Z",
                "heart_rate_observed_value": 80.0,
                "heart_rate_value": 80.0,
                "heart_rate_missing": 0,
                "heart_rate_hours_since": 0,
                "mean_arterial_pressure_observed_value": map_value,
                "mean_arterial_pressure_value": map_value,
                "mean_arterial_pressure_missing": int(map_value is None),
                "mean_arterial_pressure_hours_since": (
                    None if map_value is None else 0
                ),
            }
        )
    return rows


def test_hourly_median_and_duplicate_count() -> None:
    rows = [
        _canonical_row(0, "heart_rate", 70),
        _canonical_row(0, "heart_rate", 90),
        _canonical_row(0, "mean_arterial_pressure", 75),
    ]
    hourly, quality = aggregate_stay_hourly(
        CanonicalStay(
            "SYNTHETIC-SUBJECT", "SYNTHETIC-HADM", "SYNTHETIC-STAY-A", rows
        ),
        VARIABLES,
        2,
    )
    assert hourly[0]["heart_rate_observed_value"] == 80.0
    assert quality["duplicate_values_collapsed"] == 1


def test_forward_fill_is_limited_and_never_backward_fills() -> None:
    rows = [
        _canonical_row(1, "heart_rate", 80),
        _canonical_row(4, "heart_rate", 90),
        _canonical_row(0, "mean_arterial_pressure", 75),
        _canonical_row(4, "mean_arterial_pressure", 75),
    ]
    hourly, _ = aggregate_stay_hourly(
        CanonicalStay(
            "SYNTHETIC-SUBJECT", "SYNTHETIC-HADM", "SYNTHETIC-STAY-A", rows
        ),
        VARIABLES,
        2,
    )
    assert hourly[0]["heart_rate_value"] is None
    assert hourly[0]["heart_rate_hours_since"] is None
    assert hourly[2]["heart_rate_value"] == 80.0
    assert hourly[2]["heart_rate_missing"] == 1
    assert hourly[3]["heart_rate_value"] == 80.0
    assert hourly[3]["heart_rate_hours_since"] == 2
    assert hourly[4]["heart_rate_value"] == 90.0


def test_sustained_hypotension_requires_consecutive_future_hours() -> None:
    assert sustained_hypotension_label([70, 64, 63, 70, 70, 70]) == 1
    assert sustained_hypotension_label([64, 70, 64, 70, 70, 70]) == 0
    assert sustained_hypotension_label([70, 64, None, 63, 70, 70]) is None


def test_current_map_is_not_part_of_future_label() -> None:
    map_values = [75.0] * 18
    map_values[11] = 40.0
    windows, quality = build_stay_windows(
        _hourly_rows(map_values),
        VARIABLES,
        input_hours=12,
        horizon_hours=6,
        map_variable="mean_arterial_pressure",
        threshold=65.0,
        consecutive_hours=2,
        require_complete_future_map=True,
    )
    output = list(windows)
    assert quality["windows_created"] == 1
    assert output[0]["label"] == 0
    assert output[0]["mean_arterial_pressure_h0_value"] == 40.0


def test_future_values_never_enter_predictor_window() -> None:
    map_values = [75.0] * 18
    map_values[12:14] = [60.0, 60.0]
    output = list(
        build_stay_windows(
            _hourly_rows(map_values),
            VARIABLES,
            12,
            6,
            "mean_arterial_pressure",
            65.0,
            2,
            True,
        )[0]
    )
    assert output[0]["label"] == 1
    assert output[0]["mean_arterial_pressure_h0_value"] == 75.0
    assert all("h1_" not in key for key in output[0])


def test_incomplete_future_horizon_is_excluded() -> None:
    map_values = [75.0] * 18
    map_values[17] = None
    windows, quality = build_stay_windows(
        _hourly_rows(map_values), VARIABLES, 12, 6, "mean_arterial_pressure", 65, 2, True
    )
    assert list(windows) == []
    assert quality["windows_excluded_incomplete_future_map"] == 1


def test_short_stay_does_not_create_cross_stay_window() -> None:
    windows, quality = build_stay_windows(
        _hourly_rows([75.0] * 17),
        VARIABLES,
        12,
        6,
        "mean_arterial_pressure",
        65,
        2,
        True,
    )
    assert list(windows) == []
    assert quality["candidate_windows"] == 0


def test_end_to_end_outputs_are_deterministic_and_report_is_aggregate(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / "canonical.csv"
    fieldnames = list(_canonical_row(0, "heart_rate", 80))
    rows = []
    for hour in range(18):
        rows.append(_canonical_row(hour, "heart_rate", 80 + hour))
        rows.append(
            _canonical_row(
                hour,
                "mean_arterial_pressure",
                60 if hour in (12, 13) else 75,
            )
        )
    with canonical.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    hourly_a = tmp_path / "hourly-a.csv"
    windows_a = tmp_path / "windows-a.csv"
    report_a = tmp_path / "quality-a.json"
    quality = build_phase_1b_dataset(
        canonical, hourly_a, windows_a, report_a, CONFIG
    )
    hourly_b = tmp_path / "hourly-b.csv"
    windows_b = tmp_path / "windows-b.csv"
    report_b = tmp_path / "quality-b.json"
    build_phase_1b_dataset(canonical, hourly_b, windows_b, report_b, CONFIG)

    assert hourly_a.read_bytes() == hourly_b.read_bytes()
    assert windows_a.read_bytes() == windows_b.read_bytes()
    assert report_a.read_bytes() == report_b.read_bytes()
    assert quality["counts"]["windows_created"] == 1
    assert quality["counts"]["positive_windows"] == 1
    report_text = report_a.read_text(encoding="utf-8")
    for forbidden in ("SYNTHETIC-SUBJECT", "SYNTHETIC-HADM", "SYNTHETIC-STAY"):
        assert forbidden not in report_text
    assert json.loads(report_text)["event_prevalence"] == 1.0
