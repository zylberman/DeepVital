# DeepVital research protocol

**Protocol status:** current development protocol  
**Evaluation state:** `confirmatory_test_pending`  
**Intended use:** retrospective methodological research only

## 1. Study design

DeepVital is a retrospective methodological study of early prediction of sustained
hypotension from longitudinal ICU vital signs. The completed work comprises data
engineering and internal patient-grouped validation in a small demonstration
cohort. It does not comprise confirmatory, external, prospective, clinical-utility,
or impact evaluation.

## 2. Data source

The development source is the MIMIC-IV Clinical Database Demo on FHIR 2.1.0. The
local FHIR distribution contains gzip-compressed NDJSON resources. The implemented
inventory reader streams one resource per line rather than decompressing complete
files to disk or loading them wholly into memory. Relevant relationships involve
FHIR Patient, hospital Encounter, ICU Encounter, and Observation resources.

All 100 demo patients are development data. No independent patient cohort has been
accessed for confirmatory evaluation.

## 3. Study population

The canonical extraction represents 100 patients, 128 hospital admissions, and 140
ICU stays with supported observations. The administrative ICU Encounter period
defines time at risk. Observations are linked to one patient, hospital admission,
and ICU stay; ambiguous or inconsistent relationships are rejected and counted.

The canonical temporal cohort contains 8,970 eligible windows from 92 patients.
Eligibility requires sufficient 12-hour history, a complete six-hour temporal
horizon, at least the configured minimum observed predictor information, and
complete future MAP assessment for the primary outcome.

## 4. FHIR processing

`scripts/extract_canonical_vitals.py` builds a long-format local canonical table.
The extractor streams Chartevents observations, resolves Patient and Encounter
relationships, validates the configured coding system and code, parses the
effective timestamp, and preserves original and normalized values and units.

The extraction retained 89,415 supported observations. Unsupported codes or value
types, implausible values, and invalid relationships are represented only by
aggregate rejection counts in the public quality report. The mappings are
configuration-controlled and audited against the local inventory; they are not
claimed to constitute definitive ontology validation.

## 5. Variables

The eight physiological variables are heart rate, respiratory rate, systolic blood
pressure, diastolic blood pressure, MAP, peripheral oxygen saturation,
temperature, and oxygen flow. Fahrenheit is converted to degrees Celsius only when
the source unit explicitly identifies Fahrenheit. Original numeric values and units
are retained alongside normalized values. Oxygen flow is not interpreted as FiO2.

Invasive, non-invasive, and alternate arterial-pressure codes map to shared
variables in the primary cohort. Phase 3 additionally evaluated the prespecified
invasive-preferred and non-invasive-only development alternatives.

## 6. Temporal aggregation

Each ICU stay is processed independently. The hourly grid begins at the hour
containing the ICU Encounter start and ends at the hour containing its end.
Observations outside the exact administrative period are excluded and counted.
Multiple values for a variable within an hour are aggregated by the median.

The canonical route produced 12,502 hourly rows. A historical route bounded its
grid by first and last supported observations and produced 12,309 rows. The
administrative route is canonical because it explicitly defines clinical time at
risk and is not dependent on charting onset or cessation.

## 7. Missing-data handling

No backward fill or future-dependent interpolation is permitted. Forward fill is
limited to two hours within each ICU stay. The hourly representation preserves the
observed median, observation indicator, measurement count, bounded-forward-filled
value, missingness indicator, forward-fill indicator, and hours since the last real
measurement. Missingness is potentially informative and is not interpreted as
random.

Clinical benchmark scores that cannot be computed receive a predeclared neutral
score of 0.5 in the primary comparison. Availability and complete-case sensitivity
results are reported separately. This rule was not chosen after observing
performance.

## 8. Prediction window

At time \(t\), predictors comprise the closed retrospective sequence \(t-11\)
through \(t\). Tabular summaries include current and previous values, change,
trailing mean, median, minimum, maximum, standard deviation and slope, observation
counts, missing proportions, and time since last observation. Pulse pressure and
shock index are included when inputs are available. Identifiers, split labels,
prediction time, outcome, and future variables are excluded from candidate
predictors.

## 9. Primary outcome

The primary outcome is observed hourly MAP strictly below 65 mmHg for at least two
consecutive hours within \(t+1\) through \(t+6\). MAP at \(t\) is not part of the
outcome, MAP equal to 65 mmHg does not qualify, and forward-filled MAP is not outcome
evidence. All six future MAP hours must be observed. This complete-ascertainment
rule may select periods with more intensive monitoring.

Phase 3 evaluated the prespecified threshold and duration grid as sensitivity
analyses. The two incomplete-horizon bounds failed during execution because their
datasets contained patients absent from the frozen fold manifest; the formal run
was not repeated and those failures do not replace the primary analysis.

## 10. Leakage safeguards

Windows cannot cross patients, admissions, or ICU stays. Predictor construction
ends at \(t\), while outcome construction starts at \(t+1\). Forward fill uses only
prior observations. Patient grouping is enforced in outer and inner
cross-validation. Training-dependent imputers, scalers, model parameters, and
hyperparameters are fitted only on the relevant training patients. Outer-fold
labels or predictions are not used to select the candidate or threshold evaluated
in that fold.

## 11. Development strategy

All current demo data may inform development through patient-grouped internal
validation. The conventional candidates are logistic regression, Gaussian Naive
Bayes, and Histogram Gradient Boosting. The nested strategy evaluates logistic
regression with C values 0.1 and 1.0, Gaussian Naive Bayes with variance-smoothing
values 1e-10 and 1e-9, and Histogram Gradient Boosting with learning rates 0.03 and
0.05. Other configured parameters remain fixed.

Logistic regression and Gaussian Naive Bayes use median imputation and scaling in
pipelines fitted within training folds. Histogram Gradient Boosting handles missing
values natively. No data-driven feature-selection step or post-hoc calibration
model is currently fitted.

## 12. Internal validation

Internal validation uses five outer folds and three inner folds with patient as the
grouping unit. Each patient belongs to exactly one outer fold, all windows from that
patient remain together, and each eligible window receives exactly one out-of-fold
prediction. Candidate selection prioritizes inner AUPRC, followed by inner Brier
score and model name as deterministic tie-breakers. Thresholds are selected from
inner out-of-fold scores only.

This earlier nested-CV comparison did not itself select a final strategy. The later
prespecified Phase 3 analysis completed the development strategy decision.

## 13. Clinical benchmarks

The prespecified comparators are constant training-fold prevalence, last MAP,
six-hour mean MAP, six-hour minimum MAP, MAP slope, shock index, and modified shock
index. They provide interpretable reference points against which added complexity
must be justified.

Except for training prevalence, these outputs are monotonic bounded ranking scores,
not calibrated probabilities. Their metadata record output type, calibration
status, calibration method and scope, score range, and risk direction.

## 14. Metrics

AUROC and AUPRC apply to probabilities and ranking scores. Sensitivity, specificity,
PPV, NPV, F1, and confusion counts use fold-specific thresholds selected inside the
inner cycle. Results at threshold 0.5 are descriptive. Brier score and log loss are
reported only for probability outputs and are not reported for uncalibrated clinical
ranking scores.

The primary comparison metric is AUPRC. No clinical-utility or causal interpretation
is assigned to discrimination estimates.

## 15. Bootstrap inference and paired comparisons

Uncertainty is estimated using 1,000 patient-cluster bootstrap replicates. Patients
are sampled with replacement and all their windows remain together. This partially
addresses within-patient dependence but does not make overlapping windows
independent.

Paired comparisons use the same sampled patients for a benchmark and the nested ML
reference. Differences are comparison minus nested ML. Positive differences favor
the comparison for AUROC/AUPRC; negative differences favor the comparison for
Brier score/log loss. Separate confidence-interval overlap is not used to infer
equivalence or superiority.

## 16. Phase 3 development strategy decision

Phase 3 compared `map_mean_6h` with one frozen 18-predictor L2 logistic candidate.
Candidate AUPRC was 0.6293981556 versus 0.6218694691 for the benchmark, for delta
AUPRC `+0.0075286864` (paired patient-bootstrap 95% interval `+0.0004996287` to
`+0.0171297719`). The gain was positive but did not reach the prespecified `+0.020`
development relevance margin. The logistic candidate therefore did not advance,
and `map_mean_6h` remains the parsimonious development strategy.

The margin is not a p-value or a clinically validated minimal important difference.
Recorded calibrated-candidate operating points remain development summaries, not
validated clinical thresholds.

## 17. Confirmatory evaluation policy

A confirmatory test requires patients entirely absent from feature development,
preprocessing decisions, training, internal validation, debugging, and historical
holdout evaluation. Re-splitting the same 100 patients cannot create independence.

Before access, the protocol hash, cohort fingerprint, serialized model and hash,
model metadata, feature schema, and threshold must be frozen. The implemented
evaluator performs inference only, rejects development-patient overlap, records
first consumption, rejects changed inputs after consumption, and classifies exact
repetitions as technical reproductions. No confirmatory evaluation has been
executed.

## 18. Reproducibility

Canonical metadata record `source_code_commit`,
`working_tree_dirty_before_run`, `generation_timestamp`, configuration hash, input
fingerprint, and output fingerprint. `source_code_commit` identifies the code used
at generation time; it does not claim that an artifact belongs to the later commit
that versions it. Publication builds should use `--require-clean-worktree`, which
aborts before input processing or output writing if the source tree is dirty.

Software verification uses Python 3.12 in CI, Ruff, and pytest. Clinical report
regeneration is not part of CI.

The Phase 3 provenance chain is: frozen protocol commit
`158656304a96a4229208aad7e07fe45959672bfe`; preregistered implementation source
`54414fae32cc1c8b7cece36b2f1a96d81a48db35`; preregistration tag
`phase3-preregistered-v1`; original formal result commit `c7db731`; and CSV
line-ending normalization commit `d3c6915`, merged through PR #5. The normalization
changed line endings only, not scientific values. The preregistration JSON itself
was not committed before execution; its SHA-256
`03bf1ce0efa6eb5e431b1e76654a878e9059353c8f6d11cdd0d6d09f6632a7c1` was
published in the preregistration tag before execution.

## 19. Privacy and governance

Raw and identifier-bearing derived data are local-only and ignored by Git. Public
reports contain aggregate statistics and fingerprints, not patient-level rows or
split assignments. Credentials must be supplied through environment variables.
Restricted data must not be redistributed or re-identified.

Ethics and data-use statements should be finalized according to the requirements
of the underlying dataset and the intended venue.

## 20. Planned future validation

Planned work prioritizes consolidation of Phase 3, transparent post-Phase-3
technical investigation of the failed incomplete-future-MAP inputs, environment
locking, and acquisition of appropriately governed independent patients. External
work should reproduce `map_mean_6h` and, if justified in advance, the frozen
logistic candidate, then assess transportability and calibration. Further model
development should be considered only after independent evidence rather than by
continued optimization on the same development cohort. Confirmatory outcomes must
remain isolated until a future confirmatory protocol is frozen.
