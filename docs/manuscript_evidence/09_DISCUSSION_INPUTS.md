# Discussion inputs

## Manuscript-ready principal interpretation

“The frozen multivariable logistic candidate showed a small positive incremental
AUPRC over six-hour mean MAP, but the observed improvement did not reach the
preregistered absolute +0.020 development relevance margin required to justify
additional complexity. Under the mechanical advancement rule, the candidate did
not advance and `map_mean_6h` was retained as the parsimonious development
strategy.”

## Contributions supported internally

- A leakage-resistant temporal task with explicit `t` versus future boundaries.
- Patient-grouped nested validation with training-fold preprocessing and inner-only
  selection/calibration/threshold operations.
- Direct comparison of a frozen multivariable candidate against a strong,
  interpretable physiological comparator.
- Paired patient-cluster inference that respects the patient grouping unit.
- Preregistration, fingerprints, preserved failure states, and a non-advancement
  decision reported without result-driven rerun.

## Why the negative advancement result matters

The result is not “no improvement”: delta AUPRC and its interval were positive.
It is a failure to meet a preregistered complexity-justification margin. This
supports parsimony under the specific development protocol while preserving the
possibility that a small incremental signal exists. Secondary or favorable
sensitivity results cannot override the primary rule.

## Strengths

- Frozen 18-feature candidate and closed hyperparameter space.
- Zero patient overlap and one OOF prediction per eligible window.
- Comparator and candidate evaluated on identical windows/folds/bootstrap samples.
- Transparent score semantics: `map_mean_6h` is ranking-only, not a probability.
- Formal primary deviation log empty; failed sensitivities disclosed.

## Limitations to discuss prominently

- Demo cohort, 92 eligible patients, and limited effective sample size.
- Correlated overlapping windows and unequal patient contribution.
- Retrospective proxy outcome without treatment context or adjudication.
- Selection induced by requiring complete future MAP observation.
- Provisional BP source pooling and local code mappings.
- Failed incomplete-future-MAP sensitivity datasets.
- No external, confirmatory, prospective, workflow, utility, or impact evidence.
- Runtime environment not fully locked and private inputs unavailable publicly.
- Historical 1,551-window holdout accessed four times; historical development only.

## Claims requiring external literature

- Clinical burden and consequences of ICU hypotension.
- Rationale and guideline context for MAP <65 mmHg.
- Expected intervention window and treatment implications.
- Prior prediction-model limitations and comparative performance.
- Methodological guidance for nested CV, clustered bootstrap, TRIPOD+AI, and PROBAST+AI.
- MIMIC-IV/MIMIC-IV FHIR construction, deidentification, and representativeness.

## Permitted and prohibited interpretation

Permitted: internal development discrimination; small positive incremental signal;
non-advancement under a frozen rule; need for independent evaluation.

Avoid: clinical superiority, clinical utility, validated threshold, calibrated
clinical risk, generalizability, causal predictor importance, external validation,
confirmatory success, or readiness for deployment.

## Focused bibliography searches pending

1. Official MIMIC-IV and MIMIC-IV-on-FHIR records and version documentation.
2. Official TRIPOD+AI statement/checklist and explanation paper.
3. Official PROBAST+AI tool/guidance.
4. Primary guideline/consensus sources for MAP thresholds in ICU populations.
5. Primary methods literature on clustered repeated prediction windows and internal validation.
