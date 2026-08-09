# DeepVital academic roadmap

The roadmap is evidence-gated. Software completion and internal development results
do not establish clinical readiness.

## Current decision

Phase 3 is complete. The frozen logistic candidate showed a small positive
incremental AUPRC over `map_mean_6h`, but the gain did not reach the prespecified
`+0.020` development relevance margin. `map_mean_6h` is therefore retained as the
parsimonious development strategy.

The immediate next step is not to try additional models until one wins on the same
cohort. Such model shopping would weaken the interpretation of the completed
prespecified analysis.

## Next-stage priorities

1. **Consolidate Phase 3 evidence.** Complete documentation and manuscript-ready
   reporting without changing the frozen decision rule or result.
2. **Investigate the incomplete-future-MAP failure.** Diagnose the fold-manifest
   mismatch as explicitly post-Phase-3 technical or supplementary work. Preserve
   the failed original sensitivity outputs and do not present later work as a rerun
   or replacement of the preregistered analysis.
3. **Secure a genuinely independent cohort.** Establish permissions, governance,
   ethics, storage, retention, and publication controls before access.
4. **Reproduce the parsimonious benchmark externally.** Evaluate `map_mean_6h` in
   new patients and a distinct setting. If scientifically justified in advance,
   also reproduce the frozen 18-predictor logistic candidate without adapting it to
   the new outcomes.
5. **Assess transportability and calibration.** Examine cohort shift, BP-source and
   charting differences, discrimination, calibration, and operating-point behavior
   without describing development thresholds as clinically validated.
6. **Reconsider model development only after independent evidence.** Decide whether
   further feature or model work is scientifically warranted from transportability
   findings, not by continued optimization on the 92-patient development cohort.
7. **Preserve the confirmatory boundary.** Keep confirmatory outcomes isolated until
   a future confirmatory protocol, strategy, calibration and threshold are frozen.
8. **Consider prospective work only after adequate independent evidence.** Silent
   evaluation, workflow studies, impact evaluation and deployment remain later
   evidence stages.

## Continuing technical priorities

- lock or constrain the runtime environment and preserve provenance;
- maintain privacy-safe aggregate reporting and private patient-level artifacts;
- document data-source and charting differences before cross-site comparisons;
- define supportable subgroup analyses before accessing larger datasets;
- retain human review for any drift or model-update decision.

## Deferred work

Deep learning, new model families, explainability dashboards, drift monitoring,
workflow integration and deployment are not immediate next steps. They should be
considered only for a prospectively defined scientific question and after the
parsimonious strategy has been evaluated independently.
