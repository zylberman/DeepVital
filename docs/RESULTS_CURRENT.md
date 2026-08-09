# Current results

All results in this document are retrospective development results. They do not
establish clinical effectiveness, generalizability, or confirmatory performance.

## Canonical cohort construction

Canonical extraction retained 89,415 supported observations representing 100
patients, 128 hospital admissions, and 140 ICU stays. The administrative ICU-bounds
route excluded 270 observations outside exact ICU periods and produced 12,502
hourly rows. Of 10,185 candidate prediction times, 1,215 were excluded because
future MAP assessment was insufficient. The final cohort comprised 8,970 eligible
windows, including 1,774 positive and 7,196 negative windows, for a prevalence of
19.78%.

| Quantity | Canonical result |
| --- | ---: |
| Patients represented | 100 |
| Patients with eligible windows | 92 |
| Hospital admissions | 128 |
| ICU stays | 140 |
| Hourly rows | 12,502 |
| Eligible windows | 8,970 |
| Positive windows | 1,774 |
| Event prevalence | 0.1978 |

These counts are supported by `reports/canonical_cohort_metadata.json` and
`reports/canonical_v1/`.

## Internal nested cross-validation

Five outer and three inner patient-grouped folds were used. The internal report
confirmed that each patient was assigned to one outer fold, all windows remained
with their patient, there was no patient overlap between outer folds, and all 8,970
windows received exactly one out-of-fold prediction.

| Strategy | Output type | AUROC (95% CI) | AUPRC (95% CI) | Brier score (95% CI) | Log loss |
| --- | --- | --- | --- | --- | ---: |
| Constant training prevalence | Probability | 0.4565 (0.3825–0.5364) | 0.1826 (0.1334–0.2533) | 0.1590 (0.1299–0.1871) | 0.4985 |
| Last MAP | Ranking score | 0.8216 (0.7856–0.8559) | 0.5613 (0.4464–0.6538) | Not applicable | Not applicable |
| Six-hour mean MAP | Ranking score | 0.8416 (0.7984–0.8809) | 0.6219 (0.4914–0.7210) | Not applicable | Not applicable |
| Six-hour minimum MAP | Ranking score | 0.8221 (0.7761–0.8637) | 0.5196 (0.3941–0.6250) | Not applicable | Not applicable |
| MAP slope | Ranking score | 0.6174 (0.5933–0.6413) | 0.2564 (0.1978–0.3189) | Not applicable | Not applicable |
| Shock index | Ranking score | 0.6390 (0.5774–0.6944) | 0.2987 (0.2068–0.3847) | Not applicable | Not applicable |
| Modified shock index | Ranking score | 0.7098 (0.6582–0.7594) | 0.3965 (0.2756–0.5007) | Not applicable | Not applicable |
| Nested ML strategy | Probability | 0.8185 (0.7747–0.8633) | 0.5333 (0.4226–0.6423) | 0.1354 (0.1092–0.1605) | 0.4228 |

The clinical ranking scores were not post-hoc calibrated; Brier score and log loss
are intentionally not reported for them. The nested ML output was also not
post-hoc calibrated, although its probability losses remain descriptive.

## Paired benchmark comparisons

In paired patient bootstrap, six-hour mean MAP minus nested ML yielded an observed
AUPRC difference of 0.0886 (95% interval 0.0205–0.1453; 99.6% of valid bootstrap
differences above zero) and an AUROC difference of 0.0231 (0.0010–0.0419; 98.0%
above zero). All 1,000 requested replicates were valid.

These estimates support the restrained statement that six-hour mean MAP showed
higher internal discrimination than the tested nested ML strategy in the current
development cohort. They do not establish clinical superiority, equivalence in
other metrics, transportability, or a final model choice.

## Missing benchmark values

The primary neutral-score analysis used 0.5 when a clinical score could not be
calculated. Last MAP and modified shock index were unavailable for 9 windows from 9
patients; shock index was unavailable for 8 windows from 8 patients. Six-hour mean
MAP, six-hour minimum MAP, and MAP slope were available for all eligible windows.
The report also contains complete-case sensitivity summaries.

## Constant-prevalence interpretation

Each outer fold used the prevalence of its corresponding training data. Within a
fold, this score is constant and has AUROC 0.5 when both classes are present.
Different prevalence values across folds can produce a pooled AUROC different from
0.5. The pooled value of 0.4565 is therefore not evidence of discrimination.

## Historical development holdout

The historical observation-bounded cohort contained 8,872 windows, including 1,759
positive windows. Its earlier selected six-hour mean MAP benchmark had validation
AUROC 0.7897 and AUPRC 0.6124 and developmental-holdout AUROC 0.8649 and AUPRC
0.5490. These values are preserved in the historical reports and must not be mixed
with canonical nested-CV results.

The partition was accessed four times. It is now named `development_holdout_v1`,
has the role `development`, and is not confirmatory. The repeated access has high
impact on confirmatory interpretation; Git history does not support reconstructing
every execution with complete certainty.

## Prespecified Phase 3 incremental-value analysis

Phase 3 compared `map_mean_6h` with one frozen 18-predictor L2 logistic strategy in
the same 92-patient, 8,970-window development cohort. It used five outer and three
inner patient-grouped folds, zero patient overlap, exactly one OOF prediction per
eligible window, and 1,000 paired patient-bootstrap replicates. There was one formal
preregistered execution, with no result-driven rerun.

| Quantity | `map_mean_6h` | Raw logistic candidate | Candidate minus benchmark |
| --- | ---: | ---: | ---: |
| AUPRC | 0.6218694691 | 0.6293981556 | +0.0075286864 |
| AUROC | 0.8416282800 | 0.8447827084 | +0.0031544285 |

The primary delta-AUPRC paired 95% interval was `+0.0004996287` to
`+0.0171297719`; all 1,000 replicates were valid and 0.987 of bootstrap differences
were above zero. The secondary delta-AUROC interval was `-0.0002853698` to
`+0.0066426853`.

The logistic candidate therefore showed a small positive incremental AUPRC, but its
`+0.0075` gain did not reach the prespecified `+0.020` development relevance margin.
The candidate failed the frozen advancement rule, and `map_mean_6h` remains the
parsimonious development strategy. The `+0.020` margin is neither a p-value nor a
clinically validated minimal important difference.

## Calibration and development operating points

The calibrated candidate had AUPRC 0.6255061186, AUROC 0.8434693457, Brier score
0.1114882686, and log loss 0.3619400064. Its recorded development operating points
were 0.5 fixed, 0.3208213008 for target sensitivity 0.80, and 0.3775406688 by the
Youden procedure. These are development summaries, not validated clinical or
deployment thresholds.

## Phase 3 robustness and sensitivity results

Patient-equal delta AUPRC was `+0.0156094374`. Invasive-preferred BP construction
yielded delta AUPRC `+0.0066575655` (95% interval `-0.0024251482` to
`+0.0179764767`); non-invasive-only yielded `-0.0004748683`
(`-0.0110530349` to `+0.0135345370`). Both met the frozen robustness condition of
not falling below `-0.020`.

The prespecified outcome-grid delta AUPRC values were:

| Strict MAP threshold | 1 hour | 2 consecutive hours | 3 consecutive hours |
| --- | ---: | ---: | ---: |
| <60 mmHg | +0.0024470062 | +0.0027222423 | +0.0199924643 |
| <65 mmHg | +0.0062732192 | +0.0075286864 (primary) | +0.0139717236 |
| <70 mmHg | +0.0034531672 | +0.0053589107 | +0.0010087804 |

These are sensitivity analyses and do not redefine the primary endpoint. In
particular, the `<60 mmHg × 3 hours` result was not selected post hoc.

The two incomplete-future-MAP sensitivities, `missing_as_low` and
`missing_as_not_low`, failed with `ValueError: Dataset contains patients absent
from private fold manifest`. The failure was disclosed, Phase 3 was not rerun to
repair it, and the primary advancement result was unchanged. The formal deviation
report records `protocol_deviations = []`; this was reported as a sensitivity-
analysis execution failure rather than a primary protocol deviation.

## Current selection status

Phase 3 is complete. `map_mean_6h` is retained as the parsimonious development
strategy. The logistic candidate remains a documented non-advancing development
candidate. No confirmatory evaluation report exists, and neither strategy is
clinically validated.
