# DeepVital Phase 2 baseline model card

## Intended use

Research-only benchmarking of sustained hypotension prediction in the MIMIC-IV
FHIR demo cohort. DeepVital is not a medical device and these outputs are not
validated for clinical care or patient-level decisions.

## Frozen prediction task

Predictors cover the 12 hours ending at prediction time `t`. The outcome is MAP
below 65 mmHg for at least two consecutive hourly observations in `t+1` through
`t+6`; MAP at `t` is not part of the outcome. Windows require complete future
MAP and never cross ICU stays. The existing deterministic patient split is
70%/15%/15% for train/validation/test.

## Models

Clinical comparators include training prevalence, current and previous MAP,
three- and six-hour MAP minima and means, MAP change and slope, shock index, and
modified shock index. Conventional baselines are prior dummy classification,
logistic regression, Gaussian Naive Bayes, and histogram gradient boosting.

Logistic regression and Gaussian Naive Bayes use median imputation and scaling
inside pipelines fitted on train only. Histogram gradient boosting handles
missing values natively. No post-hoc calibration model was fitted.

## Selection and evaluation

Selection used validation AUPRC, with Brier score as the tie-breaker. Thresholds
were locked on validation: 0.5, Youden index, and a sensitivity target near
0.80. Model name is the deterministic final tie-break if both metrics are equal.
Test was opened only after the selection record was written. Confidence
intervals use 1,000 deterministic patient-cluster bootstrap replicates.

## Limitations

- The demo cohort has only 100 patients and the test set has 15 patients.
- Repeated windows within a stay are correlated; patient bootstrap addresses
  clustering but uncertainty remains wide.
- Validation and test prevalence differ materially.
- Neutral risk 0.5 is used when a transparent clinical score is unavailable.
- Results are internal validation on a demo dataset, not external validation.
- Association and predictive utility do not imply causal importance.
