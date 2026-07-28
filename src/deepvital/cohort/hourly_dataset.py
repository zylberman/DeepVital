"""Build the private, ICU-period-bounded hourly vital-sign table."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from deepvital.cohort.encounters import build_encounter_index
from deepvital.preprocessing.hourly import (
    aggregate_stay_hourly,
    hourly_columns,
    stream_canonical_stays,
)
from deepvital.preprocessing.missingness import validate_missingness_config


def csv_fallback(path: Path) -> Path:
    if path.exists() and path.suffix.lower() == ".csv":
        return path
    fallback = path.with_suffix(".csv")
    if fallback.exists():
        return fallback
    if path.exists() and path.suffix.lower() == ".parquet":
        raise RuntimeError("Parquet input requires pyarrow; CSV fallback was not found")
    raise FileNotFoundError(path)


def build_hourly_dataset(
    canonical_input: Path,
    fhir_dir: Path,
    output: Path,
    report_path: Path,
    aggregation_config: dict[str, Any],
    missingness_config: dict[str, Any],
) -> dict[str, Any]:
    variables = list(aggregation_config["variables"])
    validate_missingness_config(missingness_config, variables)
    canonical_path = csv_fallback(canonical_input)
    output = output.with_suffix(".csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    encounter_index = build_encounter_index(fhir_dir)
    bounds = {
        stay.stay_id: stay
        for stay in encounter_index.icu_stays.values()
    }
    counts: Counter[str] = Counter()
    variable_counts = {
        variable: Counter(
            hours_observed=0,
            real_measurements=0,
            forward_filled=0,
            missing_after_forward_fill=0,
        )
        for variable in variables
    }
    patients: set[str] = set()
    admissions: set[str] = set()
    stays_processed = 0
    invalid_stay_identifier = 0

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=hourly_columns(variables))
        writer.writeheader()
        for stay in stream_canonical_stays(canonical_path):
            bound = bounds.get(stay.stay_id)
            if (
                bound is None
                or bound.hadm_id != stay.hadm_id
                or encounter_index.patient_ids.get(bound.patient_resource_id)
                != stay.subject_id
            ):
                invalid_stay_identifier += 1
                continue
            hourly_rows, quality = aggregate_stay_hourly(
                stay,
                variables,
                missingness_config["forward_fill_max_hours"],
                period_start=bound.start,
                period_end=bound.end,
            )
            writer.writerows(hourly_rows)
            stays_processed += 1
            patients.add(stay.subject_id)
            admissions.add(stay.hadm_id)
            for key, value in quality.items():
                if key != "variable_counts":
                    counts[key] += value
            for variable, values in quality["variable_counts"].items():
                variable_counts[variable].update(values)

    report = {
        "configuration": {
            "frequency_hours": aggregation_config["frequency_hours"],
            "aggregation_method": aggregation_config["method"],
            "uses_confirmed_icu_period": True,
            "forward_fill_max_hours": missingness_config[
                "forward_fill_max_hours"
            ],
            "backward_fill": False,
            "interpolation": False,
        },
        "entities": {
            "patients": len(patients),
            "hospital_admissions": len(admissions),
            "icu_stays": stays_processed,
        },
        "counts": {
            **dict(sorted(counts.items())),
            "invalid_or_missing_stay_identifier": invalid_stay_identifier,
        },
        "by_variable": {
            variable: dict(sorted(values.items()))
            for variable, values in variable_counts.items()
        },
        "output_format": "csv",
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
