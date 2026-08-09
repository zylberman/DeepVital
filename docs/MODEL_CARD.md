# DeepVital current development-strategy model card

## Status and intended use

This card describes the strategy decision after the completed prespecified Phase 3
development analysis. DeepVital is a retrospective research project, not a medical
device, production model, or clinical decision-support system. No strategy in this
repository is validated for patient-care decisions.

## Prediction task

At prediction time `t`, the task uses information from `t-11` through `t` to predict
observed hourly MAP strictly below 65 mmHg for at least two consecutive hours in
`t+1` through `t+6`. MAP at `t` is not part of the outcome. Primary windows require
all six future MAP hours and cannot cross a patient, admission, or ICU stay.

## Retained parsimonious development strategy

`map_mean_6h` is the arithmetic mean of calculable MAP values in the six predictor
hours ending at `t`, mapped through the existing monotonically decreasing sigmoid
risk score. It is an uncalibrated ranking score, not a probability.

Phase 3 retained `map_mean_6h` because the sole multivariable candidate did not meet
the frozen advancement rule. Retention means preferred parsimony for subsequent
development and independent evaluation; it does not establish clinical validity,
optimality, causal importance, or transportability.

## Non-advancing multivariable candidate

The sole Phase 3 candidate was L2 logistic regression with 18 locked predictors,
`solver="lbfgs"`, `class_weight="balanced"`, `max_iter=1000`, and inner-CV selection
between `C ∈ {0.1, 1.0}`. Continuous inputs underwent training-fold median
imputation and scaling. Five binary current-hour missingness indicators passed
through structurally complete.

The candidate increased raw AUPRC from 0.6218694691 to 0.6293981556. Delta AUPRC
was `+0.0075286864`, with paired patient-bootstrap 95% interval `+0.0004996287` to
`+0.0171297719`. This is evidence of a small positive incremental signal, not of no
incremental value or inferiority.

The observed gain was below the prespecified `+0.020` development relevance margin,
so the candidate did not advance. The margin is not a p-value and is not a
clinically validated minimal important difference.

## Calibration and thresholds

Platt recalibration was fitted through the frozen leakage-controlled development
procedure. The calibrated candidate had Brier score 0.1114882686 and log loss
0.3619400064. Recorded development operating points were:

- fixed 0.5: `0.5`;
- target sensitivity 0.80: `0.3208213008`;
- Youden: `0.3775406688`.

These thresholds are development operating points only. They are not deployment
thresholds, clinically optimal thresholds, or evidence of clinical utility.

## Evaluation data and safeguards

The evaluation used 8,970 windows from 92 eligible development patients in five
outer and three inner patient-grouped folds. All windows from a patient stayed
together, patient overlap was zero, and each window received one outer OOF
prediction. The 8,970 windows are correlated observations, not independent people.

There was one formal preregistered Phase 3 development execution. The run was not
repeated after results were observed. The confirmatory state remains
`confirmatory_test_pending`.

## Key limitations

- The source is the small MIMIC-IV-on-FHIR demonstration environment.
- Evidence is retrospective and development-only.
- No external, prospective, confirmatory, workflow, or clinical-impact evaluation
  has been completed.
- The two incomplete-future-MAP sensitivity analyses failed because their datasets
  contained patients absent from the frozen fold manifest.
- Predictive performance and coefficients do not imply causality.
- Neither the retained benchmark nor the logistic candidate is ready for clinical
  deployment.

## Historical Phase 2 record

The earlier 8,872-window `development_holdout_v1` model card state is preserved in
the Phase 2 reports and Git history. That partition was accessed four times and is
development evidence, not an untouched confirmatory holdout.
