# Phase 1B Data-Leakage Safeguards

> **Historical Phase 1B audit.** The invariants remain relevant, but the numerical
> completion evidence belongs to the legacy 8,872-window route. Current evidence is
> documented in `RESEARCH_PROTOCOL.md` and `reports/canonical_v1/`.

## Implemented invariants

- Every hourly grid and window is constructed within one `subject_id`, `hadm_id`,
  and `stay_id`.
- FHIR ICU Encounter start/end timestamps bound the hourly grid.
- Predictors end at `t`; future hours are not emitted as predictor columns.
- The outcome begins at `t+1`.
- Rolling and derived features receive only the closed trailing history through
  `t`.
- Forward filling uses only earlier real measurements in the same ICU stay and is
  capped independently by variable.
- Backward filling and future-dependent interpolation are configuration-validated
  as disabled.
- Future MAP labels use real hourly aggregates, never forward-filled MAP.
- Missing future MAP produces exclusion, not a negative label.
- Train, validation, and test assignments are made by `subject_id`.
- Every admission, ICU stay, and window for a patient receives the same split.
- A runtime assertion fails on patient overlap.
- The split seed and proportions are fixed in configuration.
- No scaler, imputer, feature selector, calibration model, threshold, or model is
  fit in Phase 1B.

## Completion-audit evidence

The audited 8,872-window build passed all three reconciliation checks:

- `12,309 × 8 = 76,190 + 8,846 + 13,436`;
- `10,008 = 8,872 + 1,136`;
- `8,872 = 1,759 + 7,113`.

The private split manifest assigns 100 patients using seed `20260726`. Aggregate
split reporting confirms zero patient overlap. Patients without eligible windows
remain assigned in the manifest and are distinguished from patients contributing
windows.

## Privacy boundary

Hourly data, windows, and the split manifest are private local artifacts under
ignored `data/processed/`. Public reports contain counts and proportions only.
Console output contains only aggregate totals.

## Remaining safeguards before modeling

- Verify split stability and outcome balance on larger cohorts.
- Fit all preprocessing transformations on training patients only.
- Use validation patients for calibration and decision thresholds only.
- Keep the test split untouched until final evaluation.
- Decide BP source precedence before interpreting pooled hourly BP values.
