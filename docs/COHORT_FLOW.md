# Phase 1B Cohort Flow

This report describes the local MIMIC-IV FHIR demo and contains aggregate values
only.

## Hourly construction

| Step | Count |
|---|---:|
| Canonical observations read | 89,415 |
| Observations outside exact ICU period | 270 |
| ICU stays processed | 140 |
| Patients represented | 100 |
| Hospital admissions represented | 128 |
| Hourly rows | 12,502 |
| Real hourly variable cells | 76,049 |
| Duplicate measurements collapsed | 13,096 |
| Forward-filled cells | 9,435 |
| Missing after bounded forward fill | 14,532 |

## Window and label flow

| Step | Count |
|---|---:|
| Prediction hours excluded for insufficient 12-hour history | 1,514 |
| Prediction hours excluded for incomplete six-hour temporal horizon | 803 |
| Candidate prediction times | 10,185 |
| Excluded for insufficient future MAP assessment | 1,215 |
| Excluded for minimum observed predictor data | 0 |
| Eligible labeled windows | 8,970 |
| Positive windows | 1,774 |
| Negative windows | 7,196 |
| Event prevalence | 19.78% |

## Patient-level split

| Split | Assigned patients | Patients with windows | Windows | Positive | Prevalence |
|---|---:|---:|---:|---:|---:|
| Train | 70 | 63 | 5,697 | 1,100 | 19.31% |
| Validation | 15 | 14 | 1,701 | 456 | 26.81% |
| Test | 15 | 15 | 1,572 | 218 | 13.87% |

Patient overlap across splits is zero. The prevalence imbalance reflects the small
demo cohort; the split is deterministic but not outcome-stratified.

## Interpretive limitations

- Counts refer to overlapping windows, not independent patients or unique events.
- Strict complete-future-MAP assessment may select more intensively monitored
  periods.
- BP source pooling remains provisional.
- The small demo split is unsuitable for clinical-performance claims.
