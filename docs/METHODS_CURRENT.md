# Current methods

## Study design and data source

DeepVital was developed as a retrospective methodological pipeline for predicting
sustained hypotension from longitudinal ICU vital signs. The current study used the
MIMIC-IV Clinical Database Demo on FHIR 2.1.0. All patients in this demonstration
dataset were treated as development data. The analysis did not include an
independent confirmatory cohort, external validation population, or prospective
evaluation.

FHIR resources were stored locally as gzip-compressed newline-delimited JSON. The
inventory and extraction routines streamed one resource at a time. Patient,
hospital Encounter, ICU Encounter, and Observation relationships were reconstructed
locally. Each supported observation was assigned to one patient, admission, and ICU
stay; inconsistent, absent, or ambiguous relationships were rejected and counted
in aggregate. Public reports did not contain patient-level records or identifiers.

## Canonical physiological representation

The canonical extraction represented heart rate, respiratory rate, systolic blood
pressure, diastolic blood pressure, MAP, peripheral oxygen saturation, temperature,
and oxygen flow. Mapping required the configured FHIR coding system and exact code.
Original numeric values and units were retained alongside normalized values and
units. Fahrenheit values were converted to degrees Celsius through an explicit unit
rule. Provisional physiological plausibility ranges excluded values outside
configured limits. Oxygen flow was retained in litres per minute and was not
interpreted as FiO2.

The extraction retained 89,415 observations representing 100 patients, 128
hospital admissions, and 140 ICU stays. Invasive, non-invasive, and alternate
arterial-pressure codes were mapped to shared variables; no clinically validated
source-priority hierarchy was applied.

## Hourly processing and missing data

The canonical cohort used the administrative period of each FHIR ICU Encounter to
define the hourly grid. Observations outside the exact period were excluded. Each
stay was processed independently, and multiple measurements for the same variable
and hour were aggregated using the median.

For each variable-hour, the representation retained the observed median, number of
measurements, observation indicator, missingness indicator, bounded-forward-filled
value, forward-fill indicator, and elapsed hours since the last real observation.
Forward fill was restricted to two hours within an ICU stay. Backward filling and
interpolation using future observations were prohibited.

## Prediction windows and outcome

At each prediction time \(t\), predictors were derived from the 12 hourly rows
spanning \(t-11\) through \(t\). Features included current and previous values,
change, trailing distributional summaries and slope, observation counts, missing
proportions, time since the last observation, pulse pressure, and shock index.
Patient, admission, stay, window, timestamp, split, label, and future-value fields
were excluded from model predictors.

The primary outcome was MAP strictly below 65 mmHg for at least two consecutive
observed hourly values during \(t+1\) through \(t+6\). MAP at \(t\) was not included
in the outcome, and a MAP value equal to 65 mmHg did not qualify. Forward-filled MAP
was not accepted as outcome evidence. All six future MAP hours were required;
otherwise the candidate window was excluded.

## Cohort-route decision

An earlier observation-bounded implementation constructed grids from the first to
the last supported vital-sign hour and produced 12,309 hourly rows and 8,872
eligible windows. The canonical administrative route produced 12,502 hourly rows
and 8,970 windows. The latter was selected because it defines time at risk through
the ICU Encounter rather than charting activity, validates FHIR relationships, and
provides an auditable rule for excluding out-of-period observations. Historical
artifacts from the earlier route were preserved and explicitly labeled.

## Candidate models and clinical benchmarks

The conventional candidate set comprised logistic regression, Gaussian Naive
Bayes, and Histogram Gradient Boosting. Nested candidate variants used logistic
regression C values of 0.1 and 1.0, Gaussian Naive Bayes variance-smoothing values
of 1e-10 and 1e-9, and Histogram Gradient Boosting learning rates of 0.03 and 0.05.
Median imputation and scaling were encapsulated within applicable pipelines and
fitted on training folds only. Histogram Gradient Boosting handled missing values
natively. No post-hoc calibration model was fitted.

The clinical comparators were training-fold prevalence, last MAP, six-hour mean
MAP, six-hour minimum MAP, MAP slope, shock index, and modified shock index. The MAP
and shock-index scores were monotonic sigmoid transformations bounded between zero
and one. These transformations preserved risk ordering but were not calibrated
probabilities. A score that could not be calculated received the prespecified
neutral value 0.5 in the primary analysis, with availability and complete-case
sensitivity results reported separately.

## Patient-grouped nested cross-validation

Internal validation used five outer folds and three inner folds grouped by patient.
All windows from a patient remained in one outer fold. Each patient was assigned to
exactly one outer fold, and every eligible window received exactly one out-of-fold
prediction. Candidate selection and threshold selection used inner-fold predictions
only. The outer fold was used exclusively to estimate performance for the strategy
selected without that fold.

The primary model-selection metric within the nested procedure was AUPRC, followed
by Brier score and model name as deterministic tie-breakers. Each outer fold retained
its inner-selected threshold. Pooled threshold-0.5 summaries were descriptive. The
procedure did not select a final model or final threshold.

## Prespecified Phase 3 incremental-value analysis

After the benchmark audit and holdout-protocol repair, Phase 3 addressed one frozen
question: whether a single interpretable multivariable strategy provided sufficient
incremental value over `map_mean_6h`. The sole candidate was L2 logistic regression
with 18 locked predictors, `solver="lbfgs"`, `class_weight="balanced"`,
`max_iter=1000`, and inner-fold selection between `C=0.1` and `C=1.0`.

The analysis reused the registered five outer and three inner patient-grouped folds.
Continuous inputs underwent median imputation and scaling within the applicable
training scope; binary missingness indicators passed through structurally complete.
Each eligible window received one outer OOF prediction, and patient overlap was
zero. Platt recalibration used inner OOF predictions from outer-training patients
only. Youden and target-sensitivity operating points were selected without using
outer-fold outcomes.

The primary estimand was candidate-minus-`map_mean_6h` AUPRC. Uncertainty used 1,000
paired patient-bootstrap replicates, retaining every window for each sampled
patient. Advancement required observed delta AUPRC of at least `+0.020`, a paired
interval lower bound above zero, valid OOF accounting, and no primary protocol
deviation. The `+0.020` value was a development relevance margin, not a p-value or
a clinically validated minimal important difference.

Prespecified secondary and robustness analyses covered AUROC, probability losses,
calibration, threshold metrics, patient-equal weighting, the 60/65/70-mmHg by
one/two/three-hour outcome grid, BP-source alternatives, benchmark availability,
and charting patterns. The two incomplete-future-MAP bounds failed because their
datasets included patients absent from the frozen fold manifest. The run was not
repeated to repair this disclosed sensitivity-analysis failure.

## Metrics and statistical analysis

Discrimination was summarized using AUROC and AUPRC. Brier score and log loss were
reported for probability outputs but not for uncalibrated clinical ranking scores.
Sensitivity, specificity, PPV, NPV, F1 score, and confusion counts were computed
using fold-specific inner-selected thresholds, with threshold-0.5 results reported
separately.

Uncertainty was estimated with 1,000 patient-cluster bootstrap replicates. Patients
were sampled with replacement, retaining all windows from each sampled patient.
Paired benchmark comparisons used identical patient samples and defined differences
as benchmark minus nested ML. Positive differences favored the benchmark for AUROC
and AUPRC; negative differences favored it for probability-loss metrics.

## Historical holdout and confirmatory safeguards

The historical 8,872-window test partition was accessed four times and was formally
reclassified as `development_holdout_v1`. Its metrics and access count were
preserved, but it was not interpreted as an untouched confirmatory holdout.

The current confirmatory state is pending. The confirmatory evaluator requires a
frozen model, feature schema and threshold, verifies protocol, cohort, model, and
metadata hashes, and rejects overlap with development patients. It records first
consumption and treats identical repetitions as technical reproductions. It does
not train or select models, hyperparameters, or thresholds. No confirmatory
evaluation has been executed.

## Reproducibility, ethics, and data use

Canonical metadata recorded the source-code commit and pre-run working-tree state,
generation time, configuration hash, input fingerprint, and output fingerprint.
Identifier-bearing data remained local and outside version control. Automated tests
used synthetic fixtures.

Ethics and data-use statements should be finalized according to the requirements of
the underlying dataset and the intended venue. No institutional review or exemption
is asserted here.
