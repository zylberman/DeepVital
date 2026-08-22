# Study methods extraction

## Study identity

**Manuscript-ready text:** “DeepVital was a retrospective, leakage-resistant
internal development study using the MIMIC-IV Clinical Database Demo on FHIR 2.1.0.
Phase 3 tested whether a prespecified multivariable logistic model added sufficient
discrimination beyond recent mean arterial pressure alone to justify additional
complexity.”

- Audited version: commit `58c0ab1`, tag `phase3-final-closure-v1`.
- Phase 3 formal execution timestamp: `2026-08-09T04:25:24.406193+00:00`.
- Intended use: methodological research only; no patient-care use.
- Design role: preregistered internal development comparison, not confirmatory.
- Prediction time: each eligible hourly time `t` within an ICU stay.

## Data source and participants

The source is the MIMIC-IV Clinical Database Demo on FHIR 2.1.0, stored locally as
gzip-compressed NDJSON. Relevant FHIR R4 resources were Patient, hospital Encounter,
ICU Encounter, and Observation. Exact clinical date range, official citation,
credentialing statement, deidentification description, and dataset license wording
are not contained in publication-ready form and require primary-source verification.

| Flow item | Count | Source |
|---|---:|---|
| Canonical patients | 100 | `canonical_cohort_metadata.json` |
| Hospital admissions | 128 | same |
| ICU stays | 140 | same |
| Candidate prediction times | 10,185 | `canonical_v1/cohort_flow.json` |
| Eligible windows | 8,970 | same |
| Positive/negative windows | 1,774 / 7,196 | same |
| Patients with eligible windows | 92 | Phase 3 OOF invariants |

Exclusion counters are non-exclusive construction counters and must not be summed
as unique people: insufficient 12-hour history 1,514; incomplete future horizon
803; insufficient future MAP assessment 1,215; minimum observed data 0; invalid ICU
key 0. The repository does not report a mutually exclusive patient-level exclusion
flow, patients with at least one positive outcome, or median/IQR windows per patient.
The sensitivity report provides window-count range 1–650 and mean 97.5 per patient.

## FHIR processing and variables

Observations were linked to patient, admission, and ICU stay. The administrative
ICU Encounter period defined the hourly grid. Duplicate variable measurements in an
hour were summarized by median. Original values/units were retained; configured
normalized units were beats/min, breaths/min, mmHg, percent, degrees Celsius, and
L/min. Fahrenheit was explicitly converted to Celsius. Provisional physiological
ranges were HR 20–300, RR 1–100, SBP 30–350, DBP 10–250, MAP 20–300, SpO2 0–100,
temperature 25–45 °C, and oxygen flow 0–100 L/min.

The primary cohort pooled invasive, non-invasive, and alternate BP codes within
the hourly median. Phase 3 separately evaluated invasive-preferred and
non-invasive-only constructions.

## Missingness and windows

No backward fill was permitted. Forward fill was limited to two hours within an
ICU stay and retained observed, missing, forward-filled, measurement-count, and
hours-since-last-real-observation fields. Phase 3 continuous predictors were median
imputed and standardized inside applicable training folds. Five binary current-hour
missingness indicators were passed through and were required to be structurally
complete.

Predictor history was the 12 hourly rows `t-11,...,t`; the future horizon was
`t+1,...,t+6`. The stride was one hour because every eligible hourly prediction
index was considered. Windows could overlap within a patient but could not cross a
patient, admission, or ICU stay.

## Locked Phase 3 predictor dictionary

All predictors were available no later than `t`. Continuous predictors were
training-fold median-imputed and scaled; the final five binary indicators were not
scaled by the Phase 3 column transformer.

| Code name | Clinical definition | Unit / scale | Temporal derivation |
|---|---|---|---|
| `map_mean_6h` | Mean calculable MAP in six hours ending at `t` | mmHg | Raw mean underlying comparator |
| `mean_arterial_pressure_current` | Current MAP | mmHg | hour `t` |
| `mean_arterial_pressure_rolling_slope` | MAP linear trend | mmHg/hour | trailing 12-hour feature window |
| `heart_rate_current` | Current heart rate | beats/min | hour `t` |
| `systolic_bp_current` | Current systolic BP | mmHg | hour `t` |
| `shock_index` | Heart rate / systolic BP | ratio | current hour |
| `respiratory_rate_current` | Current respiratory rate | breaths/min | hour `t` |
| `oxygen_saturation_current` | Current pulse oximetry | percent | hour `t` |
| `mean_arterial_pressure_proportion_missing` | MAP missing fraction | proportion | trailing 12 hours |
| `heart_rate_proportion_missing` | HR missing fraction | proportion | trailing 12 hours |
| `systolic_bp_proportion_missing` | SBP missing fraction | proportion | trailing 12 hours |
| `respiratory_rate_proportion_missing` | RR missing fraction | proportion | trailing 12 hours |
| `oxygen_saturation_proportion_missing` | SpO2 missing fraction | proportion | trailing 12 hours |
| `mean_arterial_pressure_h0_missing` | Current MAP missing | binary | hour `t` |
| `heart_rate_h0_missing` | Current HR missing | binary | hour `t` |
| `systolic_bp_h0_missing` | Current SBP missing | binary | hour `t` |
| `respiratory_rate_h0_missing` | Current RR missing | binary | hour `t` |
| `oxygen_saturation_h0_missing` | Current SpO2 missing | binary | hour `t` |

FHIR code mappings are in `configs/fhir_vital_signs.yaml`; derived features do not
map one-to-one to a single FHIR code. The set deliberately excluded identifiers,
timestamps, outcomes, future values, split labels, temperature, oxygen flow, DBP,
and unlisted feature families.

## Outcome

For future hourly observed MAP values \(M_{t+1},...,M_{t+6}\), the label was 1 if
there existed adjacent hours \(j,j+1\) with both values strictly <65 mmHg; otherwise
0. All six future MAP hours had to be observed. MAP at `t` and forward-filled MAP
were not outcome evidence. This complete ascertainment can induce selection bias.

## Candidate, comparator, and validation

- Candidate: logistic regression, L2 penalty, `lbfgs`, balanced class weights,
  maximum 1,000 iterations; inner selection of `C ∈ {0.1,1.0}` by mean AUPRC with
  `C=0.1` favored on ties.
- Comparator: `map_mean_6h`, transformed to a monotonically decreasing bounded
  ranking score centered at 65 mmHg with scale 10; not a calibrated probability.
- Validation: five deterministic outer and three inner patient-grouped folds,
  seed `20260726`. The registered private manifest fixed assignments.
- Selection/preprocessing: inner/training data only. Each eligible window received
  one outer OOF prediction; patient overlap was zero.
- Calibration: prespecified Platt logistic calibration fitted on outer-training
  inner OOF candidate scores, then applied to outer-fold predictions.
- Thresholds: fold-specific Youden threshold from inner OOF scores; target
  sensitivity 0.80 secondary; 0.5 descriptive. Higher threshold resolved Youden ties.

## Metrics and inference

Primary metric was window-weighted OOF AUPRC. Secondary metrics included AUROC,
Brier score and log loss for probability outputs, calibration intercept/slope,
sensitivity, specificity, PPV, NPV, F1, and confusion counts. Paired percentile
95% intervals used 1,000 patient-cluster bootstrap samples with seed `20260726`,
retaining all windows for each sampled patient. No multiplicity-adjusted
confirmatory hypothesis test was claimed.

Advancement required all of: delta AUPRC ≥0.020; paired CI lower bound >0; valid
OOF accounting; and no primary-impacting protocol deviation. Secondary metrics
could not rescue failure of the primary rule.
