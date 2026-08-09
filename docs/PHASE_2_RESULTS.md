# Phase 2 clinical benchmarks and baseline results

> **Historical results.** These values belong to the legacy 8,872-window cohort and
> `development_holdout_v1`. They must not be combined with canonical nested-CV
> results in `RESULTS_CURRENT.md`.

These results are development evidence. The partition was accessed four times and
must not be interpreted as an intact confirmatory holdout. The historical
evaluation is named `development_holdout_v1`, and its metrics are preserved.

## Completion summary

The Phase 1B gate passed before fitting: the private split manifest matches the
modeling dataset, patient overlap is zero, all 8,872 windows reconcile with the
aggregate split report, and candidate-window accounting passes. Predictors are
restricted to values through `t`; the outcome remains `t+1` through `t+6`.

The validation rule selected the six-hour trailing mean MAP benchmark
(`map_mean_6h`). On validation it achieved AUROC 0.7897, AUPRC 0.6124, and Brier
score 0.1622. The validation prevalence was 0.2682.

The locked model was then evaluated once on 1,551 test windows from 15 patients.
Test prevalence was 0.1412. At its validation-selected Youden threshold,
`map_mean_6h` achieved:

- AUROC 0.8649
- AUPRC 0.5490
- Brier score 0.1024
- sensitivity 0.6849
- specificity 0.8686
- PPV 0.4615
- NPV 0.9437

The 95% patient-bootstrap intervals for `map_mean_6h` were 0.6987–0.9554 for
AUROC, 0.1739–0.7875 for AUPRC, and 0.0621–0.1461 for Brier score. All 1,000
requested bootstrap replicates were valid.

For context, histogram gradient boosting had test AUPRC 0.5094 and Brier score
0.0929; logistic regression had test AUPRC 0.4942; current MAP (`last_map`) had
test AUPRC 0.4549. These are descriptive comparisons only. Wide, overlapping
patient-bootstrap uncertainty and the small test cohort do not support a
superiority claim.

During final verification, a tie-handling defect was found in average precision
for constant predictions. After correcting it and adding a regression test, all
aggregate test reports were regenerated. This security and methodology audit
regenerated them once more after making the configured model-selection rule
executable and once more to persist an unambiguous post-evaluation lock status.
Consequently, the held-out partition was technically processed four
times; the selected model and thresholds did not change, but this is an
evaluation-protocol deviation and is recorded in the private selection manifest.

Patient-equal-weight sensitivity analysis produced AUPRC 0.6004 for the locked
benchmark, versus its ordinary window-weighted AUPRC of 0.5490. Exact results
for every model and threshold are in the aggregate CSV reports.

## Reproducibility and privacy

Configuration, random seeds, thresholds, metrics, bootstrap counts, and
aggregate plots are retained. Serialized pipelines and the private selection
lock are under `models/baselines/`, which is ignored by version control. Public
reports contain no subject, admission, stay, window, or prediction-time
identifiers.

## Recommended next phase

Before considering temporal neural networks, validate these simple benchmarks
on a larger, independently defined cohort; review calibration and unit/data
quality; and pre-register any model or outcome changes. No deployment,
monitoring, API, or clinical-use work is warranted from this demo result.
