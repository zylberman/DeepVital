# Phase 2 model selection lock

> **Historical document.** This lock belongs to `development_holdout_v1` and does
> not select the current canonical final model or threshold. Current status is
> `model_selection_status: not_final` and `final_threshold_status: not_frozen`.

This record was created from train and validation only, before test evaluation.

- Selected model: `map_mean_6h`
- Best simple MAP benchmark: `map_mean_6h`
- Predictors: 140 prespecified current/trailing features
- Rule: highest validation AUPRC, then lowest Brier score, then model name.
- Thresholds: fixed 0.5, validation Youden index, and validation target sensitivity near 0.80.
- Imputation/scaling: fitted within each applicable training pipeline only.
- Test set: not read by this command.
