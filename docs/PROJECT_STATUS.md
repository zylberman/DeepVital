# DeepVital project status

**Status date:** 2026-08-09

**Repository state reviewed:** Phase 3 results merged through PR #5

**Intended use:** retrospective methodological research only

## Summary

DeepVital implements a reproducible pipeline from FHIR resource inspection through
prespecified patient-grouped development evaluation. Phase 3 is complete. The
prespecified 18-predictor L2 logistic candidate showed a small positive incremental
AUPRC over `map_mean_6h`, but the gain did not reach the frozen `+0.020`
development relevance margin. `map_mean_6h` is therefore retained as the
parsimonious development strategy.

This is development evidence from a small demonstration dataset. DeepVital is not
a medical device or clinical decision-support system. No confirmatory, external,
prospective, workflow, or clinical-impact evaluation has been completed.

## Completed phases

| Phase | Completed work | Current interpretation |
| --- | --- | --- |
| Phase 1 | Canonical FHIR extraction, ICU-bounded hourly processing, cohort and future-only outcome | Canonical development cohort established |
| Phase 2 | Clinical/simple and conventional ML baselines | Six-hour mean MAP identified as the strongest parsimonious benchmark |
| Phase 2.5 | Fingerprints, source-state metadata, private/public artifact boundaries | Reproducibility infrastructure established |
| Holdout-protocol repair | Historical holdout reclassified; patient-grouped nested internal evaluation implemented | Repeated holdout is development history, not confirmation |
| Phase 3 | Frozen incremental-value and robustness analysis | Completed once; logistic candidate did not advance under the frozen rule |

## Current cohort and evaluation

The canonical development cohort represents 100 patients, 128 hospital admissions,
and 140 ICU stays. Ninety-two patients contribute 8,970 eligible windows, including
1,774 positive windows. The 8,970 overlapping windows are clustered observations,
not independent individuals.

Phase 3 used five outer and three inner folds grouped by patient. Patient overlap
was zero, and each eligible window received exactly one outer-fold OOF prediction.
There was one formal preregistered Phase 3 development execution; it was not rerun
after results were observed.

## Phase 3 primary result and decision

| Quantity | Result |
| --- | ---: |
| `map_mean_6h` AUPRC | 0.6218694691 |
| Raw logistic AUPRC | 0.6293981556 |
| Delta AUPRC, logistic minus benchmark | +0.0075286864 |
| Paired patient-bootstrap 95% CI | +0.0004996287 to +0.0171297719 |
| Valid bootstrap replicates | 1,000 |
| Prespecified development relevance margin | +0.020 |

The candidate produced a small positive incremental signal, and the paired interval
was above zero. The observed gain nevertheless failed the prespecified `+0.020`
advancement criterion. That margin is not a p-value and is not a clinically
validated minimal important difference. Added complexity was not justified under
the frozen development rule, so `map_mean_6h` remains the parsimonious development
strategy.

The calibrated candidate and its thresholds remain recorded development outputs;
they are not deployment parameters or clinically validated operating points.

## Sensitivities and disclosed failure

The prespecified outcome grid, BP-source alternatives, missing-score analysis,
patient-equal evaluation, and charting summaries were reported. Both BP-source
deltas satisfied the robustness floor of not falling below `-0.020`.

The `missing_as_low` and `missing_as_not_low` incomplete-future-MAP sensitivities
failed because their datasets contained patients absent from the frozen fold
manifest. This disclosed sensitivity-analysis execution failure did not change the
primary result and the formal run was not repeated. Any later investigation must be
labeled post-Phase-3 technical or supplementary work.

## Evidence boundary

The earlier 8,872-window holdout remains `development_holdout_v1`, with four
recorded accesses. It is historical development evidence and not an untouched
confirmatory test. Phase 3 is also development-only internal evidence.
`confirmatory_test_pending` remains unchanged.

## Next milestone

Consolidate Phase 3 reporting, investigate the failed incomplete-future-MAP inputs
without rewriting the original result, and seek a genuinely independent cohort.
External work should first reproduce `map_mean_6h` and, if scientifically justified,
the frozen logistic candidate, then assess transportability and calibration. No
additional model shopping on this development cohort is warranted.
