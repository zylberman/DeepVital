# DeepVital documentation index

This index distinguishes current sources of truth from historical records. Code,
configuration, and versioned aggregate reports take precedence over narrative
documentation when a discrepancy is found.

## Project overview

| Document | Purpose | Audience | Status |
| --- | --- | --- | --- |
| `../README.md` | Repository entry point and concise current evidence summary | All readers | Current |
| `PROJECT_STATUS.md` | Current methodological state and next milestone | Collaborators and reviewers | Current |
| `ROADMAP.md` | Evidence-gated academic development plan | Research team | Current plan |

## Scientific protocol

| Document | Purpose | Audience | Status |
| --- | --- | --- | --- |
| `RESEARCH_PROTOCOL.md` | Manuscript-grade protocol separating completed and planned work | Investigators and access reviewers | Current |
| `METHODS_CURRENT.md` | Continuous manuscript-ready methods | Manuscript authors | Current |
| `STATISTICAL_ANALYSIS_PLAN.md` | Pre-Phase-3 nested-CV estimands and reporting rules | Methodologists and statisticians | Historical methodological record |
| `EVALUATION_PROTOCOL.md` | Pre-Phase-3 frozen evaluation-role and leakage rules | Reproducibility reviewers | Historical methodological record |

## Data and cohort

| Document | Purpose | Audience | Status |
| --- | --- | --- | --- |
| `CANONICAL_DATA_MODEL.md` | Phase 1A local schema and relationship invariants | Data engineers | Current |
| `FHIR_TO_CANONICAL_MAPPING.md` | Implemented code/unit mappings and limitations | Clinical data reviewers | Current, with stated limitations |
| `PHASE_1B_COHORT_DECISION.md` | Rationale for the administrative ICU-bounds route | Methodological reviewers | Current decision record |
| `WINDOWING_AND_LABELING.md` | Current temporal processing and outcome contract | Researchers and engineers | Current |
| `COHORT_FLOW.md` | Canonical aggregate cohort accounting | Reviewers | Current |
| `PHASE_1B_DATA_DICTIONARY.md` | Private local hourly/window schema | Authorized developers | Current |

## Evaluation and results

| Document | Purpose | Audience | Status |
| --- | --- | --- | --- |
| `RESULTS_CURRENT.md` | Current canonical internal-development results | Manuscript readers | Current |
| `PHASE_3_CLOSURE.md` | Immutable Phase 3 result, provenance, decision, and closure boundary | Auditors and investigators | Current closure record |
| `CLINICAL_BENCHMARK_AUDIT.md` | Ranking/probability semantics and missing-score policy | Methodologists | Current |
| `EXPERIMENT_REGISTRY.md` | Separation of historical, internal, and future confirmatory experiments | Auditors | Current |
| `VALIDATION_STRATEGY.md` | Development-to-prospective validation hierarchy | Investigators | Current plan |
| `HOLDOUT_REUSE_ASSESSMENT.md` | Transparent reconstruction of historical repeated access | Auditors | Current historical assessment |

## Reproducibility and governance

| Document | Purpose | Audience | Status |
| --- | --- | --- | --- |
| `REPRODUCIBILITY.md` | Public/software and authorized-data reproducibility boundaries | Reproducibility reviewers | Current |
| `DATA_GOVERNANCE.md` | Local clinical-data controls and future restricted-data principles | Access and governance reviewers | Current project policy |
| `ARCHITECTURE.md` | Software and data-flow architecture | Engineers and reviewers | Current |
| `DATA_LEAKAGE_SAFEGUARDS.md` | Earlier Phase 1B leakage audit | Methodological reviewers | Historical; see header |

## Limitations

| Document | Purpose | Audience | Status |
| --- | --- | --- | --- |
| `LIMITATIONS.md` | Data, methodological, statistical, clinical, and deployment limitations | All scientific readers | Current |
| `MODEL_CARD.md` | Current retained strategy and non-advancing Phase 3 candidate | Model reviewers | Current |

## Historical documentation

The following files preserve development history and must not be treated as the
current project state without the current documents above:

- `AUDIT.md`: initial Phase 0 repository audit;
- `CODEX_MASTER_SPEC.md`: aspirational implementation specification;
- `FHIR_DATA_INVENTORY.md`: pre-extraction discovery record;
- `COHORT_DEFINITION.md`: historical 8,872-window route;
- `PHASE_1B_COMPLETION_AUDIT.md`: historical route completion audit;
- `PHASE_2_PROTOCOL.md`, `PHASE_2_RESULTS.md`, and `MODEL_SELECTION.md`: historical
  train/validation/developmental-holdout experiment;
- `../DeepVital_Fase_1_Informe_para_articulo.md`: filename retained for history,
  content updated to summarize the present project state.

## Evidence files

The principal machine-readable sources are:

- `../reports/canonical_extraction_quality.json`;
- `../reports/canonical_cohort_metadata.json`;
- `../reports/canonical_v1/`;
- `../reports/internal_nested_cross_validation.json`;
- `../reports/internal_nested_model_comparison.csv`;
- `../reports/internal_nested_paired_comparisons.csv`;
- `../reports/phase3_incremental_value.json`;
- `../reports/phase3_model_comparison.csv`;
- `../reports/phase3_paired_comparisons.csv`;
- `../reports/phase3_sensitivity_analysis.json`;
- `../reports/phase3_protocol_deviations.json`;
- `../reports/archive/phase3_protocol_registration_v1.json` (archived preregistration);
- `../models/baselines/model_selection.json` for the historical holdout record.
