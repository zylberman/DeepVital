#!/usr/bin/env python3
"""Stream FHIR NDJSON gzip files and write aggregate-only schema inventories.

This utility deliberately never records FHIR resource identifiers or full reference
values. Malformed lines are counted, not printed.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator


TIMESTAMP_FIELDS = {
    "authoredOn",
    "birthDate",
    "date",
    "deceasedDateTime",
    "effectiveDateTime",
    "end",
    "issued",
    "occurrenceDateTime",
    "recordedDate",
    "start",
}
PRESENCE_PATHS = (
    "subject.reference",
    "encounter.reference",
    "effectiveDateTime",
    "effectivePeriod",
    "issued",
    "period",
)
SENSITIVE_KEYS = {"id", "subject_id", "hadm_id", "stay_id", "patient_id", "encounter_id"}


def stream_ndjson_gz(path: Path) -> Iterator[tuple[int, dict[str, Any] | None]]:
    """Yield line number and parsed resource, returning None for malformed JSON."""
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                resource = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                yield line_number, None
                continue
            yield line_number, resource if isinstance(resource, dict) else None


def _has_path(resource: dict[str, Any], dotted_path: str) -> bool:
    current: Any = resource
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return current is not None


def _walk(value: Any, path: str = "") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield child_path, key, child
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child, path)


def _reference_target(reference: Any) -> str:
    if not isinstance(reference, str) or "/" not in reference:
        return "unqualified"
    return reference.split("/", 1)[0] or "unqualified"


def _codings(concept: Any) -> Iterator[tuple[str, str, str]]:
    if not isinstance(concept, dict):
        return
    for coding in concept.get("coding", []):
        if isinstance(coding, dict):
            yield (
                str(coding.get("system", "")),
                str(coding.get("code", "")),
                str(coding.get("display", "")),
            )


def _coding(coding: Any) -> tuple[str, str, str] | None:
    if not isinstance(coding, dict):
        return None
    return (
        str(coding.get("system", "")),
        str(coding.get("code", "")),
        str(coding.get("display", "")),
    )


def _quantity_unit(quantity: Any) -> tuple[str, str]:
    if not isinstance(quantity, dict):
        return "", ""
    return str(quantity.get("unit", "")), str(quantity.get("code", ""))


def _observation_entries(
    resource: dict[str, Any],
) -> Iterator[tuple[str, str, str, str, str, str]]:
    """Yield system, code, display, value type, unit, and UCUM code."""
    top_value_types = sorted(
        key for key in resource if key.startswith("value") and key != "valueSet"
    )
    value_type = "|".join(top_value_types) or "none"
    unit, ucum = _quantity_unit(resource.get("valueQuantity"))
    for system, code, display in _codings(resource.get("code")):
        yield system, code, display, value_type, unit, ucum

    for component in resource.get("component", []):
        if not isinstance(component, dict):
            continue
        component_types = sorted(key for key in component if key.startswith("value"))
        component_value_type = (
            "component." + ("|".join(component_types) if component_types else "none")
        )
        component_unit, component_ucum = _quantity_unit(component.get("valueQuantity"))
        for system, code, display in _codings(component.get("code")):
            yield (
                system,
                code,
                display,
                component_value_type,
                component_unit,
                component_ucum,
            )


def inspect_file(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict]:
    """Inspect one gzip NDJSON file while retaining aggregate metadata only."""
    resource_count = 0
    malformed_count = 0
    resource_types: Counter[str] = Counter()
    top_fields: Counter[str] = Counter()
    coding_systems: Counter[str] = Counter()
    coding_values: Counter[tuple[str, str, str]] = Counter()
    value_types: Counter[str] = Counter()
    units: Counter[tuple[str, str]] = Counter()
    timestamps: Counter[str] = Counter()
    presence: Counter[str] = Counter()
    references: Counter[tuple[str, str]] = Counter()
    code_rows: Counter[tuple[str, str, str, str]] = Counter()
    code_units: defaultdict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    encounter_icu = {
        "class_codes": Counter(),
        "type_codes": Counter(),
        "identifier_systems": Counter(),
        "part_of_reference_targets": Counter(),
        "location_reference_targets": Counter(),
        "subject_reference_targets": Counter(),
        "icu_stay_identifier_present": 0,
    }

    for _, resource in stream_ndjson_gz(path):
        if resource is None:
            malformed_count += 1
            continue
        resource_count += 1
        resource_types[str(resource.get("resourceType", "(missing)"))] += 1
        top_fields.update(resource.keys())
        for presence_path in PRESENCE_PATHS:
            if _has_path(resource, presence_path):
                presence[presence_path] += 1

        resource_codings: set[tuple[str, str, str]] = set()
        for field_path, key, child in _walk(resource):
            if key == "coding" and isinstance(child, list):
                for coding in child:
                    if isinstance(coding, dict):
                        item = (
                            str(coding.get("system", "")),
                            str(coding.get("code", "")),
                            str(coding.get("display", "")),
                        )
                        resource_codings.add(item)
            if key.startswith("value") and key != "valueSet":
                value_types[type(child).__name__ + ":" + key] += 1
            if key in TIMESTAMP_FIELDS or key in {"effectivePeriod", "period"}:
                timestamps[field_path] += 1
            if key == "reference":
                references[(field_path, _reference_target(child))] += 1
            if key == "valueQuantity":
                units[_quantity_unit(child)] += 1
        for system, code, display in resource_codings:
            coding_systems[system] += 1
            coding_values[(system, code, display)] += 1

        seen_entries: set[tuple[str, str, str, str]] = set()
        for system, code, display, value_type, unit, ucum in _observation_entries(resource):
            entry = (system, code, display, value_type)
            seen_entries.add(entry)
            if unit or ucum:
                code_units[entry].add(f"{unit} [{ucum}]" if ucum else unit)
        for entry in seen_entries:
            code_rows[entry] += 1

        if path.name == "MimicEncounterICU.ndjson.gz":
            class_coding = _coding(resource.get("class"))
            if class_coding:
                encounter_icu["class_codes"][class_coding] += 1
            for concept in resource.get("type", []):
                for coding in _codings(concept):
                    encounter_icu["type_codes"][coding] += 1
            identifier_systems = {
                str(identifier.get("system", ""))
                for identifier in resource.get("identifier", [])
                if isinstance(identifier, dict)
            }
            encounter_icu["identifier_systems"].update(identifier_systems)
            if identifier_systems:
                encounter_icu["icu_stay_identifier_present"] += 1
            part_of = resource.get("partOf", {}).get("reference")
            if part_of:
                encounter_icu["part_of_reference_targets"][_reference_target(part_of)] += 1
            for location in resource.get("location", []):
                reference = location.get("location", {}).get("reference", "")
                if reference:
                    encounter_icu["location_reference_targets"][
                        _reference_target(reference)
                    ] += 1
            subject = resource.get("subject", {}).get("reference")
            if subject:
                encounter_icu["subject_reference_targets"][
                    _reference_target(subject)
                ] += 1

    denominator = resource_count or 1
    inventory = {
        "filename": path.name,
        "resource_count": resource_count,
        "malformed_resource_count": malformed_count,
        "resource_types": dict(sorted(resource_types.items())),
        "top_level_fields": dict(sorted(top_fields.items())),
        "coding_systems": dict(sorted(coding_systems.items())),
        "code_values": [
            {"system": s, "code": c, "display": d, "resource_count": n}
            for (s, c, d), n in sorted(coding_values.items())
        ],
        "value_field_types": dict(sorted(value_types.items())),
        "units": [
            {"unit": unit, "ucum_code": ucum, "count": count}
            for (unit, ucum), count in sorted(units.items())
        ],
        "timestamp_fields": dict(sorted(timestamps.items())),
        "presence": {
            key: {"count": presence[key], "rate": presence[key] / denominator}
            for key in PRESENCE_PATHS
        },
        "reference_targets": [
            {"path": p, "target_resource_type": target, "count": count}
            for (p, target), count in sorted(references.items())
        ],
    }
    code_report_rows = [
        {
            "code_system": system,
            "code": code,
            "display": display,
            "resource_count": count,
            "value_type": value_type,
            "observed_units": "|".join(sorted(code_units[(system, code, display, value_type)])),
        }
        for (system, code, display, value_type), count in sorted(code_rows.items())
    ]
    return inventory, code_report_rows, encounter_icu


def _counter_rows(counter: Counter) -> list[dict[str, Any]]:
    rows = []
    for key, count in sorted(counter.items()):
        values = key if isinstance(key, tuple) else (key,)
        rows.append({"values": list(values), "count": count})
    return rows


def build_inventory(input_dir: Path) -> tuple[dict[str, Any], list[dict], list[dict], list[dict]]:
    files = sorted(input_dir.glob("*.ndjson.gz"))
    inventory_files = []
    chartevent_codes: list[dict] = []
    reference_rows: list[dict] = []
    icu_details: dict[str, Any] = {}
    for path in files:
        inventory, code_rows, encounter_icu = inspect_file(path)
        inventory_files.append(inventory)
        if path.name == "MimicObservationChartevents.ndjson.gz":
            chartevent_codes = code_rows
        if path.name == "MimicEncounterICU.ndjson.gz":
            icu_details = {
                key: _counter_rows(value) if isinstance(value, Counter) else value
                for key, value in encounter_icu.items()
            }
        for row in inventory["reference_targets"]:
            reference_rows.append(
                {
                    "filename": path.name,
                    "reference_path": row["path"],
                    "target_resource_type": row["target_resource_type"],
                    "count": row["count"],
                    "resource_count": inventory["resource_count"],
                }
            )
    encounter_resolution = _resolve_encounter_references(input_dir)
    return (
        {
            "file_count": len(files),
            "files": inventory_files,
            "icu_encounter": icu_details,
            "chartevents_encounter_resolution": encounter_resolution,
        },
        chartevent_codes,
        reference_rows,
        [{"filename": item["filename"], "resource_count": item["resource_count"]}
         for item in inventory_files],
    )


def _digest_identifier(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def _resource_id_digests(path: Path) -> set[bytes]:
    digests = set()
    for _, resource in stream_ndjson_gz(path):
        if resource is not None and isinstance(resource.get("id"), str):
            digests.add(_digest_identifier(resource["id"]))
    return digests


def _resolve_encounter_references(input_dir: Path) -> dict[str, int]:
    """Count Chartevents encounter matches without persisting identifiers or hashes."""
    hospital_ids = _resource_id_digests(input_dir / "MimicEncounter.ndjson.gz")
    icu_ids = _resource_id_digests(input_dir / "MimicEncounterICU.ndjson.gz")
    counts: Counter[str] = Counter()
    chart_path = input_dir / "MimicObservationChartevents.ndjson.gz"
    for _, resource in stream_ndjson_gz(chart_path):
        if resource is None:
            continue
        reference = resource.get("encounter", {}).get("reference")
        if not isinstance(reference, str) or "/" not in reference:
            counts["missing_or_unqualified"] += 1
            continue
        digest = _digest_identifier(reference.rsplit("/", 1)[-1])
        in_hospital = digest in hospital_ids
        in_icu = digest in icu_ids
        if in_icu and not in_hospital:
            counts["icu_encounter"] += 1
        elif in_hospital and not in_icu:
            counts["hospital_encounter"] += 1
        elif in_hospital and in_icu:
            counts["ambiguous_both"] += 1
        else:
            counts["unmatched"] += 1
    return dict(sorted(counts.items()))


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    """Build and write the five aggregate reports requested for discovery."""
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory, codes, references, counts = build_inventory(input_dir)
    inventory_path = output_dir / "fhir_inventory.json"
    inventory_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_csv(
        output_dir / "fhir_resource_counts.csv",
        ["filename", "resource_count"],
        counts,
    )
    _write_csv(
        output_dir / "fhir_chartevents_codes.csv",
        [
            "code_system",
            "code",
            "display",
            "resource_count",
            "value_type",
            "observed_units",
        ],
        codes,
    )
    unit_counter: Counter[tuple[str, str]] = Counter()
    chartevents = next(
        (
            item
            for item in inventory["files"]
            if item["filename"] == "MimicObservationChartevents.ndjson.gz"
        ),
        None,
    )
    if chartevents:
        for unit in chartevents["units"]:
            unit_counter[(unit["unit"], unit["ucum_code"])] += unit["count"]
    _write_csv(
        output_dir / "fhir_chartevents_units.csv",
        ["unit", "ucum_code", "count"],
        (
            {"unit": unit, "ucum_code": ucum, "count": count}
            for (unit, ucum), count in sorted(unit_counter.items())
        ),
    )
    _write_csv(
        output_dir / "fhir_reference_summary.csv",
        [
            "filename",
            "reference_path",
            "target_resource_type",
            "count",
            "resource_count",
        ],
        references,
    )
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()
    inventory = write_reports(args.input_dir, args.output_dir)
    total = sum(item["resource_count"] for item in inventory["files"])
    malformed = sum(item["malformed_resource_count"] for item in inventory["files"])
    print(
        f"Inspected {inventory['file_count']} files and {total} resources; "
        f"malformed lines: {malformed}. Aggregate reports written to {args.output_dir}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
