# Phase 2 protocol

Phase 2 freezes the Phase 1B cohort, patient split, 12-hour trailing predictor
window, and future-only six-hour sustained-hypotension outcome. It compares
transparent MAP and shock-index benchmarks with four conventional classifiers.

Training data alone fit model parameters, imputers, and scalers. Validation
selects one model and three decision thresholds. Test is evaluated once after a
machine-readable selection lock exists. Metrics include prevalence, AUROC,
AUPRC, Brier score, log loss, calibration intercept/slope, sensitivity,
specificity, PPV, NPV, F1, and confusion counts.

Uncertainty is estimated by deterministic patient-cluster bootstrap, retaining
all windows belonging to every sampled patient. Single-class replicates are
rejected and counted. A patient-equal-weight analysis checks sensitivity to
patients contributing unequal numbers of windows.

Model selection follows `configs/evaluation.yaml`: highest validation AUPRC,
then lowest validation Brier score, then lexicographically smallest model name
as a deterministic final tie-break. Test metrics are not inputs to this rule.

All reports are aggregate-only. No identifier or patient-level prediction is a
permitted report field.
