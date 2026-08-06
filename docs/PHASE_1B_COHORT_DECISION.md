# Phase 1B canonical cohort decision

## Compared routes

The historical combined builder (`scripts/build_phase_1b_dataset.py`) groups
already-resolved canonical observations by patient, admission, and ICU stay but
constructs each grid from the first to last supported observation hour. It produced
12,309 hourly rows and 8,872 eligible windows. It does not independently reload the
FHIR ICU encounter period and reports zero observations outside the ICU period by
construction.

The administrative route combines `build_hourly_dataset.py` and
`build_modeling_dataset.py`. It resolves every canonical stay against the FHIR ICU
Encounter, verifies patient and admission consistency, grids from the containing
hour of `period.start` through the containing hour of `period.end`, and excludes
observations outside the exact period. It produced 12,502 hourly rows, excluded 270
out-of-period observations, and retained 8,970 windows.

The administrative route has more grid hours despite excluding observations
because it represents clinically valid ICU time before the first or after the last
supported vital measurement. Differences then propagate through bounded forward
fill, complete-future-MAP eligibility, and window counts.

## Decision

The administrative ICU-period-bounded route is canonical. The choice is based on
the explicit clinical time at risk, FHIR Encounter consistency, auditable exclusion
of out-of-period observations, and reproducible patient/admission/stay validation.
It is not based on the number of windows or downstream model performance.

This decision does not establish that every boundary is clinically perfect. FHIR
period accuracy, hour-floor/ceiling semantics, blood-pressure source pooling, and
selection induced by complete future MAP remain limitations requiring sensitivity
analysis.

## Impact and migration

- Historical Phase 1B and Phase 2 artifacts remain unchanged and are labeled as
  `development_holdout_v1` based on the 8,872-window cohort.
- Canonical Phase 1B v1 contains 12,502 hourly rows and 8,970 eligible windows.
- `scripts/build_canonical_cohort.py` is the only official canonical command.
- `scripts/build_hourly_dataset.py` and `scripts/build_modeling_dataset.py` remain
  internal stages used by that command.
- `scripts/build_phase_1b_dataset.py` is deprecated. It refuses execution unless
  `--allow-legacy-builder` is supplied explicitly.
- New model development must use the canonical dataset and internal patient-grouped
  validation. Historical metrics must not be silently replaced.

## Canonical command

```bash
python scripts/build_canonical_cohort.py \
  --canonical-input data/processed/canonical_vitals.csv \
  --fhir-dir data/mimic-iv-clinical-database-demo-on-fhir-2.1.0/fhir
```

The command writes new canonical-v1 private outputs and new aggregate reports; it
does not overwrite historical Phase 1B or Phase 2 results.

