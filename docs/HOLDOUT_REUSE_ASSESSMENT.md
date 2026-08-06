# Holdout reuse assessment

**Assessment date:** 2026-08-05  
**Historical evaluation name:** `development_holdout_v1`  
**Evaluation role:** development  
**Confirmatory holdout:** no

> Estos resultados corresponden a evaluación de desarrollo. El conjunto fue
> accedido cuatro veces y no debe interpretarse como un holdout confirmatorio
> intacto.

## Evidence boundary

Git first records the Phase 2 implementation, metrics, model-selection metadata,
and all four accesses together in commit `d32425e` dated 2026-07-28 15:17:40
-05:00. The committed selection record already has `test_evaluation_count: 4`.
There are no four commits, immutable run logs, or four separately timestamped
artifacts. Consequently, the date and commit of each individual access cannot be
reconstructed. It would be incorrect to invent that chronology.

## Chronology supported by the repository

1. Commit `f15f2fd` froze the historical 8,872-window Phase 1B build and patient
   split.
2. Phase 2 training selected `map_mean_6h` from training and validation and locked
   its Youden threshold at `0.37754066879814546`.
3. The developmental holdout was accessed four times before commit `d32425e`.
   Documentation in that commit identifies a correction to average precision for
   tied constant predictions, regeneration after making the configured selection
   rule executable, and regeneration to persist an unambiguous post-evaluation
   lock state. The exact one-to-one mapping of these descriptions to accesses is
   not recoverable from Git.
4. After `d32425e`, commits on `main` changed security, lint, documentation, and
   the isolated synthetic demo. The diff through `cc9222c` shows no changes to
   clinical features, candidate models, hyperparameters, thresholds, labeling,
   or exclusion configuration.

## Potentially influenced decisions

The repeated access can have influenced debugging, metric implementation,
report-generation behavior, documentation, and confidence in the selected result.
Git does not show a post-result change to the selected model, frozen threshold,
feature set, model hyperparameters, or Phase 1B exclusion criteria. Absence of a
committed change is not proof that no uncommitted judgment was influenced.

The four runs were therefore not four independent confirmatory evaluations and
cannot be classified as purely identical technical reproductions. At least some
were associated with methodology or reporting corrections after results had been
observed.

## Impact classification

Impact is **high for confirmatory interpretation** and **moderate for internal
development use**. The metrics remain useful as historical development evidence,
but they cannot provide an unbiased final performance estimate. No counter is
reset, reduced, or hidden.

## Items that cannot be verified

- exact timestamp and commit for each access;
- whether any uncommitted experiment occurred between accesses;
- which result was visible before each correction;
- whether informal decisions not represented in Git were influenced;
- bit-for-bit identity of inputs, environment, and serialized models for every run.

## Decision

All 100 patients used by this experiment are development data. The historical test
partition is now formally named `development_holdout_v1`, has
`evaluation_role: development`, `confirmatory_holdout: false`, and retains
`test_evaluation_count: 4`. A future confirmatory evaluation requires completely
new patients and a preregistered protocol, frozen cohort definition, model, and
threshold.

