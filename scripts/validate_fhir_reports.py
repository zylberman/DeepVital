from __future__ import annotations

import csv
import gzip
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
FHIR_DIR = (
    PROJECT_ROOT
    / "data"
    / "mimic-iv-clinical-database-demo-on-fhir-2.1.0"
    / "fhir"
)

REPORT_FILES = [
    "fhir_resource_counts.csv",
    "fhir_chartevents_codes.csv",
    "fhir_chartevents_units.csv",
    "fhir_reference_summary.csv",
]

EXPECTED_COLUMN_GROUPS: dict[str, list[set[str]]] = {
    "fhir_resource_counts.csv": [
        {"filename", "file", "source_file"},
        {"resource_count", "count", "resources"},
    ],
    "fhir_chartevents_codes.csv": [
        {"code_system", "system"},
        {"code"},
        {"display", "code_display"},
        {"resource_count", "count"},
        {"value_type"},
    ],
    "fhir_chartevents_units.csv": [
        {"unit", "unit_code", "observed_unit", "original_unit"},
        {"resource_count", "count"},
    ],
    "fhir_reference_summary.csv": [
        {"reference_path", "path", "field"},
        {"target_type", "reference_target", "target_resource_type"},
        {"resource_count", "count"},
    ],
}

SENSITIVE_FIELD_NAMES = {
    "subject_id",
    "hadm_id",
    "stay_id",
    "patient_id",
    "encounter_id",
    "resource_id",
}

# Matches a complete FHIR reference value, but not a display such as
# "Patient/Family Informed".
FHIR_IDENTIFIER_REFERENCE = re.compile(
    r"^(Patient|Encounter)/[A-Za-z0-9._-]+$"
)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise ValueError("CSV has no header")

        fieldnames = [name.strip() for name in reader.fieldnames]
        rows = []

        for raw_row in reader:
            row = {
                (key or "").strip(): (value or "").strip()
                for key, value in raw_row.items()
            }
            rows.append(row)

        return fieldnames, rows


def find_column(headers: Iterable[str], candidates: set[str]) -> str | None:
    normalized = {header.lower(): header for header in headers}

    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]

    return None


def validate_nonnegative_counts(
    filename: str,
    headers: list[str],
    rows: list[dict[str, str]],
    errors: list[str],
) -> None:
    count_columns = [
        header
        for header in headers
        if header.lower() in {"count", "resource_count", "resources"}
        or header.lower().endswith("_count")
    ]

    for column in count_columns:
        for row_number, row in enumerate(rows, start=2):
            value = row.get(column, "")

            if value == "":
                errors.append(
                    f"{filename}:{row_number}: empty count in {column}"
                )
                continue

            try:
                numeric_value = int(value)
            except ValueError:
                errors.append(
                    f"{filename}:{row_number}: non-integer count "
                    f"{column}={value!r}"
                )
                continue

            if numeric_value < 0:
                errors.append(
                    f"{filename}:{row_number}: negative count "
                    f"{column}={numeric_value}"
                )


def validate_privacy(
    filename: str,
    headers: list[str],
    rows: list[dict[str, str]],
    errors: list[str],
) -> None:
    for header in headers:
        if header.lower() in SENSITIVE_FIELD_NAMES:
            errors.append(
                f"{filename}: sensitive column present: {header}"
            )

    for row_number, row in enumerate(rows, start=2):
        for column, value in row.items():
            if FHIR_IDENTIFIER_REFERENCE.fullmatch(value):
                errors.append(
                    f"{filename}:{row_number}: individual FHIR reference "
                    f"found in column {column}"
                )


def validate_duplicate_rows(
    filename: str,
    headers: list[str],
    rows: list[dict[str, str]],
    warnings: list[str],
) -> None:
    serialized = [
        tuple(row.get(header, "") for header in headers)
        for row in rows
    ]
    duplicates = sum(
        count - 1 for count in Counter(serialized).values() if count > 1
    )

    if duplicates:
        warnings.append(
            f"{filename}: {duplicates} exact duplicate rows"
        )


def validate_required_columns(
    filename: str,
    headers: list[str],
    errors: list[str],
) -> None:
    groups = EXPECTED_COLUMN_GROUPS[filename]

    for alternatives in groups:
        if find_column(headers, alternatives) is None:
            errors.append(
                f"{filename}: missing one of these equivalent columns: "
                f"{sorted(alternatives)}"
            )


def count_gzip_lines(path: Path) -> int:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def validate_resource_counts_against_raw(
    headers: list[str],
    rows: list[dict[str, str]],
    errors: list[str],
    warnings: list[str],
) -> None:
    filename_column = find_column(
        headers, {"filename", "file", "source_file"}
    )
    count_column = find_column(
        headers, {"resource_count", "count", "resources"}
    )

    if filename_column is None or count_column is None:
        warnings.append(
            "Could not cross-check raw files because filename/count columns "
            "were not identified."
        )
        return

    report_counts: dict[str, int] = {}

    for row in rows:
        filename = Path(row.get(filename_column, "")).name
        raw_count = row.get(count_column, "")

        if not filename or not raw_count:
            continue

        try:
            report_counts[filename] = int(raw_count)
        except ValueError:
            continue

    for raw_file in sorted(FHIR_DIR.glob("*.ndjson.gz")):
        if raw_file.name not in report_counts:
            warnings.append(
                f"Raw file missing from resource report: {raw_file.name}"
            )
            continue

        actual_count = count_gzip_lines(raw_file)
        reported_count = report_counts[raw_file.name]

        if actual_count != reported_count:
            errors.append(
                f"Count mismatch for {raw_file.name}: "
                f"raw={actual_count}, report={reported_count}"
            )


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    loaded: dict[str, tuple[list[str], list[dict[str, str]]]] = {}

    for filename in REPORT_FILES:
        path = REPORTS_DIR / filename

        if not path.exists():
            errors.append(f"Missing report: {path}")
            continue

        try:
            headers, rows = read_csv(path)
        except Exception as exc:
            errors.append(f"{filename}: cannot parse CSV: {exc}")
            continue

        loaded[filename] = (headers, rows)

        print(f"\n{filename}")
        print(f"  columns: {headers}")
        print(f"  data rows: {len(rows)}")

        if not rows:
            errors.append(f"{filename}: report contains no data rows")

        validate_required_columns(filename, headers, errors)
        validate_nonnegative_counts(filename, headers, rows, errors)
        validate_privacy(filename, headers, rows, errors)
        validate_duplicate_rows(filename, headers, rows, warnings)

    resource_report = loaded.get("fhir_resource_counts.csv")

    if resource_report is not None:
        validate_resource_counts_against_raw(
            *resource_report,
            errors=errors,
            warnings=warnings,
        )

    print("\nWARNINGS")
    if warnings:
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("  None")

    print("\nERRORS")
    if errors:
        for error in errors:
            print(f"  - {error}")
        print(f"\nValidation failed with {len(errors)} error(s).")
        return 1

    print("\nAll structural, count and privacy checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
