# Frozen evaluation protocol

**Protocol version:** `deepvital-evaluation-v1`
**Current state:** `confirmatory_test_pending`
**Intended use:** research only; not for clinical decision-making

## Population and cohort

Development uses authorized ICU encounters resolved to `subject_id`, `hadm_id`,
and `stay_id`. Canonical time at risk is the FHIR ICU Encounter administrative
period. Observations outside that exact period are excluded. Windows never cross a
patient, admission, or ICU stay.

## Outcome and prediction task

- predictor window: 12 hourly rows, `t-11` through `t`;
- prediction horizon: `t+1` through `t+6`;
- event: observed hourly MAP strictly below 65 mmHg for at least two consecutive
  future hours;
- all six future MAP hours must be observed for the primary analysis;
- forward-filled MAP is not outcome evidence.

## Predictors and missing data

The prespecified feature families are current/previous values, change, backward-
looking mean/median/minimum/maximum/standard deviation/slope, observed counts,
missing proportions, observation/forward-fill indicators, time since last real
measurement, pulse pressure, and shock index. Identifiers, timestamps, split,
future values, and label are excluded. Forward fill is limited to two hours;
backward fill and future-dependent interpolation are prohibited.

Median imputers and scalers, when applicable, are pipeline components fitted only
inside the current training fold. There is no data-driven feature selection in v1;
the feature set is prespecified. Any future selector must be fitted inside the inner
training fold.

## Candidate models and selection

Candidates are clinical MAP/shock-index benchmarks, dummy prevalence, logistic
regression, Gaussian Naive Bayes, and histogram gradient boosting with configuration-
registered hyperparameters. Internal development uses patient-grouped nested cross-
validation. Hyperparameter or candidate selection occurs in inner folds only.

The primary comparison metric is AUPRC. The secondary metric is Brier score,
followed by model name as deterministic tie-break if a later development decision
uses them. The primary fold-specific threshold is selected by Youden index from
inner-fold predictions. Fixed 0.5 and target-sensitivity 0.80 are descriptive or
secondary thresholds. An outer fold is never used to choose its own model or
threshold.

Clinical benchmarks and ML candidates use the same outer and inner patient groups,
windows, labels, and patient-cluster bootstrap. Missing clinical scores receive an
explicit neutral risk of 0.5; no population imputer or scaler is fitted for these
transparent scores. This comparison does not itself select a final model.

Each outer fold retains its inner-CV threshold. Pooled threshold-0.5 metrics are
descriptive only. No single threshold is frozen at this stage. After the model
strategy is chosen using development evidence, its final threshold will be
estimated from out-of-fold predictions across all development patients, before any
confirmatory dataset is accessed.

## Metrics and uncertainty

Primary performance metric: AUPRC. Secondary metrics include AUROC, sensitivity,
specificity, PPV, NPV, F1, confusion counts, and prevalence. Brier score, log loss,
calibration intercept/slope, and calibration curves apply only to interpretable
probability outputs, never to uncalibrated ranking scores. Confidence intervals use
patient-cluster bootstrap, retaining every window for each sampled patient.

Every patient is assigned to exactly one outer evaluation fold, all windows from a
patient remain together, and each eligible window receives exactly one OOF
prediction. Duplicate external predictions are prohibited and checked at runtime.

The predeclared missing-score primary strategy is neutral risk 0.5. For every
clinical benchmark, aggregate availability indicators and a complete-case
sensitivity analysis are also reported. The strategy is not selected after viewing
which result performs better.

## Planned sensitivity and subgroup analyses

Sensitivity analyses will examine MAP thresholds 60/65/70, one/two/three
consecutive low hours, incomplete-future-MAP handling, BP source pooling, and
patient-equal weighting. Prespecified exploratory subgroups, when available and
adequately sized, are sex, age group, ICU type, and admission type. These analyses
must be labeled exploratory and cannot redefine the primary result.

## Evaluation roles

- `development`: all current 100 MIMIC-IV demo patients and historical artifacts.
- `internal_validation`: outer-fold predictions from patient-grouped nested CV;
  label `internal_nested_cross_validation`.
- `confirmatory_test`: one frozen model and threshold evaluated on completely new
  patients after protocol and cohort registration.
- external validation: a future evaluation on an independently sourced setting;
  it is not synonymous with the confirmatory test.

## Confirmatory independence and lock

A dataset is confirmatory only when none of its patients appeared in feature
development, preprocessing decisions, training, internal validation, threshold
selection, debugging, or historical holdout evaluation. A new seed over the same
100 patients is not independent.

Before access, the protocol hash, cohort fingerprint, frozen serialized model hash,
feature schema, and threshold must be registered. The confirmatory evaluator cannot
train, select candidates, or modify the threshold. Its first successful execution
marks the cohort consumed. Later executions require identical hashes and are
technical reproductions, not new selections.

Changing the primary metric or selection procedure after access is a protocol
deviation and must be reported with timing, rationale, and affected analyses.
