import csv
import json
from pathlib import Path

from deepvital.cohort.dataset import (
    assert_accounting_identities,
    build_phase_1b_dataset,
)
from deepvital.features.temporal import derived_features, trailing_features
from deepvital.features.windows import build_stay_windows
from deepvital.labeling.hypotension import sustained_hypotension_label
from deepvital.preprocessing.hourly import CanonicalStay, aggregate_stay_hourly
from deepvital.splitting.patient_split import (
    assert_patient_disjoint,
    assign_patient_splits,
)
from deepvital.windows.builder import build_modeling_dataset, stream_hourly_stays

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
    assert sustained_hypotension_label([70, 65, 64, 70, 70, 70]) == 0


def test_hourly_grid_respects_confirmed_icu_period() -> None:
    rows = [
        _canonical_row(0, "heart_rate", 70),
        _canonical_row(1, "heart_rate", 80),
        _canonical_row(3, "heart_rate", 90),
    ]
    from deepvital.preprocessing.hourly import parse_utc

    hourly, quality = aggregate_stay_hourly(
        CanonicalStay(
            "SYNTHETIC-SUBJECT", "SYNTHETIC-HADM", "SYNTHETIC-STAY-A", rows
        ),
        VARIABLES,
        {"heart_rate": 1, "mean_arterial_pressure": 0},
        period_start=parse_utc("2020-01-01T01:00:00Z"),
        period_end=parse_utc("2020-01-01T02:59:00Z"),
    )
    assert [row["hour"] for row in hourly] == [
        "2020-01-01T01:00:00Z",
        "2020-01-01T02:00:00Z",
    ]
    assert quality["observations_outside_icu_period"] == 2
    assert hourly[0]["heart_rate_observed"] == 1
    assert hourly[0]["heart_rate_measurement_count"] == 1
    assert hourly[1]["heart_rate_forward_filled"] == 1


def test_trailing_features_do_not_use_future_rows() -> None:
    rows = _hourly_rows([80.0] * 13)
    for index, row in enumerate(rows):
        row["heart_rate_value"] = float(index + 1)
        row["heart_rate_observed_value"] = float(index + 1)
    first_twelve = trailing_features(rows[:12], "heart_rate")
    rows[12]["heart_rate_value"] = 9999.0
    rows[12]["heart_rate_observed_value"] = 9999.0
    repeated = trailing_features(rows[:12], "heart_rate")
    assert first_twelve == repeated
    assert first_twelve["heart_rate_current"] == 12.0
    assert first_twelve["heart_rate_rolling_mean"] == 6.5
    assert first_twelve["heart_rate_rolling_slope"] == 1.0


def test_derived_features_require_valid_denominator() -> None:
    valid = derived_features(
        {
            "systolic_bp_value": 120.0,
            "diastolic_bp_value": 70.0,
            "heart_rate_value": 90.0,
        }
    )
    assert valid["pulse_pressure"] == 50.0
    assert valid["shock_index"] == 0.75
    invalid = derived_features(
        {
            "systolic_bp_value": 0.0,
            "diastolic_bp_value": 70.0,
            "heart_rate_value": 90.0,
        }
    )
    assert invalid["shock_index"] is None
    assert invalid["shock_index_missing"] == 1


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


def test_patient_level_split_is_disjoint_and_deterministic() -> None:
    patients = {f"SYNTHETIC-PATIENT-{index}" for index in range(20)}
    proportions = {"train": 0.7, "validation": 0.15, "test": 0.15}
    first = assign_patient_splits(patients, proportions, seed=42)
    second = assign_patient_splits(patients, proportions, seed=42)
    assert first == second
    assert list(first.values()).count("train") == 14
    assert list(first.values()).count("validation") == 3
    assert list(first.values()).count("test") == 3
    rows = [
        {"subject_id": patient, "split": split}
        for patient, split in first.items()
        for _ in range(2)
    ]
    assert_patient_disjoint(rows)


def test_all_stays_and_windows_for_patient_remain_together() -> None:
    patients = {"SYNTHETIC-PATIENT-A", "SYNTHETIC-PATIENT-B"}
    assignments = assign_patient_splits(
        patients,
        {"train": 0.5, "validation": 0.0, "test": 0.5},
        seed=11,
    )
    rows = []
    for patient in patients:
        for admission in range(2):
            for stay in range(2):
                for window in range(3):
                    rows.append(
                        {
                            "subject_id": patient,
                            "hadm_id": f"SYNTHETIC-HADM-{admission}",
                            "stay_id": f"SYNTHETIC-STAY-{admission}-{stay}",
                            "window_id": f"SYNTHETIC-WINDOW-{window}",
                            "split": assignments[patient],
                        }
                    )
    assert_patient_disjoint(rows)
    for patient in patients:
        assert len({row["split"] for row in rows if row["subject_id"] == patient}) == 1


def test_exact_phase_1b_accounting_identities() -> None:
    counts = {
        "hourly_rows": 12309,
        "hourly_observed_cells": 76190,
        "forward_filled_cells": 8846,
        "unfilled_missing_cells": 13436,
        "candidate_windows": 10008,
        "windows_created": 8872,
        "windows_excluded_incomplete_future_map": 1136,
        "windows_excluded_minimum_observed_data": 0,
        "positive_windows": 1759,
        "negative_windows": 7113,
    }
    identities = assert_accounting_identities(counts, variable_count=8)
    assert identities == {
        "hourly_cell_partition": True,
        "candidate_window_partition": True,
        "label_partition": True,
    }


def test_numeric_looking_identifiers_remain_text(tmp_path: Path) -> None:
    path = tmp_path / "hourly.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["subject_id", "hadm_id", "stay_id", "hour", "x_value"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "subject_id": "001",
                "hadm_id": "002",
                "stay_id": "003",
                "hour": "2020-01-01T00:00:00Z",
                "x_value": "4.5",
            }
        )
    row = next(stream_hourly_stays(path))[0]
    assert row["subject_id"] == "001"
    assert row["hadm_id"] == "002"
    assert row["stay_id"] == "003"
    assert row["x_value"] == 4.5


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


def test_legacy_phase_1b_split_report_is_aggregate_only(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.csv"
    rows = []
    for hour in range(18):
        rows.extend(
            [
                _canonical_row(hour, "heart_rate", 80),
                _canonical_row(hour, "mean_arterial_pressure", 75),
            ]
        )
    with canonical.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = tmp_path / "split-manifest.json"
    split_report = tmp_path / "split-report.json"
    quality = tmp_path / "quality.json"
    build_phase_1b_dataset(
        canonical,
        tmp_path / "hourly.csv",
        tmp_path / "windows.csv",
        quality,
        CONFIG,
        {
            "seed": 9,
            "proportions": {"train": 1.0, "validation": 0.0, "test": 0.0},
        },
        manifest,
        split_report,
    )
    public_text = quality.read_text() + split_report.read_text()
    for forbidden in ("SYNTHETIC-SUBJECT", "SYNTHETIC-HADM", "SYNTHETIC-STAY"):
        assert forbidden not in public_text
    assert "SYNTHETIC-SUBJECT" in manifest.read_text()
    report = json.loads(split_report.read_text())
    assert report["patient_overlap_count"] == 0
    assert report["splits"]["train"]["patients"] == 1


def test_new_modeling_reports_are_aggregate_only(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.csv"
    rows = []
    for hour in range(18):
        rows.extend(
            [
                _canonical_row(hour, "heart_rate", 80),
                _canonical_row(hour, "mean_arterial_pressure", 75),
            ]
        )
    with canonical.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    hourly = tmp_path / "hourly.csv"
    build_phase_1b_dataset(
        canonical,
        hourly,
        tmp_path / "legacy-windows.csv",
        tmp_path / "legacy-quality.json",
        CONFIG,
    )
    report_dir = tmp_path / "reports"
    build_modeling_dataset(
        hourly,
        tmp_path / "deepvital_windows.parquet",
        tmp_path / "split_manifest.json",
        report_dir,
        VARIABLES,
        {
            "minimum_total_observed_cells_per_window": 1,
            "minimum_observed_hours_by_variable": {},
        },
        {"observation_window_hours": 12, "prediction_horizon_hours": 6},
        {
            "map_variable": "mean_arterial_pressure",
            "threshold": 65.0,
            "consecutive_low_hours": 2,
            "require_all_future_map_hours_observed": True,
        },
        {
            "seed": 7,
            "proportions": {"train": 0.7, "validation": 0.15, "test": 0.15},
        },
    )
    public_text = "\n".join(
        path.read_text(encoding="utf-8") for path in report_dir.glob("*.json")
    )
    for forbidden in ("SYNTHETIC-SUBJECT", "SYNTHETIC-HADM", "SYNTHETIC-STAY"):
        assert forbidden not in public_text
    assert "SYNTHETIC-SUBJECT" in (
        tmp_path / "split_manifest.json"
    ).read_text(encoding="utf-8")
