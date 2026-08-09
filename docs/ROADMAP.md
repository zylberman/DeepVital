# DeepVital academic roadmap

The roadmap is evidence-gated. Progress to a later stage does not follow solely
from software completion and must not be interpreted as clinical readiness.

## Immediate scientific decision

Determine whether the six-hour mean MAP benchmark should remain the preferred
parsimonious development strategy or whether additional multivariable modeling can
demonstrate reproducible added value. Complexity is not an objective in itself.

## Milestones

1. **Model-strategy decision.** Review nested-CV discrimination, availability,
   interpretability, and limitations; document the development decision without
   accessing confirmatory data.
2. **Calibration strategy.** If the selected strategy produces probabilities,
   specify training-only calibration and sample-size requirements. If it remains a
   ranking score, define whether and how calibration will be developed.
3. **Outcome sensitivity.** Evaluate prespecified MAP thresholds, duration rules,
   and incomplete-future-MAP handling without replacing the primary definition.
4. **Blood-pressure-source analysis.** Quantify invasive/non-invasive source
   composition, simultaneous measurements, and alternative precedence rules.
5. **Missingness sensitivity.** Assess neutral-score handling, complete cases,
   charting frequency, and informative missingness.
6. **Subgroup planning.** Define supportable exploratory strata and minimum sample
   requirements before a larger dataset is accessed.
7. **Environment reproducibility.** Pin or lock runtime dependencies, record Python
   and package versions, and resolve or document Joblib/NumPy compatibility.
8. **Restricted dataset application.** Establish purpose, permissions, ethics and
   data-use statements, storage, retention, and publication controls for new data.
9. **Frozen confirmatory protocol.** Freeze cohort, features, strategy, calibration,
   threshold, primary estimand, and fingerprints.
10. **Independent confirmatory evaluation.** Execute once on entirely new patients;
    record first consumption and disclose deviations.
11. **External validation.** Evaluate an independently sourced clinical setting.
12. **Prospective planning.** Consider silent evaluation only after adequate
    confirmatory and external evidence and governance review.

## Deferred work

Temporal neural networks, explainability dashboards, drift monitoring, workflow
integration, and deployment should be pursued only when they address a defined
scientific question and can be compared fairly with the parsimonious benchmark.
They are not prerequisites for a valid current development conclusion.
