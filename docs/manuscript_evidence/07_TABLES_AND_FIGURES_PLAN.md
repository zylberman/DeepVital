# Tables and figures plan

## Main tables

| Table | Content | Source | Reproducible now? | Missing/caution |
|---|---|---|---|---|
| 1 | Cohort flow/composition | `canonical_cohort_metadata.json`, `canonical_v1/*.json` | Yes, aggregate | Patient-level mutually exclusive flow and demographics absent |
| 2 | Eighteen locked predictors | Phase 3 protocol, prefreeze code, FHIR/unit configs | Yes | Derived predictors lack single FHIR code; state this |
| 3 | Formal pooled performance | `phase3_model_comparison.csv`, incremental JSON | Yes | Comparator Brier/log loss deliberately NA |
| 4 | Paired candidate-vs-comparator comparisons | `phase3_paired_comparisons.csv` | Yes | CI is clustered percentile bootstrap, not confirmatory p-value |

## Supplementary tables

| Table | Source | Status |
|---|---|---|
| Outer-fold accounting, selected C, inner AUPRC and thresholds | `phase3_incremental_value.json:folds` | Reproducible; per-fold outer performance metrics are not persisted separately |
| Hyperparameters and preprocessing | `phase3_frozen.json`, protocol | Complete |
| Outcome/BP/patient-weight sensitivities | `phase3_sensitivity_analysis.json` | Complete except two explicitly failed analyses |
| Protocol deviations | `phase3_protocol_deviations.json` | Empty primary-deviation table plus sensitivity-failure note |
| Variable/FHIR/unit dictionary | FHIR and unit configs | Reproducible |
| Bootstrap summary | Phase 3 paired CSV and incremental JSON | Primary/secondary paired results available; replicate-level rows private/not persisted publicly |
| TRIPOD+AI checklist | `06_TRIPOD_PROBAST_GAP_AUDIT.md` | Preliminary only |

## Proposed figures

| Figure | Purpose | Data source / existing code | Current feasibility | Interpretation risk |
|---|---|---|---|---|
| Cohort flow | Separate patients/stays/windows and exclusions | Aggregate cohort JSON; no existing dedicated Phase 3 plot | Can be drawn from aggregate counts | Exclusion counters are not unique patients and may overlap by construction stage |
| Temporal diagram | Show `t-11..t` and `t+1..t+6` | Configs and window code | Fully reproducible | Do not imply non-overlapping windows |
| Nested-CV diagram | Show 5 outer/3 inner patient grouping | Frozen config and fold accounting | Fully reproducible schematically | Never expose private patient assignments |
| OOF ROC/PR curves | Compare raw logistic and `map_mean_6h` | Requires patient-level OOF scores not tracked publicly; generic plotting code exists | Not reproducible from public aggregate files alone | Reconstructing/rerunning Phase 3 is prohibited for this packet |
| Calibration plot | Candidate development calibration | Aggregate intercept/slope exist; point-level probabilities unavailable publicly | Only schematic/summary possible | Comparator is not calibrated; avoid clinical calibration claims |
| Forest plot | Delta AUPRC/AUROC and sensitivity CIs | Paired CSV and sensitivity JSON | Reproducible from aggregate values | Label sensitivities and failed analyses clearly; do not select favorable cells |
| Decision sensitivity grid | Show nine outcome-definition deltas | Sensitivity JSON | Reproducible | Primary 65×2 cell must remain visually distinguished |

No graph should be fabricated from rounded narrative values. Aggregate figures can
be created later from frozen structured files without rerunning the clinical
analysis; point-level ROC/PR/calibration curves require governed access to preserved
OOF predictions or a separately approved reproduction.
