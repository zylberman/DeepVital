# Statistical analysis plan

## Analysis population and unit structure

The canonical development population comprises 92 patients with 8,970 eligible
window-level predictions. Patient is the grouping and resampling unit; the
prediction window is the unit at which labels and scores are defined. All windows
from a patient remain together in validation and bootstrap procedures.

## Internal validation design

Five outer and three inner GroupKFold partitions are used. Inner folds select the
conventional candidate and fold-specific threshold. The corresponding outer fold
estimates performance without contributing to those decisions. Every window must
receive exactly one out-of-fold prediction, and every patient must be assigned to
one outer fold.

## Outcomes and estimands

The binary outcome is sustained future hypotension under the primary definition in
`RESEARCH_PROTOCOL.md`. Principal estimands are window-weighted out-of-fold
discrimination and classification summaries in the canonical development cohort.
They are not estimands of clinical utility or transportability.

## Discrimination and probability metrics

AUPRC is the primary comparison metric because the outcome is imbalanced. AUROC is
secondary. Brier score and log loss apply only to probability outputs. They do not
apply to uncalibrated clinical ranking scores even when those scores are bounded
between zero and one.

The constant-prevalence and nested ML outputs are probabilities. The nested ML
probabilities have no post-hoc calibration. No calibration claim is made from a
bounded clinical transform.

## Classification metrics and thresholds

Sensitivity, specificity, PPV, NPV, F1, and confusion counts are computed from one
inner-selected threshold per outer-fold prediction. These are recorded under
`inner_selected_fold_thresholds`. Results under `threshold_0.5_descriptive` are
descriptive. No pooled threshold is a frozen final threshold.

## Missing clinical scores

The primary rule assigns neutral score 0.5 when a benchmark is not calculable. The
report includes the number of affected windows and patients and a complete-case
sensitivity analysis. The neutral and complete-case approaches are not selected
according to which performs better.

## Patient-cluster bootstrap

Ninety-five per cent percentile intervals use 1,000 bootstrap replicates with seed
20260726. Patients are sampled with replacement, and all windows from each sampled
patient are retained. Replicates with a single outcome class are rejected and
counted; all 1,000 current replicates were valid.

## Paired comparisons

Each clinical benchmark is compared with `nested_ml_strategy` using the same
bootstrap patient samples. Differences are comparison minus reference. Positive
deltas favor the comparison for AUROC/AUPRC; negative deltas favor it for Brier
score/log loss. Probability-loss differences are calculated only when both outputs
are probabilities.

Bootstrap interval exclusion of zero is interpreted as development evidence of a
directional difference, not as a multiplicity-adjusted confirmatory test. Overlap of
separate model-specific intervals is not used to infer equality or superiority.

## Multiple comparisons and reporting

The analysis compares multiple prespecified benchmarks. No family-wise or false-
discovery adjustment has been implemented, and no claim of definitive model
superiority is permitted. Exact estimates, intervals, valid replicate counts,
difference definitions, and favorable directions are reported for transparency.

## Future strategy and confirmatory analysis

After development evidence is reviewed, one model strategy may be selected and its
threshold estimated from development OOF predictions. Protocol, features, model,
threshold, and fingerprints must then be frozen. A future independent confirmatory
analysis should predefine its primary estimand, confidence interval, calibration
assessment, missing-data handling, and multiplicity policy before accessing
outcomes. No such analysis has been completed.
