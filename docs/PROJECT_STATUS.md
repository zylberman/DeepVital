# DeepVital project status

**Status date:** 2026-08-06

**Repository state reviewed:** `main` at merge commit `0b7ce15`

**Intended use:** retrospective methodological research only

## Summary

DeepVital currently implements a reproducible research pipeline from FHIR resource
inspection through patient-grouped internal validation. It is not a medical device
or clinical decision-support system. The current evidence is development evidence;
no confirmatory, external, prospective, workflow, or clinical-impact evaluation has
been completed.

## Completed work

| Component | Status | Evidence |
| --- | --- | --- |
| Aggregate FHIR inventory | Completed | `reports/fhir_inventory.json` |
| Canonical FHIR vital-sign extraction | Completed | `reports/canonical_extraction_quality.json` |
| Administrative ICU-bounded cohort | Completed | `reports/canonical_v1/` |
| Future-only sustained-hypotension outcome | Completed | `configs/labeling.yaml`; tests |
| Clinical and conventional ML baselines | Completed as development work | `src/deepvital/models/` |
| Patient-grouped nested cross-validation | Completed | `reports/internal_nested_cross_validation.json` |
| Historical holdout reclassification | Completed | `docs/HOLDOUT_REUSE_ASSESSMENT.md` |
| Confirmatory evaluation | Pending | `confirmatory_test_pending` |
| External validation | Not started | No independent dataset report |

## Current cohort and outcome

The canonical development cohort represents 100 patients, 128 hospital admissions,
and 140 ICU stays. Ninety-two patients contribute 8,970 eligible windows, including
1,774 positive windows (19.78%). Predictors cover \(t-11\) through \(t\). The
primary outcome is observed MAP strictly below 65 mmHg for at least two consecutive
hours in \(t+1\) through \(t+6\), with complete future MAP required.

## Current validation and results

Internal validation uses five outer and three inner folds grouped by patient. Each
patient is assigned to one outer fold and each eligible window receives exactly one
out-of-fold prediction. The six-hour mean MAP benchmark achieved AUROC 0.8416 and
AUPRC 0.6219; the nested ML strategy achieved AUROC 0.8185, AUPRC 0.5333, Brier
score 0.1354, and log loss 0.4228. These are internal development estimates.

No final model has been selected and no final threshold has been frozen. Fold-
specific classification thresholds originate only from inner cross-validation.

## Historical evidence boundary

The earlier 8,872-window holdout remains `development_holdout_v1`, with four
recorded accesses. It is preserved as historical development evidence and is not
an untouched confirmatory test.

## Software and reproducibility state

At the reviewed merge commit, 70 tests pass and Ruff reports no violations. Twelve
external Joblib/NumPy deprecation warnings remain non-blocking. Canonical cohort
metadata records clean source provenance and deterministic configuration, input,
and output fingerprints. Runtime dependencies are not fully pinned.

## Unresolved scientific decisions

- determine whether six-hour mean MAP should remain the preferred parsimonious
  development strategy or whether multivariable modeling adds reproducible value;
- define a calibration strategy after selecting a model strategy;
- perform outcome, missingness, and blood-pressure-source sensitivity analyses;
- specify subgroup analyses that are supportable in a larger cohort;
- obtain appropriately governed independent patients for confirmatory evaluation.

## Next milestone

Select and document the development model strategy without accessing confirmatory
data, then estimate and freeze its final threshold from development out-of-fold
predictions. Independent confirmatory data must remain inaccessible until the
protocol, cohort, feature schema, model, and threshold are frozen.
