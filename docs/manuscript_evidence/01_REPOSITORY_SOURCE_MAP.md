# Repository source map

The audit inventoried 170 paths returned by `rg --files`. The following map lists
the sources materially relevant to a Phase 3 manuscript. Priority follows the
evidence hierarchy: frozen structured results, producer code, frozen protocol,
model card/current methods, then narrative summaries.

| Area | Principal files | Function | Status / hierarchy |
|---|---|---|---|
| Frozen results | `reports/phase3_incremental_value.json`; `phase3_model_comparison.csv`; `phase3_paired_comparisons.csv`; `phase3_sensitivity_analysis.json`; `phase3_protocol_deviations.json` | Primary metrics, paired estimates, sensitivities, deviations | Canonical, highest priority |
| Preregistration | `reports/archive/phase3_protocol_registration_v1.json`; `reports/phase3_protocol_registration.json` | Frozen hashes, inputs, source commit | Canonical provenance |
| Frozen specification | `docs/PHASE_3_PROTOCOL.md`; `configs/phase3_frozen.json` | Question, 18 predictors, model, folds, calibration, thresholds, decision rule | Frozen protocol |
| Phase 3 implementation | `src/deepvital/phase3/{implementation,prefreeze,sensitivities,provenance,generation}.py`; `scripts/run_phase3.py` | Produces formal analysis and safeguards | Producer code; do not rerun |
| Fold creation | `scripts/create_phase3_fold_manifest.py`; Phase 3 prefreeze code | Private deterministic patient grouping | Code public; manifest private/ignored |
| Cohort metadata | `reports/canonical_cohort_metadata.json`; `reports/canonical_v1/*.json` | Counts, flow, fingerprint, split summaries | Canonical aggregate cohort evidence |
| Cohort construction | `scripts/build_canonical_cohort.py`; `src/deepvital/cohort/*`; `src/deepvital/preprocessing/*` | ICU-period grid, hourly aggregation, missingness | Producer code |
| FHIR extraction | `scripts/extract_canonical_vitals.py`; `src/deepvital/fhir/*`; `configs/fhir_vital_signs.yaml`; `configs/unit_conversions.yaml` | Resource streaming, mappings, normalization, QC | Producer code/configuration |
| Window/label | `src/deepvital/features/windows.py`; `src/deepvital/windows/builder.py`; `src/deepvital/labeling/hypotension.py`; `configs/{windowing,labeling,missingness}.yaml` | 12-hour history and future-only outcome | Producer code/configuration |
| General nested CV | `src/deepvital/evaluation/nested_cv.py`; `reports/internal_nested_cross_validation.json`; `internal_nested_*.csv` | Earlier broad internal comparison | Development context, not Phase 3 final decision |
| Metrics/inference | `src/deepvital/evaluation/{metrics,bootstrap,calibration}.py` | AUROC/AUPRC, losses, thresholds, clustered bootstrap | Producer code |
| Historical holdout | `models/baselines/model_selection.json`; `reports/test_metrics.csv`; `docs/HOLDOUT_REUSE_ASSESSMENT.md` | Four-access legacy development holdout | Historical only; not confirmatory |
| Current narrative | `docs/{METHODS_CURRENT,RESULTS_CURRENT,MODEL_CARD,PROJECT_STATUS,LIMITATIONS}.md`; `README.md` | Manuscript-ready narrative and limitations | Secondary to structured artifacts |
| Closure | `docs/PHASE_3_CLOSURE.md`; tag `phase3-final-closure-v1` | Defines immutable result and closure boundary | Current closure record |
| Reproducibility | `docs/REPRODUCIBILITY.md`; `requirements*.txt`; `Makefile`; `.github/workflows/ci.yml` | Public checks, environment and CI | Current, dependencies partly unpinned |
| Tests | `tests/test_phase3_*.py`; `test_evaluation_protocol.py`; other `tests/` | Synthetic methodological/software contracts | 101 passing at audit |
| Synthetic demonstration | `scripts/{generate_synthetic_demo,run_synthetic_demo}.py`; `tests/test_synthetic_demo.py` | Public end-to-end software example | Not clinical evidence |
| Governance | `docs/DATA_GOVERNANCE.md`; `.gitignore`; `.env.example` | Privacy and publication boundary | Project-level safeguards, not institutional approval |
| Dataset inventory | `docs/{FHIR_DATA_INVENTORY,FHIR_TO_CANONICAL_MAPPING,CANONICAL_DATA_MODEL}.md`; `reports/fhir_*` | Aggregate FHIR structure and mappings | Supporting evidence |
| Legacy/historical docs | `docs/AUDIT.md`; `CODEX_MASTER_SPEC.md`; `COHORT_DEFINITION.md`; Phase 1/2 docs | Earlier state and requirements | Cite only with status context |
| License/citation | no `LICENSE`, `CITATION.cff`, Zenodo file, or DOI found | Publication metadata | Missing |
| Public repository | Git remote `https://github.com/zylberman/DeepVital.git` | Code location | Verified locally |

No patient-level data, predictions, or private fold assignments are included in
this evidence packet.
