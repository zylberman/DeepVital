# DeepVital: current methodological report

> This filename is retained for repository history. The document now summarizes
> the project beyond Phase 1 and should be read with `docs/RESEARCH_PROTOCOL.md`,
> `docs/METHODS_CURRENT.md`, and `docs/RESULTS_CURRENT.md`.

DeepVital is a research-only methodological pipeline for early prediction of
sustained hypotension using longitudinal ICU vital signs represented through
FHIR-compatible resources. It is not a medical device and has not been validated
for clinical decision-making.

## Data processing and canonical cohort

The project uses the MIMIC-IV Clinical Database Demo on FHIR 2.1.0. Streaming FHIR
extraction retained 89,415 supported observations representing 100 patients, 128
hospital admissions, and 140 ICU stays. The current canonical Phase 1B route uses
FHIR ICU Encounter periods to define hourly time at risk. It produced 12,502 hourly
rows and 8,970 eligible windows, of which 1,774 were positive (19.78%).

A historical observation-bounded route produced 12,309 hourly rows and 8,872
windows, including 1,759 positive windows. Those artifacts remain part of the
historical development record. The administrative route was selected as canonical
because its boundaries are explicit, encounter-consistent, auditable, and
independent of vital-sign recording onset and cessation.

Each ICU stay is processed independently. Within-hour duplicates are summarized by
the median. Forward fill is limited to two hours; backward fill and future-based
interpolation are prohibited. Predictors use a closed 12-hour history ending at
time \(t\). The outcome begins at \(t+1\) and requires observed MAP strictly below
65 mmHg for at least two consecutive hours within the following six hours. All six
future MAP hours are required in the primary analysis.

## Internal development validation

The canonical cohort was evaluated by five-outer-fold, three-inner-fold nested
cross-validation grouped by patient. Ninety-two patients contributed eligible
windows. Every patient belonged to one outer fold, all windows from a patient
remained together, and every one of the 8,970 windows received exactly one
out-of-fold prediction. Model, hyperparameter, and threshold selection were
restricted to inner cross-validation. Training-dependent preprocessing remained
within the corresponding training folds.

The comparison included a nested conventional machine-learning strategy and seven
simple benchmarks: training prevalence, last MAP, six-hour mean MAP, six-hour
minimum MAP, MAP slope, shock index, and modified shock index. Clinical sigmoid
transforms are ranking scores rather than calibrated probabilities; Brier score and
log loss are therefore not reported for those scores.

| Strategy | AUROC | AUPRC | Brier score | Log loss |
| --- | ---: | ---: | ---: | ---: |
| Six-hour mean MAP | 0.8416 | 0.6219 | Not applicable | Not applicable |
| Last MAP | 0.8216 | 0.5613 | Not applicable | Not applicable |
| Nested ML strategy | 0.8185 | 0.5333 | 0.1354 | 0.4228 |

In a paired patient bootstrap, the six-hour mean MAP minus nested ML difference was
0.0231 for AUROC (95% interval 0.0010–0.0419) and 0.0886 for AUPRC
(0.0205–0.1453). These results indicate higher discrimination for the six-hour mean
MAP benchmark in the present internal analysis, but they do not establish clinical
superiority, a final strategy, or generalizability. The model status remains
`not_final`, and no final threshold is frozen.

## Historical holdout and confirmatory status

The historical 8,872-window holdout is formally `development_holdout_v1`. Its role
is development, it is not confirmatory, and its recorded evaluation count remains
four. Its metrics have been preserved, but repeated access prevents interpretation
as an untouched confirmatory assessment.

All 100 demo patients are now development data. `confirmatory_test_pending` remains
the current state. A confirmatory evaluation will require entirely new patients and
a frozen protocol, cohort, model, feature schema, and threshold. No confirmatory or
external evaluation has been executed.

## Interpretation and limitations

DeepVital currently demonstrates a reproducible, leakage-aware research workflow
and internal comparison of transparent clinical benchmarks with conventional
machine learning. It does not demonstrate clinical utility, prospective
performance, transportability, regulatory readiness, or benefit to patients.
Interpretation is limited by the small demo cohort, overlapping windows, potentially
informative missingness, complete-future-MAP selection, provisional blood-pressure
source pooling, absence of post-hoc calibration, and lack of independent data.
