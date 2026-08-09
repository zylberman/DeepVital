# DeepVital experiment registry

## Registry principles

Experiment names identify distinct evidence roles. A historical label must not be
renamed to imply independence, and a new random split of the same patients does not
create a confirmatory cohort.

## Historical development experiment

| Field | Value |
| --- | --- |
| Name | `development_holdout_v1` |
| Role | Development |
| Cohort | Historical observation-bounded Phase 1B; 8,872 windows |
| Data reuse | Holdout accessed four times |
| Model selection allowed | Historical selection used train/validation; repeated holdout access compromises confirmatory interpretation |
| Threshold selection allowed | Historical validation-derived thresholds preserved |
| Interpretation | Historical development evidence, not confirmatory |
| Reports | `reports/validation_metrics.csv`, `reports/test_metrics.csv`, `reports/bootstrap_summary.json` |

The count `test_evaluation_count: 4` remains in
`models/baselines/model_selection.json`. Exact chronology of all four accesses
cannot be reconstructed from Git.

## Current internal validation

| Field | Value |
| --- | --- |
| Name | `internal_nested_cross_validation` |
| Role | Internal validation using development data |
| Cohort | Canonical administrative ICU-bounds cohort; 92 patients with windows, 8,970 windows |
| Data reuse | All 100 demo patients are development data |
| Model selection allowed | Candidate/hyperparameter selection inside inner folds only |
| Threshold selection allowed | Fold-specific thresholds inside inner folds only |
| Interpretation | Internal development comparison; no final strategy selected |
| Reports | `reports/internal_nested_cross_validation.json`, `reports/internal_nested_model_comparison.csv`, `reports/internal_nested_paired_comparisons.csv` |

The status is `model_selection_status: not_final` and
`final_threshold_status: not_frozen`.

## Future confirmatory evaluation

| Field | Value |
| --- | --- |
| Name | `confirmatory_test_pending` |
| Role | Independent confirmatory test |
| Cohort | Entirely new patients; not yet available or accessed |
| Data reuse | Prohibited before strategy and protocol freeze |
| Model selection allowed | No |
| Threshold selection allowed | No |
| Interpretation | Pending; no result exists |
| Reports | None |

The first future evaluation must use frozen protocol, cohort, model, model metadata,
features, and threshold. Later exact repeats are technical reproductions, not new
confirmatory experiments.
