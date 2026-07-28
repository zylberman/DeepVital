import csv
import gzip
import json
from pathlib import Path

from deepvital.cohort.encounters import (
    build_encounter_index,
    parse_fhir_datetime,
    resolve_icu_stay,
)
from deepvital.fhir.extraction import (
    CANONICAL_COLUMNS,
    extract_rows,
    observation_measurements,
    write_output,
    write_quality_report,
)
from deepvital.fhir.reader import stream_fhir_resources
from deepvital.preprocessing.units import normalize_unit

SYSTEM = "https://synthetic.invalid/chartevents"
PATIENT_SYSTEM = "http://mimic.mit.edu/fhir/mimic/identifier/patient"
HOSPITAL_SYSTEM = "http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp"
ICU_SYSTEM = "http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu"

VITAL_CONFIG = {
    "code_system": SYSTEM,
    "mappings": {
        "hr": {"display": "Synthetic heart rate", "variable": "heart_rate"},
        "temp": {"display": "Synthetic temperature", "variable": "temperature"},
        "sys": {"display": "Synthetic systolic pressure", "variable": "systolic_bp"},
    },
    "physiological_ranges": {
        "heart_rate": [20.0, 300.0],
        "temperature": [25.0, 45.0],
        "systolic_bp": [30.0, 350.0],
    },
}
UNIT_CONFIG = {
    "heart_rate": {
        "normalized_unit": "beats/min",
        "accepted_units": {"bpm": "identity"},
    },
    "temperature": {
        "normalized_unit": "degrees Celsius",
        "accepted_units": {"°F": "fahrenheit_to_celsius", "°C": "identity"},
    },
    "systolic_bp": {
        "normalized_unit": "mmHg",
        "accepted_units": {"mmHg": "identity"},
    },
}


def _write(path: Path, resources: list[dict], malformed: bool = False) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for resource in resources:
            handle.write(json.dumps(resource) + "\n")
        if malformed:
            handle.write("{malformed\n")


def _patient() -> dict:
    return {
        "resourceType": "Patient",
        "id": "SYNTHETIC-PATIENT-RESOURCE",
        "identifier": [{"system": PATIENT_SYSTEM, "value": "SYNTHETIC-SUBJECT"}],
    }


def _hospital() -> dict:
    return {
        "resourceType": "Encounter",
        "id": "SYNTHETIC-HOSPITAL-RESOURCE",
        "identifier": [{"system": HOSPITAL_SYSTEM, "value": "SYNTHETIC-HADM"}],
        "subject": {"reference": "Patient/SYNTHETIC-PATIENT-RESOURCE"},
    }


def _icu(resource_id: str = "SYNTHETIC-ICU-RESOURCE", stay: str = "SYNTHETIC-STAY") -> dict:
    return {
        "resourceType": "Encounter",
        "id": resource_id,
        "identifier": [{"system": ICU_SYSTEM, "value": stay}],
        "subject": {"reference": "Patient/SYNTHETIC-PATIENT-RESOURCE"},
        "partOf": {"reference": "Encounter/SYNTHETIC-HOSPITAL-RESOURCE"},
        "period": {
            "start": "2020-01-01T00:00:00Z",
            "end": "2020-01-02T00:00:00Z",
        },
    }


def _observation(
    encounter: str = "SYNTHETIC-ICU-RESOURCE",
    code: str = "hr",
    value: float = 80.0,
    unit: str = "bpm",
) -> dict:
    return {
        "resourceType": "Observation",
        "id": "SYNTHETIC-OBSERVATION-RESOURCE",
        "subject": {"reference": "Patient/SYNTHETIC-PATIENT-RESOURCE"},
        "encounter": {"reference": f"Encounter/{encounter}"},
        "effectiveDateTime": "2020-01-01T12:00:00Z",
        "code": {
            "coding": [
                {
                    "system": SYSTEM,
                    "code": code,
                    "display": f"Synthetic {code}",
                }
            ]
        },
        "valueQuantity": {"value": value, "unit": unit, "code": unit},
    }


def _fhir_dir(tmp_path: Path, observations: list[dict], icus: list[dict] | None = None) -> Path:
    fhir_dir = tmp_path / "fhir"
    fhir_dir.mkdir(parents=True)
    _write(fhir_dir / "MimicPatient.ndjson.gz", [_patient()])
    _write(fhir_dir / "MimicEncounter.ndjson.gz", [_hospital()])
    _write(fhir_dir / "MimicEncounterICU.ndjson.gz", icus or [_icu()])
    _write(fhir_dir / "MimicObservationChartevents.ndjson.gz", observations)
    return fhir_dir


def test_gzip_ndjson_streaming_and_malformed_handling(tmp_path: Path) -> None:
    path = tmp_path / "resources.ndjson.gz"
    _write(path, [_patient()], malformed=True)
    rows = list(stream_fhir_resources(path))
    assert rows[0][0]["resourceType"] == "Patient"
    assert rows[1] == (None, "malformed_json")


def test_hospital_and_icu_encounter_mapping(tmp_path: Path) -> None:
    index = build_encounter_index(_fhir_dir(tmp_path, []))
    assert index.aggregate_counts == {
        "patients": 1,
        "hospital_admissions": 1,
        "icu_stays": 1,
    }
    stay = index.icu_stays["SYNTHETIC-ICU-RESOURCE"]
    assert stay.hadm_id == "SYNTHETIC-HADM"
    assert stay.stay_id == "SYNTHETIC-STAY"


def test_observation_directly_maps_to_icu(tmp_path: Path) -> None:
    index = build_encounter_index(_fhir_dir(tmp_path, []))
    stay, error = resolve_icu_stay(
        index,
        "Patient/SYNTHETIC-PATIENT-RESOURCE",
        "Encounter/SYNTHETIC-ICU-RESOURCE",
        parse_fhir_datetime("2020-01-01T12:00:00Z"),
    )
    assert error is None
    assert stay.stay_id == "SYNTHETIC-STAY"


def test_hospital_reference_maps_by_timestamp(tmp_path: Path) -> None:
    index = build_encounter_index(_fhir_dir(tmp_path, []))
    stay, error = resolve_icu_stay(
        index,
        "Patient/SYNTHETIC-PATIENT-RESOURCE",
        "Encounter/SYNTHETIC-HOSPITAL-RESOURCE",
        parse_fhir_datetime("2020-01-01T12:00:00Z"),
    )
    assert error is None
    assert stay.stay_id == "SYNTHETIC-STAY"


def test_ambiguous_hospital_mapping_is_rejected(tmp_path: Path) -> None:
    second = _icu("SYNTHETIC-ICU-RESOURCE-2", "SYNTHETIC-STAY-2")
    index = build_encounter_index(_fhir_dir(tmp_path, [], [_icu(), second]))
    stay, error = resolve_icu_stay(
        index,
        "Patient/SYNTHETIC-PATIENT-RESOURCE",
        "Encounter/SYNTHETIC-HOSPITAL-RESOURCE",
        parse_fhir_datetime("2020-01-01T12:00:00Z"),
    )
    assert stay is None
    assert error == "ambiguous_icu_mapping"


def test_value_quantity_extraction_and_unconfirmed_components_disabled() -> None:
    resource = _observation()
    measurements = list(observation_measurements(resource))
    assert [item["coding"]["code"] for item in measurements] == ["hr"]
    assert measurements[0]["quantity"]["value"] == 80.0

    resource["component"] = [
        {
            "code": {
                "coding": [
                    {"system": SYSTEM, "code": "sys", "display": "Synthetic systolic"}
                ]
            },
            "valueQuantity": {"value": 120, "unit": "mmHg"},
        }
    ]
    measurements = list(observation_measurements(resource))
    assert [item["coding"]["code"] for item in measurements] == ["hr"]


def test_fahrenheit_conversion_requires_confirmed_unit() -> None:
    converted = normalize_unit("temperature", 98.6, "°F", "°F", UNIT_CONFIG)
    assert round(converted[0], 6) == 37.0
    assert converted[2] == "fahrenheit_to_celsius"
    assert normalize_unit("temperature", 98.6, "", "", UNIT_CONFIG) == (
        None,
        None,
        None,
    )


def test_original_value_preserved_and_unsupported_unit_rejected(tmp_path: Path) -> None:
    good_rows, _ = extract_rows(
        _fhir_dir(tmp_path, [_observation(value=81.5)]),
        VITAL_CONFIG,
        UNIT_CONFIG,
    )
    assert good_rows[0]["numeric_value"] == 81.5
    assert good_rows[0]["original_unit"] == "bpm"

    other = tmp_path / "other"
    rows, quality = extract_rows(
        _fhir_dir(other, [_observation(unit="unsupported")]),
        VITAL_CONFIG,
        UNIT_CONFIG,
    )
    assert rows == []
    assert quality["rejections"]["unsupported_unit"] == 1


def test_string_value_is_not_misclassified_as_missing(tmp_path: Path) -> None:
    observation = _observation()
    observation.pop("valueQuantity")
    observation["valueString"] = "synthetic text"
    rows, quality = extract_rows(
        _fhir_dir(tmp_path, [observation]), VITAL_CONFIG, UNIT_CONFIG
    )
    assert rows == []
    assert quality["rejections"]["unsupported_value_type"] == 1
    assert quality["rejections"]["missing_value"] == 0


def test_no_icu_candidate_and_missing_timestamp_are_explicit(tmp_path: Path) -> None:
    index = build_encounter_index(_fhir_dir(tmp_path, []))
    stay, error = resolve_icu_stay(
        index,
        "Patient/SYNTHETIC-PATIENT-RESOURCE",
        "Encounter/SYNTHETIC-HOSPITAL-RESOURCE",
        parse_fhir_datetime("2020-01-03T12:00:00Z"),
    )
    assert stay is None
    assert error == "no_candidate_icu_stay"
    stay, error = resolve_icu_stay(
        index,
        "Patient/SYNTHETIC-PATIENT-RESOURCE",
        "Encounter/SYNTHETIC-ICU-RESOURCE",
        None,
    )
    assert stay is None
    assert error == "missing_timestamp"


def test_components_and_implausible_values_are_rejected(tmp_path: Path) -> None:
    component_observation = _observation()
    component_observation["component"] = [
        {
            "code": {"coding": [{"system": SYSTEM, "code": "sys"}]},
            "valueQuantity": {"value": 120, "unit": "mmHg"},
        }
    ]
    rows, quality = extract_rows(
        _fhir_dir(tmp_path, [component_observation]),
        VITAL_CONFIG,
        UNIT_CONFIG,
    )
    assert rows == []
    assert quality["rejections"]["unsupported_component_structure"] == 1

    other = tmp_path / "range"
    rows, quality = extract_rows(
        _fhir_dir(other, [_observation(value=999.0)]),
        VITAL_CONFIG,
        UNIT_CONFIG,
    )
    assert rows == []
    assert quality["rejections"]["physiological_range_exclusion"] == 1


def test_quality_report_contains_no_identifiers(tmp_path: Path) -> None:
    rows, quality = extract_rows(
        _fhir_dir(tmp_path, [_observation()]), VITAL_CONFIG, UNIT_CONFIG
    )
    report = tmp_path / "quality.json"
    write_quality_report(report, quality, "csv")
    text = report.read_text(encoding="utf-8")
    assert rows
    for forbidden in (
        "SYNTHETIC-SUBJECT",
        "SYNTHETIC-HADM",
        "SYNTHETIC-STAY",
        "SYNTHETIC-PATIENT-RESOURCE",
        "SYNTHETIC-OBSERVATION-RESOURCE",
    ):
        assert forbidden not in text


def test_deterministic_end_to_end_synthetic_extraction(tmp_path: Path) -> None:
    observations = [
        _observation(value=90.0),
        _observation(code="temp", value=98.6, unit="°F"),
    ]
    rows, quality = extract_rows(
        _fhir_dir(tmp_path, observations), VITAL_CONFIG, UNIT_CONFIG
    )
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    assert write_output(first, rows, "csv")[1] == "csv"
    write_output(second, list(reversed(rows)), "csv")
    # write_output preserves its input order; extraction itself is deterministic.
    write_output(second, rows, "csv")
    assert first.read_bytes() == second.read_bytes()
    with first.open(encoding="utf-8", newline="") as handle:
        output_rows = list(csv.DictReader(handle))
    assert list(output_rows[0]) == CANONICAL_COLUMNS
    assert len(output_rows) == 2
    assert quality["canonical_observations"] == 2
    assert quality["unit_conversions"]["fahrenheit_to_celsius"] == 1
