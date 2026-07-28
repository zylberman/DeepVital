# Phase 2 model selection lock

This record was created from train and validation only, before test evaluation.

- Selected model: `map_mean_6h`
- Best simple MAP benchmark: `map_mean_6h`
- Predictors: 140 prespecified current/trailing features
- Rule: highest validation AUPRC, then lowest Brier score, then model name.
- Complexity was not a selection criterion; the simple MAP benchmark won under
  the same prespecified rule applied to every candidate.
- Thresholds: fixed 0.5, validation Youden index, and validation target sensitivity near 0.80.
- Imputation/scaling: fitted within each applicable training pipeline only.
- Test set: not read by this command.
- Subsequent evaluation artifacts refer to the final partition as the
  `developmental holdout` because it was processed four times during corrections.
