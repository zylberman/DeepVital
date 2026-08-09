# DeepVital Phase 3 protocol

## Prespecified Incremental-Value and Robustness Analysis

**Protocol identifier:** `deepvital-phase3-incremental-value-v1`
**Status:** FROZEN; no Phase 3 performance analysis has been executed
**Data role:** development only
**Confirmatory status:** `confirmatory_test_pending`
**Intended use:** retrospective methodological research only

> DeepVital is not a medical device or clinical decision-support system. This
> protocol defines a development analysis and cannot establish clinical utility,
> transportability, or confirmatory performance.

## 1. Purpose and primary research question

Phase 3 will determine whether one prespecified interpretable multivariable
strategy provides reproducible incremental predictive value beyond the six-hour
mean MAP benchmark for forecasting sustained hypotension.

The primary research question is:

> Does one prespecified interpretable multivariable strategy provide reproducible
> incremental predictive value beyond six-hour mean MAP?

This protocol must be reviewed, assigned a frozen Git commit, and fingerprinted
before any Phase 3 outcome, model, or sensitivity analysis is executed. Any later
change must be documented as an amendment with its timing, rationale, and effect on
interpretation. A post-analysis change cannot be represented as prespecified.

## 2. Evidence boundary and analysis population

Phase 3 will use only the canonical development cohort identified by
`reports/canonical_cohort_metadata.json` as `phase1b-canonical-v1`. The currently
versioned aggregate evidence records 100 development patients, of whom 92
contribute 8,970 eligible windows under the primary outcome definition. These
counts are evidence for planning; Phase 3 must verify them before fitting and abort
if the canonical input fingerprint or accounting differs from the registered
cohort.

All current MIMIC-IV-on-FHIR demo patients are development data. The historical
`development_holdout_v1` partition is not a confirmatory test and must not be
evaluated separately in Phase 3. No confirmatory or external dataset may be opened,
inspected, summarized, debugged against, or used to revise this protocol.

## 3. Prediction task and primary outcome

The primary predictor window remains the closed 12-hour interval from `t-11`
through `t`. The prediction horizon remains `t+1` through `t+6`. The primary label
is positive when observed hourly MAP is strictly below 65 mmHg for at least two
consecutive future hours. MAP at `t` is not part of the label, forward-filled MAP
is not outcome evidence, and all six future MAP hours are required for the primary
analysis.

No primary cohort, outcome, temporal boundary, or exclusion rule may be changed
after Phase 3 analysis begins.

## 4. Primary benchmark

The sole primary benchmark is `map_mean_6h`, defined as the arithmetic mean of all
calculable MAP values in the six predictor hours ending at `t`, transformed by the
existing monotonically decreasing sigmoid risk mapping. The implementation used in
Phase 3 must be identical to the current clinical-benchmark implementation.

`map_mean_6h` is a bounded ranking score, not a calibrated probability. AUROC,
AUPRC, and threshold-based classification metrics apply. Brier score and log loss
do not apply unless a separately prespecified, training-only calibration procedure
is implemented; Phase 3 will not calibrate the primary benchmark.

The primary missing-score policy for the benchmark remains neutral score 0.5, with
a complete-case sensitivity analysis. The policy may not be selected according to
which result is more favorable.

## 5. Sole multivariable candidate

The only multivariable candidate is L2-regularized logistic regression. No other
classifier, ensemble, feature selector, interaction search, polynomial expansion,
or temporal neural model is eligible.

The model will use `class_weight="balanced"`, `solver="lbfgs"`, L2 penalty, and a
maximum of 1,000 iterations. The solver is fixed and must not be selected or
replaced according to performance.

### 5.1 Locked predictor set

The candidate will use exactly the following predictors, all calculated from data
available no later than `t`:

| Predictor | Definition and rationale |
| --- | --- |
| `map_mean_6h` | Exact untransformed six-hour mean underlying the primary benchmark; ensures the candidate tests incremental rather than replacement value |
| `mean_arterial_pressure_current` | Current hemodynamic state |
| `mean_arterial_pressure_rolling_slope` | Direction of MAP change over the existing trailing feature window |
| `heart_rate_current` | Current compensatory cardiovascular response |
| `systolic_bp_current` | Current arterial-pressure context |
| `shock_index` | Prespecified heart-rate/systolic-pressure ratio |
| `respiratory_rate_current` | Current respiratory stress signal |
| `oxygen_saturation_current` | Current oxygenation signal |
| `mean_arterial_pressure_proportion_missing` | MAP observation density over the trailing window |
| `heart_rate_proportion_missing` | Heart-rate observation density |
| `systolic_bp_proportion_missing` | Systolic-pressure observation density |
| `respiratory_rate_proportion_missing` | Respiratory-rate observation density |
| `oxygen_saturation_proportion_missing` | Oxygen-saturation observation density |
| `mean_arterial_pressure_h0_missing` | Current-hour MAP missingness indicator |
| `heart_rate_h0_missing` | Current-hour heart-rate missingness indicator |
| `systolic_bp_h0_missing` | Current-hour systolic-pressure missingness indicator |
| `respiratory_rate_h0_missing` | Current-hour respiratory-rate missingness indicator |
| `oxygen_saturation_h0_missing` | Current-hour oxygen-saturation missingness indicator |

The set contains eight physiological level/trend features and ten prespecified
missingness features. It excludes identifiers, timestamps, future variables,
outcomes, split labels, temperature, oxygen flow, diastolic pressure, duplicated
MAP summary families, and all unlisted features. The feature set may not be expanded,
reduced, substituted, or filtered according to Phase 3 results.

`map_mean_6h` must be derived by the same six-hour value-selection rule used by the
benchmark. Its raw mean, rather than its sigmoid ranking transform, enters logistic
regression. If implementation review shows that any locked column cannot be derived
exactly and leakage-free from the current canonical window schema, the protocol
must be amended and re-frozen before analysis; no proxy may be chosen after viewing
performance.

### 5.2 Preprocessing

Continuous predictors will undergo median imputation followed by standard scaling.
Binary missingness indicators will pass through without imputation when structurally
complete; an unexpected missing indicator is a data-contract failure. Imputation
medians and scaling parameters must be fitted separately within each applicable
training fold. No full-cohort imputation, scaling, feature screening, or coefficient-
based feature deletion is permitted.

## 6. Closed hyperparameter space

The only tunable hyperparameter is inverse L2 regularization strength:

```text
C ∈ {0.1, 1.0}
```

Selection will use mean inner-fold AUPRC. If the two values tie at the precision
retained by the implementation, `C = 0.1` will be selected to prefer stronger
regularization. No new value, adaptive range, alternate penalty, class-weight
option, solver, tolerance search, or convergence-based expansion may be introduced
after results are observed.

## 7. Validation design

Phase 3 will use patient-grouped nested cross-validation:

- five outer folds;
- three inner folds within each outer-training partition;
- patient identity as the grouping unit in both cycles;
- all windows from a patient retained in the same fold;
- the same registered outer and inner group assignments for the benchmark and
  multivariable candidate;
- all training-dependent preprocessing fitted only within training folds;
- hyperparameter selection using inner folds only;
- threshold selection using inner out-of-fold predictions only;
- exactly one outer OOF prediction per eligible window;
- zero patient overlap between outer-training and outer-validation data.

The random seed will remain `20260726`. Fold membership must be persisted in a
private, identifier-bearing manifest and represented publicly only through aggregate
counts and overlap assertions. Phase 3 must abort if any patient belongs to more
than one outer fold, any window has zero or multiple OOF predictions, or the OOF
count differs from the eligible-window count.

## 8. Primary estimand and comparison

The primary estimand is the window-weighted OOF difference in AUPRC:

```text
delta AUPRC = AUPRC(logistic regression) - AUPRC(map_mean_6h)
```

The comparison will use the same eligible windows, labels, folds, and patient-
cluster bootstrap samples for both strategies. The primary analysis uses the
canonical 65-mmHg, two-consecutive-hour, complete-future-MAP outcome.

### 8.1 Clinically meaningful minimum effect

The prespecified minimum improvement required to justify multivariable complexity
is an absolute delta AUPRC of `0.02`.

This value is a development decision threshold rather than an established clinical
minimal important difference. It must be explicitly ratified by the scientific
reviewer before protocol freeze. It may not be changed after Phase 3 results are
available.

### 8.2 Paired inference

Uncertainty will use 1,000 patient-level bootstrap replicates with seed `20260726`.
Patients will be sampled with replacement, retaining all windows for each sampled
patient. Each replicate will use the identical patient sample for the candidate and
benchmark. Single-class replicates will be rejected and counted. The report will
include the observed difference, 95% percentile interval, valid-replicate count,
and proportion of finite bootstrap differences above zero.

The primary comparison is not a confirmatory hypothesis test and no multiplicity-
adjusted p-value is claimed.

## 9. Secondary metrics

Secondary analyses will report:

- delta AUROC, candidate minus benchmark, with paired patient-bootstrap interval;
- raw logistic-regression Brier score and log loss;
- cross-fitted calibrated Brier score and log loss;
- calibration intercept and slope when estimable, with estimation failures and
  boundary values reported rather than hidden;
- sensitivity, specificity, PPV, NPV, F1, and confusion counts using inner-selected
  fold thresholds;
- threshold-0.5 logistic-regression metrics as descriptive only;
- patient-equal-weight AUROC and AUPRC for both strategies and their difference;
- event prevalence, patient count, window count, availability, and alert fraction.

Brier score, log loss, and probability calibration will not be reported for the
uncalibrated `map_mean_6h` ranking score. Secondary metrics cannot rescue a failure
of the primary advancement rule.

## 10. Calibration policy

The primary delta-AUPRC analysis will use the candidate's raw OOF probability and
the benchmark's existing ranking score. Because monotonic calibration does not
define the primary incremental-discrimination question, calibration will be a
secondary, leakage-controlled analysis.

Platt logistic recalibration is the only permitted post-hoc calibration method.
Isotonic regression and method selection by observed performance are prohibited.
Within each outer fold:

1. generate raw inner OOF predictions using only outer-training patients;
2. fit the Platt recalibration model on those inner OOF predictions and labels;
3. refit the selected base logistic model on all outer-training patients;
4. apply the locked recalibration model to the outer-fold raw predictions;
5. retain raw and calibrated outer OOF probabilities separately.

No outer-fold outcome may fit or choose calibration. If calibration cannot be
estimated in a fold, the failure will be reported; no alternative method will be
substituted.

If logistic regression advances, the final development calibration mapping will be
fitted once using raw OOF predictions from all development patients, then frozen
with its coefficients and training scope before any confirmatory access. If the MAP
benchmark advances, it remains a ranking strategy unless a separate future
calibration protocol is approved before confirmatory access.

## 11. Threshold-selection procedure

For outer-fold classification summaries, each strategy will use the Youden
threshold selected exclusively from corresponding inner OOF scores. A target-
sensitivity threshold of 0.80 will be secondary. Threshold 0.5 will be descriptive
for logistic probabilities and has no privileged interpretation for the MAP ranking
score. Outer-fold outcomes may not select or alter thresholds.

After the strategy decision, one final development threshold will be estimated from
that strategy's complete development OOF scores:

- for an advancing calibrated logistic strategy, use calibrated development OOF
  probabilities;
- for an advancing MAP strategy, use its development OOF ranking scores;
- use the Youden rule as the primary final-threshold procedure;
- retain the target-sensitivity-0.80 threshold as a secondary operating point;
- resolve an exact Youden tie by choosing the higher threshold, favoring fewer
  positive classifications.

The selected numeric threshold, procedure, score semantics, cohort fingerprint,
and feature/model metadata must be frozen before confirmatory access. Phase 3 does
not itself perform confirmatory evaluation.

## 12. Prespecified sensitivity analyses

Sensitivity analyses are secondary and may not redefine the primary result. The
same locked benchmark, candidate, hyperparameter set, validation design, and
advancement logic will be used without adding models or features.

### 12.1 Outcome threshold and duration

Evaluate the full 3 × 3 grid:

```text
MAP threshold ∈ {60, 65, 70} mmHg
required consecutive low hours ∈ {1, 2, 3}
```

All comparisons remain strict (`MAP < threshold`). The registered 65-mmHg,
two-hour definition remains primary. Other cells are labeled sensitivity analyses.

### 12.2 Incomplete future MAP

Do not impute a single definitive label for missing future MAP. On candidate windows
with a complete temporal horizon but incomplete observed future MAP, report
identified bounds using two fixed assumptions:

- lower-event scenario: encode every missing future MAP hour as not low, encode
  observed hours by the strict threshold, and apply the consecutive-run rule;
- upper-event scenario: encode every missing future MAP hour as low, encode observed
  hours by the strict threshold, and apply the same consecutive-run rule.

Results under both assumptions must be presented together. Neither bound may
replace the complete-future-MAP primary analysis or be selected according to model
performance. The exact label-bound algorithm requires synthetic boundary-case tests
before execution.

### 12.3 Arterial-pressure source handling

Repeat the relevant cohort derivation under two prespecified alternatives to the
primary pooled median:

1. invasive-preferred: use invasive/arterial sources within an hour when present,
   otherwise use non-invasive sources;
2. non-invasive-only: exclude invasive/arterial sources from MAP and systolic-
   pressure construction.

For this protocol, invasive/arterial systolic-pressure codes are `220050` and
`225309`, and invasive/arterial MAP codes are `220052` and `225312`.
Non-invasive systolic pressure is code `220179`, and non-invasive MAP is code
`220181`. These assignments derive from the versioned FHIR mapping and must be
applied consistently to predictors and outcome MAP. Any clinically required change
must occur through a pre-analysis amendment; source rules may not depend on model
performance.

### 12.4 Uncalculable benchmark scores

Report both:

- the primary neutral-score-0.5 analysis on all eligible windows;
- a complete-case analysis restricted to windows where `map_mean_6h` is calculable.

Availability counts must be reported by windows and patients. The two approaches
are sensitivity analyses, not competing choices.

### 12.5 Patient weighting

The primary analysis is window-weighted. The sensitivity analysis assigns each
patient total weight one, distributing that weight equally across the patient's
windows. Both strategies must use identical weights.

### 12.6 Missingness and charting frequency

Report aggregate distributions by outer fold and outcome for:

- observed hours and proportion missing for each locked physiological variable;
- current-hour missing indicators;
- time since last real measurement where available;
- measurements per patient-hour;
- unavailable benchmark scores;
- windows contributed per patient.

These summaries are descriptive. They may identify limitations or motivate a
future protocol but may not trigger Phase 3 feature additions or model changes.

## 13. Stopping and advancement rules

Phase 3 stops after the locked candidate and benchmark have completed the primary
analysis and all prespecified sensitivity analyses, or earlier if a data-contract,
leakage, convergence, or OOF-accounting failure invalidates the analysis. A failure
must be reported and corrected under a documented amendment; analyses may not be
repeated merely to improve statistical results.

Logistic regression advances as the preferred development strategy only if all
primary conditions hold:

1. observed delta AUPRC is at least `0.02`;
2. the paired 95% bootstrap interval lower bound is greater than zero;
3. every outer fold produces valid OOF probabilities without patient or window
   accounting violations;
4. no implementation or protocol deviation affects the primary comparison.

Secondary metrics cannot override these conditions. If any primary condition
fails, `map_mean_6h` remains the preferred parsimonious development strategy and no
additional Phase 3 model may be introduced.

Before either strategy is frozen for future confirmatory evaluation, the following
robustness conditions must also be reviewed:

- patient-equal delta AUPRC must not be below `-0.02`;
- neither prespecified BP-source alternative may show delta AUPRC below `-0.02` for
  the strategy proposed to advance;
- all sensitivity results, calibration failures, missingness summaries, and
  protocol deviations must be disclosed;
- the strategy's score semantics and final-threshold procedure must be technically
  reproducible from frozen artifacts.

Failure of a robustness condition does not authorize model shopping. It requires
retaining the parsimonious benchmark or concluding that no strategy is ready to
freeze.

## 14. Explicit prohibitions

Phase 3 prohibits:

- evaluating additional model families after observing results;
- adding or removing predictors based on coefficients, significance, importance,
  discrimination, calibration, or sensitivity results;
- deep learning, recurrent neural networks, boosting, random forests, support-vector
  machines, neural feature learning, or ensembles;
- expanding the `C` grid or changing penalty, class weight, or solver according to
  performance;
- fitting preprocessing, calibration, or thresholds outside their training scope;
- threshold optimization on outer folds;
- changing AUPRC as the primary metric;
- redefining the clinically meaningful delta after analysis;
- using historical holdout performance for current candidate selection;
- accessing confirmatory or external outcome data;
- rerunning analyses until an interval excludes zero;
- choosing among sensitivity analyses according to favorability;
- describing development evidence as clinical superiority, external validation, or
  confirmatory evidence.

## 15. Required outputs and audit trail

When Phase 3 is eventually authorized, it must produce:

- a machine-readable protocol registration containing this file's hash, Git commit,
  canonical cohort fingerprint, seed, fold specification, features, hyperparameters,
  minimum delta, calibration policy, threshold policy, and analysis timestamp;
- aggregate fold accounting and OOF invariants;
- an aggregate primary comparison report;
- paired patient-bootstrap output with replicate accounting;
- raw and calibrated logistic probability metrics kept separate;
- all prespecified sensitivity results, including failures and unavailable analyses;
- a protocol-deviation log, even when empty;
- no patient, admission, ICU-stay, window, timestamp, prediction, or split-assignment
  identifiers in public reports.

The reserved public output paths are:

```text
reports/phase3_protocol_registration.json
reports/phase3_incremental_value.json
reports/phase3_model_comparison.csv
reports/phase3_paired_comparisons.csv
reports/phase3_sensitivity_analysis.json
reports/phase3_protocol_deviations.json
```

No existing Phase 1, Phase 2, historical holdout, or internal nested-CV report may
be overwritten.

## 16. Freeze checklist

The investigator formally ratified the scientific specification exactly as written,
including the development relevance margin of absolute delta AUPRC `0.02`. This
margin is neither a p-value threshold nor a clinically validated minimal important
difference. The BP-source assignments are accepted for this development protocol;
this investigator review is not independent clinical validation.

- [x] the investigator ratified absolute minimum delta AUPRC `0.02`;
- [x] the 18-feature set is confirmed derivable exactly from the canonical schema
      without information after `t`;
- [x] `map_mean_6h` is confirmed equivalent to the existing canonical benchmark;
- [x] the locked logistic specification, including `solver="lbfgs"`,
      `class_weight="balanced"`, `max_iter=1000`, and `C ∈ {0.1, 1.0}`, is accepted;
- [x] the enumerated invasive and non-invasive BP source assignments are accepted
      by the investigator for this development protocol;
- [x] the specified missing-as-not-low and missing-as-low bound algorithms are
      implemented in passing synthetic boundary tests without using clinical results;
- [x] deterministic five-outer/three-inner patient-grouped folds and private
      fold-manifest handling are fixed;
- [x] the private fold manifest accounts for 92 patients and 8,970 windows, has zero
      patient overlap, is ignored by Git, and is stored with mode `0600`;
- [x] the private fold-manifest fingerprint is
      `sha256:fff63cd0a5ab44625cd1490e3eaa5f5a01cce2d9e352ece216f8ba95d2cc9b99`;
- [x] Platt calibration as the sole development calibration method and the
      prespecified development threshold and tie rules are accepted;
- [x] preregistration and result paths have distinct safeguards: a matching
      preregistration may exist before execution, while existing result files cause
      a hard failure and no reserved artifact may be overwritten;
- [x] separate protocol-hash, Git-commit, canonical-cohort, fold-manifest, source,
      and configuration fingerprint registration is implemented;
- [x] no confirmatory dataset has been accessed;
- [x] Ruff, pytest, and `git diff --check` passed during technical pre-freeze
      validation.

The scientific protocol is frozen. Its own SHA-256 and frozen Git commit are
intentionally not embedded in this file: they will be calculated after the freeze
commit and recorded separately in `reports/phase3_protocol_registration.json`.
Formal Phase 3 performance analysis has not yet been executed and must not begin
until that preregistration matches the frozen protocol, cohort, fold manifest, and
configuration fingerprints.
