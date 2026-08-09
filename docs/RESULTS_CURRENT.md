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

## Selection status

The versioned nested-CV report records `model_selection_status: not_final` and
`final_threshold_status: not_frozen`. No confirmatory evaluation report exists.
