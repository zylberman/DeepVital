# Results extraction

## Cohort

The canonical cohort contained 8,970 windows from 92 eligible patients, including
1,774 positive and 7,196 negative windows; prevalence was
0.19777034559643256. Source-level counts were 100 patients, 128 admissions, and
140 ICU stays. Windows were correlated and overlapping.

Outer-fold validation-window counts were 1,794, 1,793, 1,795, 1,795, and 1,793.
Outer validation patients were 18, 18, 19, 19, and 18. Patient overlap was zero in
every fold. Patient-level outcome-event counts are not reported.

## Earlier broad internal nested-CV comparison

This comparison informed Phase 3 but was not the final strategy decision.

| Strategy | AUROC (95% CI) | AUPRC (95% CI) | Brier | Log loss | Sens. | Spec. | PPV | NPV |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Constant prevalence | 0.4565 (0.3825–0.5364) | 0.1826 (0.1334–0.2533) | 0.1590 | 0.4985 | 0.0000 | 1.0000 | NA | 0.8022 |
| Last MAP | 0.8216 (0.7856–0.8559) | 0.5613 (0.4464–0.6538) | NA | NA | 0.7176 | 0.7775 | 0.4429 | 0.9178 |
| `map_mean_6h` | 0.8416 (0.7984–0.8809) | 0.6219 (0.4914–0.7210) | NA | NA | 0.7266 | 0.8042 | 0.4778 | 0.9227 |
| MAP minimum 6h | 0.8221 (0.7761–0.8637) | 0.5196 (0.3941–0.6250) | NA | NA | 0.7497 | 0.7460 | 0.4212 | 0.9236 |
| MAP slope | 0.6174 (0.5933–0.6413) | 0.2564 (0.1978–0.3189) | NA | NA | 0.6742 | 0.5097 | 0.2532 | 0.8639 |
| Shock index | 0.6390 (0.5774–0.6944) | 0.2987 (0.2068–0.3847) | NA | NA | 0.6392 | 0.5104 | 0.2435 | 0.8516 |
| Modified shock index | 0.7098 (0.6582–0.7594) | 0.3965 (0.2756–0.5007) | NA | NA | 0.6928 | 0.5844 | 0.2912 | 0.8853 |
| Nested ML strategy | 0.8185 (0.7747–0.8633) | 0.5333 (0.4226–0.6423) | 0.1354 | 0.4228 | 0.7317 | 0.7775 | 0.4477 | 0.9216 |

Gaussian Naive Bayes, Histogram Gradient Boosting, and logistic regression were
candidate families inside the broad nested strategy; the public pooled report
provides the selected strategy's metrics rather than a separate pooled result for
each family. `map_mean_6h` minus nested ML delta AUPRC was 0.08856201884708681
(95% CI 0.020545018382017298–0.14527050623091592).

## Formal Phase 3 performance

| Output | AUROC | AUPRC | Brier | Log loss |
|---|---:|---:|---:|---:|
| `map_mean_6h` ranking score | 0.8416282799601181 | 0.621869469148825 | NA | NA |
| Raw logistic candidate | 0.8447827084193712 | 0.6293981555920831 | 0.162626567181836 | 0.48708885047841977 |
| Cross-fitted calibrated logistic | 0.8434693456780762 | 0.6255061185881545 | 0.11148826857622389 | 0.3619400063517131 |

Raw candidate fold-specific inner-threshold metrics: sensitivity
0.7609921082299888, specificity 0.7759866592551418, PPV 0.45577312626603644,
NPV 0.929427430093209, F1 0.5701013513513514. Comparator metrics were sensitivity
0.7254791431792559, specificity 0.8046136742634797, PPV 0.4779056813962124,
NPV 0.9224151664808029, F1 0.5762256548018805. The aggregate `threshold` is null
because fold-specific inner-CV thresholds were used.

Calibrated-candidate intercept was -0.00029701117676997503 and slope
1.0001232933333872. Descriptive final development operating points were fixed 0.5,
target-sensitivity 0.32082130082460697, and Youden 0.37754066879814546. They are
not clinically validated thresholds.

## Primary paired comparison and decision

- Delta AUPRC (logistic minus `map_mean_6h`): 0.0075286864432581035.
- Patient-bootstrap 95% CI: 0.0004996287013002788 to 0.01712977187518211.
- Valid replicates: 1,000; proportion above zero: 0.987.
- Delta AUROC: 0.003154428459253067 (95% CI -0.0002853697654447759 to 0.006642685314395779).
- Preregistered development relevance margin: 0.020.
- Decision: primary advancement failed because 0.00753 <0.020. The positive CI
  lower bound passed its separate criterion. `map_mean_6h` was retained.

No relative difference was reported; calculating one post hoc is unnecessary.

## Sensitivity analyses

| Definition | Delta AUPRC | 95% CI | Patients/windows | Status |
|---|---:|---|---|---|
| MAP<60, 1 hour | 0.0024470062 | -0.0108903605–0.0195402172 | 92/8,970 | completed |
| MAP<60, 2 hours | 0.0027222423 | -0.0112060524–0.0166743578 | 92/8,970 | completed |
| MAP<60, 3 hours | 0.0199924643 | -0.0043902896–0.0537570102 | 92/8,970 | completed |
| MAP<65, 1 hour | 0.0062732192 | -0.0025083634–0.0156221414 | 92/8,970 | completed |
| MAP<65, 2 hours | 0.0075286864 | 0.0004996287–0.0171297719 | 92/8,970 | primary |
| MAP<65, 3 hours | 0.0139717236 | -0.0007860766–0.0272318154 | 92/8,970 | completed |
| MAP<70, 1 hour | 0.0034531672 | 0.0000085259–0.0079957811 | 92/8,970 | completed |
| MAP<70, 2 hours | 0.0053589107 | -0.0015667909–0.0138458753 | 92/8,970 | completed |
| MAP<70, 3 hours | 0.0010087804 | -0.0100544477–0.0113677384 | 92/8,970 | completed |
| Invasive-preferred BP | 0.0066575655 | -0.0024251482–0.0179764767 | 92/8,970 | completed |
| Non-invasive-only BP | -0.0004748683 | -0.0110530349–0.0135345370 | 84/5,180 | completed |

Patient-equal delta AUPRC was 0.015609437384234592. Neutral-score and complete-case
benchmark analyses were identical because `map_mean_6h` was available for all
primary windows.

`missing_as_low` and `missing_as_not_low` both failed with `ValueError: Dataset
contains patients absent from private fold manifest`. They were not replaced and
the formal analysis was not rerun.

## Deviations and historical holdout

The formal primary deviation array is empty. The sensitivity execution failures
were disclosed separately. The legacy observation-bounded holdout had 1,551
windows, was accessed four times, and is now `development_holdout_v1`; it is not
confirmatory evidence. Its exact four-run chronology cannot be reconstructed.
