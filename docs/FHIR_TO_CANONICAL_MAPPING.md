# FHIR-to-Canonical Mapping

**Dataset basis:** aggregate findings from the local MIMIC-IV FHIR demo inventory  
**Phase:** 1A only

Mappings are keyed by both code system and exact code. Display labels document the
inventory finding but are not used to guess or select variables.

## Supported Chartevents codes

Code system:
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`

| Code | Inventory display | Canonical variable | Accepted source unit |
|---:|---|---|---|
| 220045 | Heart Rate | `heart_rate` | bpm |
| 220210 | Respiratory Rate | `respiratory_rate` | insp/min |
| 220050 | Arterial Blood Pressure systolic | `systolic_bp` | mmHg |
| 220179 | Non Invasive Blood Pressure systolic | `systolic_bp` | mmHg |
| 225309 | ART BP Systolic | `systolic_bp` | mmHg |
| 220051 | Arterial Blood Pressure diastolic | `diastolic_bp` | mmHg |
| 220180 | Non Invasive Blood Pressure diastolic | `diastolic_bp` | mmHg |
| 225310 | ART BP Diastolic | `diastolic_bp` | mmHg |
| 220052 | Arterial Blood Pressure mean | `mean_arterial_pressure` | mmHg |
| 220181 | Non Invasive Blood Pressure mean | `mean_arterial_pressure` | mmHg |
| 225312 | ART BP Mean | `mean_arterial_pressure` | mmHg |
| 220277 | O2 saturation pulseoxymetry | `oxygen_saturation` | % |
| 223761 | Temperature Fahrenheit | `temperature` | °F |
| 223762 | Temperature Celsius | `temperature` | °C |
| 223834 | O2 Flow | `oxygen_flow` | L/min |
| 227287 | O2 Flow (additional cannula) | `oxygen_flow` | L/min |
| 227582 | BiPap O2 Flow | `oxygen_flow` | L/min |

These 17 code/display/value-type combinations were confirmed in
`reports/fhir_chartevents_codes.csv` as `valueQuantity`. Chartevents contained no
components, but component `code` plus `valueQuantity` extraction is supported and
tested synthetically for compatible future FHIR sources.

## FHIR field mapping

| Canonical field | FHIR source |
|---|---|
| `subject_id` | Patient `identifier.value` for the MIMIC Patient system |
| `hadm_id` | parent hospital Encounter `identifier.value` |
| `stay_id` | ICU Encounter `identifier.value` |
| `observation_time` | Observation `effectiveDateTime` |
| `source_resource` | fixed source-family name for the input file |
| `code_system` | Observation or component `code.coding.system` |
| `observation_code` | Observation or component `code.coding.code` |
| `observation_display` | Observation or component `code.coding.display` |
| `normalized_variable` | `configs/fhir_vital_signs.yaml` |
| `numeric_value` | `valueQuantity.value` |
| `original_unit` | `valueQuantity.unit` |
| `normalized_value` | explicit conversion from `configs/unit_conversions.yaml` |
| `normalized_unit` | canonical unit from `configs/unit_conversions.yaml` |

## Explicit rejection reasons

- malformed or non-object JSON;
- missing or invalid timestamp;
- missing Patient or Encounter reference;
- Patient/Encounter disagreement;
- no ICU candidate;
- multiple timestamp-compatible ICU candidates;
- missing code or numeric value;
- present but unsupported non-quantity value type;
- unsupported coding system/code;
- unsupported or absent unit;
- value outside the configured physiological plausibility range.

Only aggregate reason counts are reported.

## Current methodological limitations

- Invasive, non-invasive, and alternate arterial BP codes map to common variables,
  but no precedence, deduplication, or simultaneous-measurement rule is applied.
- Physiological bounds are provisional and require clinical/data-dictionary review.
- The mapping is confirmed against the aggregate FHIR inventory, not yet against an
  independently versioned official D_ITEMS dictionary.
- Direct ICU Encounter references are Patient-validated but not rejected solely
  because an observation timestamp lies outside the recorded ICU period. The next
  cohort-validity phase must quantify and decide how to handle such discrepancies.
- Observation `issued` is not substituted for missing `effectiveDateTime`.
- No timezone sensitivity analysis has been performed beyond parsing timestamps and
  normalizing them to UTC.
- Oxygen-flow measurements do not identify FiO2 and do not prove that oxygen was
  delivered continuously.

## Next phase

The recommended next phase is canonical-data validation and cohort preparation:
review code/range choices, quantify direct-reference time-bound discrepancies,
define duplicate/source precedence, and add cohort-flow checks. Hourly aggregation,
missing-data processing, prediction windows, and future-only outcome labeling should
begin only after those decisions are documented and tested.
