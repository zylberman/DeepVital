"""Streaming extraction of canonical ICU vital observations."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from deepvital.cohort.encounters import (
    EncounterIndex,
    build_encounter_index,
    parse_fhir_datetime,
    resolve_icu_stay,
)
from deepvital.fhir.reader import stream_fhir_resources
from deepvital.preprocessing.units import normalize_unit


CANONICAL_COLUMNS = [
    "subject_id",
    "hadm_id",
    "stay_id",
    "observation_time",
    "source_resource",
    "code_system",
    "observation_code",
    "observation_display",
    "normalized_variable",
    "numeric_value",
    "original_unit",
    "normalized_value",
    "normalized_unit",
]


def load_yaml_compatible_json(path: Path) -> dict[str, Any]:
    """Load configuration written in the JSON subset of YAML."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Configuration root must be a mapping")
    return value


def _codings(concept: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(concept, dict):
        return
    for coding in concept.get("coding", []):
        if isinstance(coding, dict):
            yield coding


def observation_measurements(resource: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield confirmed top-level Chartevents code/valueQuantity measurements."""
    if isinstance(resource.get("valueQuantity"), dict):
        for coding in _codings(resource.get("code")):
            yield {"coding": coding, "quantity": resource["valueQuantity"]}


def _canonical_row(
    index: EncounterIndex,
    stay: Any,
    observation_time: Any,
    coding: dict[str, Any],
    quantity: dict[str, Any],
    mapping: dict[str, Any],
    unit_config: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    raw_value = quantity.get("value")
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        return None, "missing_value", None
    numeric_value = float(raw_value)
    variable = mapping["variable"]
    normalized_value, normalized_unit, conversion = normalize_unit(
        variable,
        numeric_value,
        quantity.get("unit"),
        quantity.get("code"),
        unit_config,
    )
    if normalized_value is None or normalized_unit is None:
        return None, "unsupported_unit", None
    subject_id = index.patient_ids[stay.patient_resource_id]
    return (
        {
            "subject_id": subject_id,
            "hadm_id": stay.hadm_id,
            "stay_id": stay.stay_id,
            "observation_time": observation_time.isoformat().replace("+00:00", "Z"),
            "source_resource": "MimicObservationChartevents",
            "code_system": str(coding.get("system", "")),
            "observation_code": str(coding.get("code", "")),
            "observation_display": str(coding.get("display", mapping["display"])),
            "normalized_variable": variable,
            "numeric_value": numeric_value,
            "original_unit": str(quantity.get("unit", "")),
            "normalized_value": normalized_value,
            "normalized_unit": normalized_unit,
        },
        None,
        conversion,
    )


def extract_rows(
    fhir_dir: Path,
    vital_config: dict[str, Any],
    unit_config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Extract canonical rows and aggregate-only quality counts."""
    index = build_encounter_index(fhir_dir)
    counters: Counter[str] = Counter()
    rejections: Counter[str] = Counter()
    conversions: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    expected_system = vital_config["code_system"]
    mappings = vital_config["mappings"]
    ranges = vital_config["physiological_ranges"]
    path = fhir_dir / "MimicObservationChartevents.ndjson.gz"

    for resource, error in stream_fhir_resources(path):
        counters["resources_read"] += 1
        if error or resource is None:
            rejections[error or "malformed_json"] += 1
            continue
        timestamp = parse_fhir_datetime(resource.get("effectiveDateTime"))
        stay, mapping_error = resolve_icu_stay(
            index,
            resource.get("subject", {}).get("reference"),
            resource.get("encounter", {}).get("reference"),
            timestamp,
        )
        if mapping_error:
            rejections[mapping_error] += 1
            continue
        if resource.get("component"):
            rejections["unsupported_component_structure"] += 1
            continue
        measurements = list(observation_measurements(resource))
        if not measurements:
            if "valueQuantity" in resource:
                rejections["missing_code"] += 1
            elif any(key.startswith("value") for key in resource):
                rejections["unsupported_value_type"] += 1
            else:
                rejections["missing_value"] += 1
            continue
        selected_from_resource = False
        for measurement in measurements:
            coding = measurement["coding"]
            code = str(coding.get("code", ""))
            if coding.get("system") != expected_system or code not in mappings:
                rejections["unsupported_code"] += 1
                continue
            row, row_error, conversion = _canonical_row(
                index,
                stay,
                timestamp,
                coding,
                measurement["quantity"],
                mappings[code],
                unit_config,
            )
            if row_error:
                rejections[row_error] += 1
                continue
            lower, upper = ranges[row["normalized_variable"]]
            if not lower <= row["normalized_value"] <= upper:
                rejections["physiological_range_exclusion"] += 1
                continue
            rows.append(row)
            selected_from_resource = True
            conversions[conversion or "identity"] += 1
        if selected_from_resource:
            counters["observations_selected"] += 1

    rows.sort(
        key=lambda row: (
            row["subject_id"],
            row["hadm_id"],
            row["stay_id"],
            row["observation_time"],
            row["observation_code"],
            row["numeric_value"],
        )
    )
    rejection_categories = (
        "malformed_json",
        "non_object_json",
        "missing_timestamp",
        "missing_subject_reference",
        "missing_encounter_reference",
        "subject_encounter_mismatch",
        "no_candidate_icu_stay",
        "ambiguous_icu_mapping",
        "missing_code",
        "missing_value",
        "unsupported_value_type",
        "unsupported_component_structure",
        "unsupported_code",
        "unsupported_unit",
        "physiological_range_exclusion",
    )
    for category in rejection_categories:
        rejections[category] += 0
    rejected = sum(rejections.values())
    quality = {
        "resources_read": counters["resources_read"],
        "observations_selected": counters["observations_selected"],
        "canonical_observations": len(rows),
        "observations_rejected": rejected,
        "rejections": dict(sorted(rejections.items())),
        "unit_conversions": dict(sorted(conversions.items())),
        "entities": index.aggregate_counts,
        "represented_entities": {
            "patients": len({row["subject_id"] for row in rows}),
            "hospital_admissions": len({row["hadm_id"] for row in rows}),
            "icu_stays": len({row["stay_id"] for row in rows}),
        },
        "relationship_index_quality": dict(sorted(index.quality.items())),
    }
    return rows, quality


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_output(
    path: Path, rows: list[dict[str, Any]], requested_format: str = "csv"
) -> tuple[Path, str]:
    """Write the requested format, falling back from Parquet to deterministic CSV."""
    if requested_format not in {"csv", "parquet"}:
        raise ValueError("requested_format must be 'csv' or 'parquet'")
    if requested_format == "parquet":
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            fallback = path.with_suffix(".csv")
            write_csv(fallback, rows)
            return fallback, "csv"
        path = path.with_suffix(".parquet")
        path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pylist(rows, schema=None)
        pq.write_table(table, path)
        return path, "parquet"
    path = path.with_suffix(".csv")
    write_csv(path, rows)
    return path, "csv"


def write_quality_report(path: Path, quality: dict[str, Any], output_format: str) -> None:
    """Write aggregate counts only; never include output rows or identifiers."""
    report = dict(quality)
    report["output_format"] = output_format
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
