# Clinical benchmark output audit

All benchmarks are development-only and use the same patient-grouped nested folds
and eligible windows. Higher values always indicate higher predicted hypotension
risk. No output is evidence of causal effect or clinical utility.

| Benchmark | Output type | Range | Missing treatment | Threshold source |
| --- | --- | --- | --- | --- |
| Training prevalence | Probability estimate | 0–1 | Always available | Corresponding inner training folds |
| Last MAP | Ranking score after decreasing sigmoid transform | 0–1 | Neutral 0.5 | Inner OOF scores |
| Six-hour mean MAP | Ranking score after decreasing sigmoid transform | 0–1 | Neutral 0.5 if no MAP is available | Inner OOF scores |
| Six-hour minimum MAP | Ranking score after decreasing sigmoid transform | 0–1 | Neutral 0.5 if no MAP is available | Inner OOF scores |
| MAP slope | Ranking score after decreasing sigmoid transform | 0–1 | Neutral 0.5 | Inner OOF scores |
| Shock index | Ranking score after increasing sigmoid transform | 0–1 | Neutral 0.5 for missing/invalid inputs | Inner OOF scores |
| Modified shock index | Ranking score after increasing sigmoid transform | 0–1 | Neutral 0.5 for missing/invalid inputs | Inner OOF scores |

The clinical sigmoid mappings were chosen as transparent monotonic risk transforms;
they were not calibrated against outcomes. AUROC, AUPRC, and fold-specific threshold
metrics are applicable. Brier score and log loss are not applicable and are omitted.

The constant prevalence is estimated only from the applicable training fold. Its
within-fold score is constant, so within-fold AUROC is 0.5 when both classes are
present. Pooled AUROC can differ from 0.5 because different folds receive different
prevalence estimates; that pooled value must not be interpreted as true
discrimination.

The nested ML strategy emits `predict_proba` probability estimates from pipelines
fitted only on training data, but no post-hoc calibration model was fitted. It is
therefore marked `probability_calibrated: false`; Brier score and log loss remain
valid descriptive probability metrics.

The missing-score rule was specified before comparison: neutral risk 0.5 is the
primary analysis, accompanied by availability counts and complete-case sensitivity.
No strategy is selected according to which produces the better result.

## Observed aggregate availability

On the 8,970-window canonical development cohort:

| Benchmark | Uncalculable windows | Patients with at least one uncalculable window |
| --- | ---: | ---: |
| Training prevalence | 0 | 0 |
| Last MAP | 9 | 9 |
| Six-hour mean MAP | 0 | 0 |
| Six-hour minimum MAP | 0 | 0 |
| MAP slope | 0 | 0 |
| Shock index | 8 | 8 |
| Modified shock index | 9 | 9 |

The public JSON contains both neutral-risk primary metrics and complete-case
sensitivity metrics. It does not contain patient or window identifiers.

## Paired development comparisons

Paired patient bootstrap uses `nested_ml_strategy` as reference and defines every
difference as benchmark minus reference. Positive values favor the benchmark for
AUROC/AUPRC; negative values favor the benchmark for Brier/log loss. Probability
loss comparisons are available only for constant prevalence because the other
clinical outputs are ranking scores.

For six-hour mean MAP, observed delta AUPRC was 0.0886 with a paired 95% interval
of 0.0205 to 0.1453; delta AUROC was 0.0231 with an interval of 0.0010 to 0.0419.
These paired development estimates do not select a final model and must not be
interpreted using overlap of separate model-specific intervals.
