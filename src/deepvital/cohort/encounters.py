"""FHIR Patient, hospital Encounter, and ICU Encounter relationship indexes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deepvital.fhir.reader import stream_fhir_resources


PATIENT_IDENTIFIER_SYSTEM = "http://mimic.mit.edu/fhir/mimic/identifier/patient"
HOSPITAL_IDENTIFIER_SYSTEM = (
    "http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp"
)
ICU_IDENTIFIER_SYSTEM = "http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu"


def reference_id(reference: Any, expected_type: str) -> str | None:
    """Return the local reference id only when the resource type is explicit."""
    if not isinstance(reference, str):
        return None
    prefix = f"{expected_type}/"
    return reference[len(prefix) :] if reference.startswith(prefix) else None


def identifier_value(resource: dict[str, Any], system: str) -> str | None:
    """Select exactly one non-empty identifier for the requested system."""
    values = {
        str(identifier["value"])
        for identifier in resource.get("identifier", [])
        if isinstance(identifier, dict)
        and identifier.get("system") == system
        and identifier.get("value") not in (None, "")
    }
    return next(iter(values)) if len(values) == 1 else None


def parse_fhir_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class HospitalEncounter:
    resource_id: str
    hadm_id: str
    patient_resource_id: str


@dataclass(frozen=True)
class ICUStay:
    resource_id: str
    stay_id: str
    hadm_id: str
    patient_resource_id: str
    start: datetime
    end: datetime


@dataclass
class EncounterIndex:
    patient_ids: dict[str, str]
    hospitals: dict[str, HospitalEncounter]
    icu_stays: dict[str, ICUStay]
    icu_by_hospital: dict[str, list[ICUStay]]
    quality: dict[str, int]

    @property
    def aggregate_counts(self) -> dict[str, int]:
        return {
            "patients": len(self.patient_ids),
            "hospital_admissions": len(self.hospitals),
            "icu_stays": len(self.icu_stays),
        }


def build_encounter_index(fhir_dir: Path) -> EncounterIndex:
    """Build small in-memory relationship indexes from the three encounter files."""
    quality = {
        "patient_resources_read": 0,
        "hospital_encounter_resources_read": 0,
        "icu_encounter_resources_read": 0,
        "malformed_relationship_resources": 0,
        "invalid_patient_resources": 0,
        "invalid_hospital_encounters": 0,
        "invalid_icu_encounters": 0,
    }
    patient_ids: dict[str, str] = {}
    for resource, error in stream_fhir_resources(fhir_dir / "MimicPatient.ndjson.gz"):
        quality["patient_resources_read"] += 1
        if error or resource is None:
            quality["malformed_relationship_resources"] += 1
            continue
        resource_id = resource.get("id")
        subject_id = identifier_value(resource, PATIENT_IDENTIFIER_SYSTEM)
        if not isinstance(resource_id, str) or subject_id is None:
            quality["invalid_patient_resources"] += 1
            continue
        patient_ids[resource_id] = subject_id

    hospitals: dict[str, HospitalEncounter] = {}
    for resource, error in stream_fhir_resources(fhir_dir / "MimicEncounter.ndjson.gz"):
        quality["hospital_encounter_resources_read"] += 1
        if error or resource is None:
            quality["malformed_relationship_resources"] += 1
            continue
        resource_id = resource.get("id")
        hadm_id = identifier_value(resource, HOSPITAL_IDENTIFIER_SYSTEM)
        patient_resource_id = reference_id(
            resource.get("subject", {}).get("reference"), "Patient"
        )
        if (
            not isinstance(resource_id, str)
            or hadm_id is None
            or patient_resource_id not in patient_ids
        ):
            quality["invalid_hospital_encounters"] += 1
            continue
        hospitals[resource_id] = HospitalEncounter(
            resource_id, hadm_id, patient_resource_id
        )

    icu_stays: dict[str, ICUStay] = {}
    icu_by_hospital: dict[str, list[ICUStay]] = {}
    for resource, error in stream_fhir_resources(
        fhir_dir / "MimicEncounterICU.ndjson.gz"
    ):
        quality["icu_encounter_resources_read"] += 1
        if error or resource is None:
            quality["malformed_relationship_resources"] += 1
            continue
        resource_id = resource.get("id")
        stay_id = identifier_value(resource, ICU_IDENTIFIER_SYSTEM)
        patient_resource_id = reference_id(
            resource.get("subject", {}).get("reference"), "Patient"
        )
        hospital_resource_id = reference_id(
            resource.get("partOf", {}).get("reference"), "Encounter"
        )
        hospital = hospitals.get(hospital_resource_id or "")
        period = resource.get("period", {})
        start = parse_fhir_datetime(period.get("start"))
        end = parse_fhir_datetime(period.get("end"))
        if (
            not isinstance(resource_id, str)
            or stay_id is None
            or patient_resource_id not in patient_ids
            or hospital is None
            or hospital.patient_resource_id != patient_resource_id
            or start is None
            or end is None
            or end < start
        ):
            quality["invalid_icu_encounters"] += 1
            continue
        stay = ICUStay(
            resource_id=resource_id,
            stay_id=stay_id,
            hadm_id=hospital.hadm_id,
            patient_resource_id=patient_resource_id,
            start=start,
            end=end,
        )
        icu_stays[resource_id] = stay
        icu_by_hospital.setdefault(hospital.resource_id, []).append(stay)

    for stays in icu_by_hospital.values():
        stays.sort(key=lambda stay: (stay.start, stay.end, stay.resource_id))
    return EncounterIndex(patient_ids, hospitals, icu_stays, icu_by_hospital, quality)


def resolve_icu_stay(
    index: EncounterIndex,
    subject_reference: Any,
    encounter_reference: Any,
    observation_time: datetime | None,
) -> tuple[ICUStay | None, str | None]:
    """Resolve an observation to one ICU stay, returning an explicit failure reason."""
    patient_resource_id = reference_id(subject_reference, "Patient")
    if patient_resource_id is None:
        return None, "missing_subject_reference"
    encounter_resource_id = reference_id(encounter_reference, "Encounter")
    if encounter_resource_id is None:
        return None, "missing_encounter_reference"
    if observation_time is None:
        return None, "missing_timestamp"

    direct_icu = index.icu_stays.get(encounter_resource_id)
    if direct_icu is not None:
        if direct_icu.patient_resource_id != patient_resource_id:
            return None, "subject_encounter_mismatch"
        return direct_icu, None

    hospital = index.hospitals.get(encounter_resource_id)
    if hospital is None or hospital.patient_resource_id != patient_resource_id:
        return None, "no_candidate_icu_stay"
    candidates = [
        stay
        for stay in index.icu_by_hospital.get(encounter_resource_id, [])
        if stay.patient_resource_id == patient_resource_id
        and stay.start <= observation_time <= stay.end
    ]
    if not candidates:
        return None, "no_candidate_icu_stay"
    if len(candidates) > 1:
        return None, "ambiguous_icu_mapping"
    return candidates[0], None
