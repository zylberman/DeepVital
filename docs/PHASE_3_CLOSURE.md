# Phase 3 closure record

**Protocol:** `deepvital-phase3-incremental-value-v1`
**Status:** completed and closed for development analysis
**Formal execution:** once, at `2026-08-09T04:25:24.406193+00:00`
**Data role:** internal development only
**Confirmatory status:** `confirmatory_test_pending`

## Frozen question and decision

Phase 3 asked whether one prespecified, interpretable 18-predictor L2 logistic
strategy provided reproducible incremental predictive value beyond six-hour mean
MAP. The primary delta AUPRC was `+0.0075286864432581035` (paired patient-level
bootstrap 95% interval `+0.0004996287013002788` to
`+0.01712977187518211`). It did not reach the frozen `+0.020` development
relevance margin. The logistic candidate therefore did not advance, and
`map_mean_6h` remains the parsimonious development strategy.

The margin was not a p-value threshold or a clinically validated minimal important
difference. This internal result does not establish clinical validity, utility, or
transportability.

## Immutable evidence and provenance

| Item | Identifier |
| --- | --- |
| Frozen protocol commit | `158656304a96a4229208aad7e07fe45959672bfe` |
| Frozen protocol SHA-256 | `sha256:c0b2e69ee468fed8f257ee65bfc46ff396db2bc6a29dab9e2dd898e15fa27eb5` |
| Implementation/preregistered source | `54414fae32cc1c8b7cece36b2f1a96d81a48db35` |
| Preregistration tag | `phase3-preregistered-v1` |
| Preregistration JSON SHA-256 | `03bf1ce0efa6eb5e431b1e76654a878e9059353c8f6d11cdd0d6d09f6632a7c1` |
| Original formal result commit | `c7db731` |
| CSV line-ending-only normalization | `d3c6915` |
| Result integration | PR #5 |
| Result release tag | `phase3-development-results-v1` |

The archived preregistration is
`reports/archive/phase3_protocol_registration_v1.json`; its SHA-256 matches the
preregistered value above. The five formal result artifacts under `reports/` are
the authoritative, immutable record. The formal analysis was not rerun after
results were observed.

## Evaluation integrity

The formal development analysis used 92 patients and 8,970 eligible windows, five
outer and three inner patient-grouped folds, zero patient overlap, and exactly one
outer out-of-fold prediction per eligible window. The formal report records no
primary protocol deviation.

Patient-equal delta AUPRC was `+0.015609437384234592`. The invasive-preferred BP
delta was `+0.006657565477214078`, with 95% interval
`-0.0024251481794628875` to `+0.01797647666299435`; the non-invasive-only BP delta
was `-0.0004748683148032562`, with interval `-0.011053034932439771` to
`+0.013534537024808382`. Both BP-source analyses met the frozen robustness floor
of not falling below `-0.020`; neither overrides the primary decision.

## Unresolved sensitivities

The `missing_as_low` and `missing_as_not_low` incomplete-future-MAP sensitivities
failed because their inputs contained patients absent from the frozen private fold
manifest. The failure is disclosed and was not repaired by rerunning Phase 3. Any
later investigation must be labeled post-Phase-3 supplementary technical work and
must not replace the original result.

## Closure boundary

Phase 3 is closed for analysis on this development cohort. The frozen protocol,
configuration, formal reports, predictor set, hyperparameters, endpoint, primary
metric, and `+0.020` rule must not be retrospectively changed. Further model
shopping or repeated analysis on this cohort is not warranted. The next evidential
step is evaluation in a genuinely independent cohort under a separately governed
protocol; no confirmatory or external validation has yet been completed.
