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

Those status fields describe the earlier nested-CV report before the later Phase 3
strategy decision.

## Prespecified Phase 3 development experiment

| Field | Value |
| --- | --- |
| Name | `deepvital-phase3-incremental-value-v1` |
| Role | Prespecified internal development comparison |
| Cohort | Canonical administrative ICU-bounds cohort; 92 patients, 8,970 windows |
| Execution count | One formal preregistered execution; no result-driven rerun |
| Comparison | Frozen 18-predictor L2 logistic candidate minus `map_mean_6h` |
| Primary result | Delta AUPRC +0.0075286864; paired 95% CI +0.0004996287 to +0.0171297719 |
| Advancement rule | Failed because observed delta was below the prespecified +0.020 margin |
| Development decision | Retain `map_mean_6h` as the parsimonious strategy |
| Interpretation | Development evidence only; not external, confirmatory, or clinical validation |
| Reports | `reports/phase3_incremental_value.json` and associated Phase 3 result files |

The two incomplete-future-MAP sensitivities failed because their datasets contained
patients absent from the frozen fold manifest. This was disclosed without rerunning
Phase 3 and did not change the primary decision. The formal report records no
primary protocol deviation.

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
