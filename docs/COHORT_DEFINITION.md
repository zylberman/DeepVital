# DeepVital Phase 1B Cohort and Window Definition

**Status:** Implemented and tested for the local MIMIC-IV FHIR demo  
**Intended use:** Retrospective research only; not for clinical decision-making

This phase transforms the private canonical observation table into stay-bounded
hourly data and future-labeled retrospective windows. It does not split patients,
fit preprocessing statistics, train a model, select a threshold, or evaluate model
performance.

## Input population

The input is `data/processed/canonical_vitals.csv` from Phase 1A. Every row already
contains a locally resolved `subject_id`, `hadm_id`, and `stay_id`. Processing is
grouped by the complete three-key identity and never combines rows across an ICU
stay, hospital admission, or patient.

The actual Phase 1B run represented:

- 100 patients;
- 128 hospital admissions;
- 140 ICU stays;
- 89,415 canonical observations.

These counts are aggregate-only. Identifier-bearing outputs remain under ignored
`data/processed/`.

## Hourly aggregation

Timestamps are normalized to UTC and floored to the containing clock hour. Within
each ICU stay, hour, and normalized variable, duplicate values are aggregated using
the median. The run produced 12,309 hourly rows and collapsed 13,225 duplicate
values.

The following eight variables are represented:

- heart rate;
- respiratory rate;
- systolic blood pressure;
- diastolic blood pressure;
- mean arterial pressure;
- oxygen saturation;
- temperature;
- oxygen flow.

Invasive, non-invasive, and alternate arterial blood-pressure codes currently map
to the same normalized BP variables. Their within-hour median is therefore a
provisional pooling rule, not a clinically validated source-precedence rule.

## Missing-data representation

For each variable and hour, the hourly table stores:

- `*_observed_value`: median of real measurements, otherwise empty;
- `*_value`: observed value or bounded forward-filled value;
- `*_missing`: 0 for a real hourly measurement and 1 otherwise;
- `*_hours_since`: hours since the last real observation, empty when no prior
  observation exists in that ICU stay.

Forward filling is limited to two hours. Values are never backward filled. A
forward-filled value retains `missing=1`, so real and carried-forward observations
remain distinguishable. Time since observation continues to increase after the
forward-fill limit even though the value becomes missing.

The actual run contained 8,846 forward-filled cells and 13,436 missing cells that
remained unfilled.

## Retrospective predictor window

For a prediction time `t`, predictors contain exactly 12 hourly rows:

```text
t-11, t-10, ..., t-1, t
```

Each window includes the bounded-forward-filled value, missingness indicator, and
time-since-last-real-observation for all eight variables at every input hour. No
measurement after `t` enters predictors. Windows are constructed separately within
each ICU stay.

## Primary future outcome

The primary label evaluates only real hourly MAP values in:

```text
t+1, t+2, ..., t+6
```

The label is positive when MAP is below 65 mmHg for at least two consecutive future
hours. MAP at `t` is not part of the label. Forward-filled MAP is never used to
create the outcome.

The primary analysis requires all six future hours to contain a real hourly MAP
value. A missing future MAP makes the label unknown and excludes that candidate
window.

The actual build produced:

- 10,008 candidate windows;
- 1,136 exclusions for incomplete future MAP;
- 8,872 labeled windows;
- 1,759 positive labels;
- event prevalence 19.83%.

This prevalence describes overlapping retrospective windows, not unique clinical
events or patients.

## Private outputs

- `data/processed/hourly_vitals.csv`: 12,309 rows and 36 columns;
- `data/processed/modeling_windows.csv`: 8,872 rows and 293 columns.

Both files contain local identifiers and must not be committed, logged, copied into
public examples, or treated as deidentified public data.

The public aggregate report is `reports/phase_1b_quality.json`.

## Known limitations

- The hourly grid begins at the first and ends at the last canonical vital-sign
  hour, not at independently loaded ICU admission/discharge bounds. Leading and
  trailing hours without any supported vital are therefore absent.
- BP source precedence and simultaneous invasive/non-invasive measurements remain
  unresolved.
- Duplicate aggregation uses the median across mapped sources; this requires
  sensitivity analysis before scientific inference.
- Complete future MAP is a strict primary-label requirement and may select for
  more frequently monitored periods.
- Overlapping windows are correlated. Future train/validation/test splitting must
  occur by patient before any fitting.
- No imputer, scaler, feature selection, calibration, or threshold selection has
  been fit.
- Oxygen flow is not FiO2 and is not a validated continuous supplemental-oxygen
  indicator.

## Recommended next action

Before model development, perform a Phase 1C validity review: incorporate or audit
ICU admission/discharge bounds, define BP source precedence, quantify label
selection caused by missing future MAP, create patient-disjoint train/validation/
test splits, and add leakage assertions. Fit no preprocessing transformation on the
full dataset.
