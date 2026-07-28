# DeepVital Canonical Vital-Sign Data Model

**Phase:** 1A — canonical FHIR extraction  
**Status:** Implemented for local research extraction; not a medical device

This phase creates a long-format, observation-level table. It does not aggregate
hours, impute values, build windows, create an outcome label, split data, or train a
model.

## Local canonical schema

| Column | Meaning |
|---|---|
| `subject_id` | Local MIMIC Patient identifier selected from the configured Patient identifier system |
| `hadm_id` | Local hospital-admission identifier from the parent hospital Encounter |
| `stay_id` | Local ICU-stay identifier from the ICU Encounter |
| `observation_time` | FHIR `effectiveDateTime`, normalized to a UTC ISO-8601 string |
| `source_resource` | Source family; currently `MimicObservationChartevents` |
| `code_system` | Source FHIR coding system |
| `observation_code` | Source chart-event code |
| `observation_display` | Source FHIR display label |
| `normalized_variable` | Configuration-controlled DeepVital variable |
| `numeric_value` | Original numeric quantity, unchanged |
| `original_unit` | Original FHIR `valueQuantity.unit` |
| `normalized_value` | Audited value after explicit unit conversion |
| `normalized_unit` | Canonical unit for the normalized variable |

The identifier-bearing table is local sensitive data. It is written under ignored
`data/` and must never be committed, copied into tests, printed, or included in
public reports. The aggregate quality report contains no identifiers.

## Relationship invariants

The extractor builds these links:

```text
Patient resource id -> Patient identifier (subject_id)
Hospital Encounter resource id -> hospital identifier (hadm_id) + Patient
ICU Encounter resource id -> ICU identifier (stay_id) + parent hospital Encounter + Patient
Observation -> Patient + Encounter -> exactly one ICU stay
```

An Observation that directly references an ICU Encounter uses that stay only when
the Patient references agree. An Observation referencing a hospital Encounter is
mapped only when its timestamp falls within exactly one child ICU period for the
same Patient. No-candidate and multiple-candidate cases are rejected explicitly.

The configured identifier systems are:

- Patient: `http://mimic.mit.edu/fhir/mimic/identifier/patient`
- Hospital Encounter:
  `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp`
- ICU Encounter:
  `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`

## Unit and value preservation

The extractor never overwrites `numeric_value` or `original_unit`. Normalized data
is stored separately. Fahrenheit is converted with `(°F - 32) × 5 / 9` only when
the original unit or UCUM code explicitly identifies Fahrenheit.

Canonical units are:

- heart rate: `beats/min`
- respiratory rate: `breaths/min`
- blood pressure: `mmHg`
- oxygen saturation: `percent`
- temperature: `degrees Celsius`
- oxygen flow: `L/min`

Oxygen flow is not treated as FiO2 or as a generic supplemental-oxygen indicator.

## Output behavior

`scripts/extract_canonical_vitals.py` accepts `--fhir-dir`, `--output`,
`--quality-report`, and required `--format {parquet,csv}`. A Parquet request is
written as Parquet when `pyarrow` is available. Otherwise, the extractor writes a
CSV with the same stem and records `"output_format": "csv"` in the aggregate
quality report.

Rows are deterministically sorted by local entity keys, observation time, code, and
original numeric value. This ordering supports reproducible development artifacts;
it is not hourly aggregation or duplicate resolution.

## Quality and safety boundaries

The report records aggregate resources, selected rows, rejection reasons, entity
counts, relationship-index validation, unit conversions, and physiological-range
exclusions. It never records a rejected resource, row, reference, raw identifier, or
hashed identifier.

Physiological ranges in `configs/fhir_vital_signs.yaml` are provisional data-quality
bounds, not clinical decision thresholds. Excluded observations are counted but not
written to the canonical table.
