# DeepVital FHIR Data Inventory

**Discovery date:** 2026-07-26  
**Scope:** MIMIC-IV Clinical Database Demo on FHIR 2.1.0, local FHIR directory  
**Status:** Inventory and schema discovery only

DeepVital is a research-only project, not a medical device. This inventory contains
aggregate metadata only. It does not reproduce patient, encounter, ICU-stay, or FHIR
resource identifiers and does not establish clinical validity.

## Dataset and file format

The local dataset contains 30 gzip-compressed NDJSON files. Each non-empty NDJSON
line is one FHIR R4 resource. `scripts/inspect_fhir.py` reads the files in text mode
with `gzip.open` and processes one line at a time. It does not decompress files to
disk or retain complete files in memory.

The discovery run found 928,935 valid resources and no malformed JSON lines.
Detailed field frequencies, coding systems, codes, value types, units, timestamps,
presence rates, and reference-target types are in `reports/fhir_inventory.json`.

## Resource counts

| File | Resources |
|---|---:|
| MimicCondition.ndjson.gz | 4,506 |
| MimicConditionED.ndjson.gz | 545 |
| MimicEncounter.ndjson.gz | 275 |
| MimicEncounterED.ndjson.gz | 222 |
| MimicEncounterICU.ndjson.gz | 140 |
| MimicLocation.ndjson.gz | 31 |
| MimicMedication.ndjson.gz | 1,480 |
| MimicMedicationAdministration.ndjson.gz | 36,131 |
| MimicMedicationAdministrationICU.ndjson.gz | 20,404 |
| MimicMedicationDispense.ndjson.gz | 14,293 |
| MimicMedicationDispenseED.ndjson.gz | 1,082 |
| MimicMedicationMix.ndjson.gz | 314 |
| MimicMedicationRequest.ndjson.gz | 17,552 |
| MimicMedicationStatementED.ndjson.gz | 2,411 |
| MimicObservationChartevents.ndjson.gz | 668,862 |
| MimicObservationDatetimeevents.ndjson.gz | 15,280 |
| MimicObservationED.ndjson.gz | 2,742 |
| MimicObservationLabevents.ndjson.gz | 107,727 |
| MimicObservationMicroOrg.ndjson.gz | 338 |
| MimicObservationMicroSusc.ndjson.gz | 1,036 |
| MimicObservationMicroTest.ndjson.gz | 1,893 |
| MimicObservationOutputevents.ndjson.gz | 9,362 |
| MimicObservationVitalSignsED.ndjson.gz | 6,300 |
| MimicOrganization.ndjson.gz | 1 |
| MimicPatient.ndjson.gz | 100 |
| MimicProcedure.ndjson.gz | 722 |
| MimicProcedureED.ndjson.gz | 1,260 |
| MimicProcedureICU.ndjson.gz | 1,468 |
| MimicSpecimen.ndjson.gz | 1,336 |
| MimicSpecimenLab.ndjson.gz | 11,122 |

The priority resources are `Patient`, hospital `Encounter`, ICU `Encounter`, and
the three ICU `Observation` sources: Chartevents, Datetimeevents, and Outputevents.

## Relationships and ICU representation

Patient-to-Encounter:

- All 275 hospital Encounters and all 140 ICU Encounters have
  `subject.reference` targeting `Patient`.
- Hospital Encounters use `period.start` and `period.end` for admission bounds.
- ICU Encounters also use `period.start` and `period.end` for stay bounds.

Hospital Encounter-to-ICU Encounter:

- Every ICU Encounter has `partOf.reference` targeting an `Encounter`; aggregate
  structure therefore represents the ICU stay as a child of a hospital Encounter.
- Every ICU Encounter contains an identifier using
  `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`, supporting an ICU-stay
  identifier mapping.
- ICU Encounter class is `ACUTE` from HL7 v3 ActCode. Its type is SNOMED CT
  `308335008`, “Patient encounter procedure.”
- All ICU Encounters reference Patient. All have location entries; 151 location
  references target `Location` because some stays have more than one location
  segment.

Observation-to-Encounter:

- All 668,862 Chartevents Observations have both `subject.reference` and
  `encounter.reference`.
- A privacy-safe cross-file comparison used one-way hashes in memory and wrote only
  aggregate match counts. All 668,862 Chartevents encounter references resolve to
  ICU Encounter resources, not hospital Encounter resources.
- All 15,280 Datetimeevents and 9,362 Outputevents Observations also contain Patient
  and Encounter references. Their exact hospital-versus-ICU resolution should be
  confirmed in the next mapping phase; this discovery run resolved Chartevents
  specifically as requested.

## Chartevents schema

Chartevents uses `effectiveDateTime` on every resource. `issued` is present on
667,703 of 668,862 resources (99.83%). There are 257,474 `valueQuantity` resources
and 411,388 `valueString` resources. No top-level `component` structure was found
in this file. Code values come from the MIMIC chartevents D_ITEMS code system;
category coding uses the MIMIC observation-category system.

### Candidate vital-sign mappings

All codes below use
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`.

| Normalized variable | Code | Display | Resources | Unit |
|---|---:|---|---:|---|
| heart_rate | 220045 | Heart Rate | 13,913 | bpm |
| respiratory_rate | 220210 | Respiratory Rate | 13,913 | insp/min |
| systolic_bp (arterial) | 220050 | Arterial Blood Pressure systolic | 5,525 | mmHg |
| diastolic_bp (arterial) | 220051 | Arterial Blood Pressure diastolic | 5,524 | mmHg |
| mean_arterial_pressure (arterial) | 220052 | Arterial Blood Pressure mean | 5,560 | mmHg |
| systolic_bp (non-invasive) | 220179 | Non Invasive Blood Pressure systolic | 8,347 | mmHg |
| diastolic_bp (non-invasive) | 220180 | Non Invasive Blood Pressure diastolic | 8,349 | mmHg |
| mean_arterial_pressure (non-invasive) | 220181 | Non Invasive Blood Pressure mean | 8,342 | mmHg |
| oxygen_saturation | 220277 | O2 saturation pulseoxymetry | 13,540 | % |
| temperature | 223761 | Temperature Fahrenheit | 3,379 | °F |
| temperature | 223762 | Temperature Celsius | 391 | °C |
| oxygen_flow | 223834 | O2 Flow | 1,090 | L/min |
| oxygen_flow | 227287 | O2 Flow (additional cannula) | 145 | L/min |
| oxygen_flow | 227582 | BiPap O2 Flow | 13 | L/min |

Additional arterial BP codes `225309`, `225310`, and `225312` (“ART BP Systolic,”
“ART BP Diastolic,” and “ART BP Mean”) occur 486, 486, and 488 times respectively
in mmHg. These are candidates, not yet an approved sensor mapping.

The full Chartevents code and unit aggregates are in
`reports/fhir_chartevents_codes.csv` and
`reports/fhir_chartevents_units.csv`. Important unit-normalization work remains:
temperature occurs in both °F and °C. Oxygen flow in L/min is not equivalent to
FiO2, oxygen concentration, or a supplemental-oxygen indicator.

## Proposed identifier mapping

The next phase should resolve identifiers locally and immediately pseudonymize them:

| Canonical key | FHIR source |
|---|---|
| `subject_id_hash` | stable keyed hash of the Patient identity referenced by `subject.reference` |
| `hadm_id_hash` | stable keyed hash of the parent hospital Encounter identity |
| `stay_id_hash` | stable keyed hash of the ICU Encounter identity / ICU identifier |

The hashing key must be supplied outside source control. Raw identities and hashes
must not appear in logs, documentation, tests, or public reports. Relationship
validation must require an ICU Encounter to reference both the expected Patient and
parent hospital Encounter.

## Proposed canonical observation table

This is a proposal only; no table or ETL was created:

| Column |
|---|
| `subject_id_hash` |
| `hadm_id_hash` |
| `stay_id_hash` |
| `observation_time` |
| `source_resource` |
| `code_system` |
| `observation_code` |
| `observation_display` |
| `normalized_variable` |
| `numeric_value` |
| `original_unit` |
| `normalized_value` |
| `normalized_unit` |

`observation_time` should initially use `effectiveDateTime`; `issued` is metadata
about recording/publication and must not silently replace physiological event time.
The table must preserve source value/unit before any auditable conversion.

## Unresolved mapping questions

- Confirm the authoritative relationship between each ICU Encounter identifier and
  the source MIMIC `stay_id`, and between each parent Encounter and `hadm_id`.
- Resolve Datetimeevents and Outputevents references against ICU versus hospital
  Encounters using the same aggregate-only validation used for Chartevents.
- Decide precedence and duplicate handling among invasive, non-invasive, and
  alternate arterial blood-pressure codes. These sources must not be merged without
  an explicit, documented rule.
- Confirm whether the primary MAP outcome should accept both invasive and
  non-invasive MAP and how simultaneous measurements are aggregated.
- Validate all candidate code mappings against the official MIMIC D_ITEMS
  dictionary; display-label matching alone is insufficient.
- Define audited Fahrenheit-to-Celsius conversion and physiological plausibility
  ranges.
- Determine how oxygen delivery device/string observations complement numeric
  oxygen-flow values. Oxygen flow must not be treated as FiO2.
- Determine handling of the 94,903 quantity records with blank unit/code across all
  Chartevents codes; absence of units may be code-specific and cannot be globally
  inferred.
- Establish timezone expectations and whether all effective timestamps are
  consistently normalized.

## Recommended next step

Proceed to a separate, synthetic-first FHIR mapping and ETL design phase. Add a
configuration-controlled code/unit map, locally pseudonymized Patient–hospital
Encounter–ICU Encounter resolution, numeric observation extraction, validation
reports, and synthetic tests. Do not train a model, write to PostgreSQL, or process
real observations into a final cohort until those mappings and safeguards are
reviewed.
