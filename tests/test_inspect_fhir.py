import csv
import gzip
import json
from pathlib import Path

from scripts.inspect_fhir import inspect_file, stream_ndjson_gz, write_reports


def _write_gzip(path: Path, records: list[object], malformed: bool = False) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
        if malformed:
            handle.write('{"resourceType": "Observation"\n')


def _observation() -> dict:
    return {
        "resourceType": "Observation",
        "id": "forbidden-resource-id",
        "subject": {"reference": "Patient/forbidden-patient-id"},
        "encounter": {"reference": "Encounter/forbidden-stay-id"},
        "effectiveDateTime": "2020-01-01T00:00:00Z",
        "code": {
            "coding": [
                {"system": "synthetic-system", "code": "hr", "display": "Heart rate"}
            ]
        },
        "valueQuantity": {"value": 80, "unit": "beats/min", "code": "/min"},
    }


def test_reads_gzip_ndjson_and_handles_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "Synthetic.ndjson.gz"
    _write_gzip(path, [_observation()], malformed=True)
    rows = list(stream_ndjson_gz(path))
    assert len(rows) == 2
    assert rows[0][1]["resourceType"] == "Observation"
    assert rows[1][1] is None


def test_observation_quantity_code_unit_and_encounter_reference(tmp_path: Path) -> None:
    path = tmp_path / "MimicObservationChartevents.ndjson.gz"
    _write_gzip(path, [_observation()])
    inventory, code_rows, _ = inspect_file(path)
    assert inventory["resource_count"] == 1
    assert inventory["presence"]["encounter.reference"]["rate"] == 1.0
    assert code_rows == [
        {
            "code_system": "synthetic-system",
            "code": "hr",
            "display": "Heart rate",
            "resource_count": 1,
            "value_type": "valueQuantity",
            "observed_units": "beats/min [/min]",
        }
    ]


def test_observation_components_are_aggregated(tmp_path: Path) -> None:
    resource = _observation()
    resource.pop("valueQuantity")
    resource["component"] = [
        {
            "code": {
                "coding": [
                    {"system": "synthetic-system", "code": "sys", "display": "Systolic"}
                ]
            },
            "valueQuantity": {"value": 120, "unit": "mmHg", "code": "mm[Hg]"},
        }
    ]
    path = tmp_path / "MimicObservationChartevents.ndjson.gz"
    _write_gzip(path, [resource])
    _, code_rows, _ = inspect_file(path)
    component = next(row for row in code_rows if row["code"] == "sys")
    assert component["value_type"] == "component.valueQuantity"
    assert component["observed_units"] == "mmHg [mm[Hg]]"


def test_reports_never_contain_identifiers(tmp_path: Path) -> None:
    input_dir = tmp_path / "fhir"
    output_dir = tmp_path / "reports"
    input_dir.mkdir()
    _write_gzip(input_dir / "MimicObservationChartevents.ndjson.gz", [_observation()])
    _write_gzip(input_dir / "MimicEncounter.ndjson.gz", [])
    _write_gzip(
        input_dir / "MimicEncounterICU.ndjson.gz",
        [{"resourceType": "Encounter", "id": "forbidden-stay-id"}],
    )
    write_reports(input_dir, output_dir)
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in output_dir.iterdir()
    )
    assert "forbidden-resource-id" not in combined
    assert "forbidden-patient-id" not in combined
    assert "forbidden-stay-id" not in combined
    with (output_dir / "fhir_chartevents_codes.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["resource_count"] == "1"


def test_icu_encounter_class_and_reference_resolution(tmp_path: Path) -> None:
    input_dir = tmp_path / "fhir"
    input_dir.mkdir()
    _write_gzip(input_dir / "MimicEncounter.ndjson.gz", [])
    _write_gzip(
        input_dir / "MimicEncounterICU.ndjson.gz",
        [
            {
                "resourceType": "Encounter",
                "id": "synthetic-icu",
                "class": {"system": "synthetic-class", "code": "ICU", "display": "ICU"},
            }
        ],
    )
    observation = _observation()
    observation["encounter"]["reference"] = "Encounter/synthetic-icu"
    _write_gzip(input_dir / "MimicObservationChartevents.ndjson.gz", [observation])
    inventory = write_reports(input_dir, tmp_path / "reports")
    assert inventory["chartevents_encounter_resolution"] == {"icu_encounter": 1}
    assert inventory["icu_encounter"]["class_codes"][0]["values"] == [
        "synthetic-class",
        "ICU",
        "ICU",
    ]
