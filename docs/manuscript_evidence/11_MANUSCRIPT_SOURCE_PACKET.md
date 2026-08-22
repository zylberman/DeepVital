# DeepVital Phase 3 manuscript source packet

## Study summary

DeepVital is a retrospective internal development study using the MIMIC-IV
Clinical Database Demo on FHIR 2.1.0. The provisional manuscript question is:
does one frozen multivariable model using routine vital-sign information from the
preceding 12 hours add enough predictive discrimination over recent mean arterial
pressure alone for sustained hypotension in the next six hours to justify its
complexity?

Audited repository: `https://github.com/zylberman/DeepVital`, commit `58c0ab1`,
tag `phase3-final-closure-v1`. Phase 3 was formally executed once on 2026-08-09.

## Design and population

All 100 demo patients were development data. Canonical processing represented 128
hospital admissions and 140 ICU stays. Ninety-two patients generated 8,970
eligible hourly prediction windows: 1,774 positive and 7,196 negative (19.78%).
Windows overlapped and were correlated; patients were the grouping/resampling unit.

FHIR Patient, hospital Encounter, ICU Encounter, and Observation resources were
streamed from gzip NDJSON. Administrative ICU Encounter periods bounded the grid.
Within-hour duplicates were summarized by median. Original values/units were
preserved; units and physiological ranges were configuration-controlled. No
backward filling was allowed; forward fill was bounded to two hours.

## Prediction task

At each hourly time `t`, predictors used `t-11` through `t`. The binary outcome used
only observed MAP in `t+1` through `t+6` and required MAP strictly below 65 mmHg
for at least two consecutive hours. All six future MAP hours had to be observed.
MAP at `t` and forward-filled future MAP were not outcome evidence.

## Phase 3 strategies

Comparator: `map_mean_6h`, the raw six-hour MAP mean converted to a monotonic
bounded ranking score; it was not a calibrated probability.

Candidate: L2 logistic regression with 18 locked predictors: six-hour MAP mean;
current MAP, HR, SBP, RR and SpO2; MAP slope; shock index; five trailing missing
fractions; and five current-hour missingness indicators. Continuous inputs used
training-fold median imputation and standardization. Model settings were balanced
class weights, `lbfgs`, 1,000 maximum iterations, and `C` selected from {0.1,1.0}
inside inner folds.

## Validation and analysis

Five outer and three inner folds were fixed by a private deterministic manifest,
grouped by patient with seed 20260726. There was zero patient overlap and each
window received exactly one outer OOF prediction. Candidate/threshold selection,
preprocessing, and Platt calibration were confined to their permitted training/
inner scopes.

The primary estimand was OOF AUPRC(candidate) minus AUPRC(`map_mean_6h`). Paired
95% percentile intervals used 1,000 patient-cluster bootstrap replicates. Candidate
advancement required delta AUPRC ≥+0.020, CI lower bound >0, valid OOF accounting,
and no primary-impacting deviation. The margin was a preregistered development
relevance rule, not a p-value or validated clinical minimal difference.

## Primary results

| Strategy | AUROC | AUPRC | Brier | Log loss |
|---|---:|---:|---:|---:|
| `map_mean_6h` | 0.8416282800 | 0.6218694691 | NA | NA |
| Raw logistic candidate | 0.8447827084 | 0.6293981556 | 0.1626265672 | 0.4870888505 |

Delta AUPRC was +0.0075286864 (95% CI +0.0004996287 to +0.0171297719).
The CI lower bound was positive, but the observed delta did not reach +0.020.
Therefore, logistic regression did not advance and `map_mean_6h` was retained as
the parsimonious development strategy. This is not evidence of no incremental
signal, clinical superiority, external validity, or clinical utility.

The calibrated logistic output had AUROC 0.8434693457, AUPRC 0.6255061186, Brier
0.1114882686, and log loss 0.3619400064. These and recorded operating points are
development summaries only.

## Robustness and sensitivities

Patient-equal delta AUPRC was +0.0156094374. Invasive-preferred delta was
+0.0066575655 (CI -0.0024251482 to +0.0179764767); non-invasive-only was
-0.0004748683 (CI -0.0110530349 to +0.0135345370; 84 patients, 5,180 windows).
All nine prespecified MAP-threshold/duration grid results are retained in
`03_RESULTS_EXTRACTION.md`.

The `missing_as_low` and `missing_as_not_low` analyses failed because their inputs
contained patients absent from the frozen private fold manifest. This was
disclosed; Phase 3 was not rerun, and future investigation cannot replace the
original result. The primary protocol-deviation array was empty.

## Historical boundary

An earlier observation-bounded `development_holdout_v1` contained 1,551 evaluation
windows and was accessed four times during methodological/reporting corrections.
It is historical development evidence, not an untouched or confirmatory test.
No confirmatory or external cohort has been evaluated.

## Limitations

The demo source is small and nonrepresentative; 92 patients, rather than 8,970
windows, frame the effective independent sample. Complete future observation may
select intensely monitored periods. The outcome is a retrospective MAP pattern,
not an adjudicated clinical event. BP source pooling is provisional. Missingness
may reflect care processes. The comparator is ranking-only. Transportability,
clinical utility, prospective performance, and impact are unknown.

## Reproducibility and provenance

- Protocol commit/hash: `1586563` / `sha256:c0b2e69e...a27eb5`.
- Preregistered implementation: `54414fa`; tag `phase3-preregistered-v1`.
- Registration JSON hash: `03bf1ce0...a7c1`.
- Original result: `c7db731`; line-ending normalization: `d3c6915`.
- Result tag: `phase3-development-results-v1`; closure tag: `phase3-final-closure-v1`.
- Cohort fingerprint: `sha256:b091325f...d862ef5e`.
- Fold fingerprint: `sha256:fff63cd0...d2cc9b99`.

At audit, Python 3.12.9, Ruff 0.16.0, and pytest 9.1.1 produced 101 passing tests
with 53 dependency warnings. Runtime dependencies are not fully pinned. Exact
clinical reproduction requires authorized inputs and the private fold manifest.

## Proposed outputs

Main tables: cohort flow, locked predictors, pooled performance, paired comparisons.
Supplement: fold accounting, hyperparameters, sensitivity grid, deviations,
variable dictionary, bootstrap results, TRIPOD+AI mapping. Figures: cohort flow,
temporal task, nested-CV schematic, and aggregate forest/sensitivity plots. Public
aggregate artifacts cannot reproduce point-level OOF ROC/PR/calibration curves.

## Declarations and gaps

Ethics/exemption, official data-use wording, authors, affiliations, ORCIDs, CRediT,
funding, conflicts, acknowledgements, AI disclosure, code license, dataset license,
and primary citations remain author responsibilities. No DOI/Zenodo record exists.
See `08_DECLARATIONS_AND_ETHICS.md` and `10_MISSING_INFORMATION_QUESTIONS.md`.

## Evidence navigation

- Methods: `02_STUDY_METHODS_EXTRACTION.md`
- Results: `03_RESULTS_EXTRACTION.md`
- Claim ledger: `04_EVIDENCE_LEDGER.csv` and `05_EVIDENCE_LEDGER.json`
- Reporting/bias gaps: `06_TRIPOD_PROBAST_GAP_AUDIT.md`
- Tables/figures: `07_TABLES_AND_FIGURES_PLAN.md`
- Discussion: `09_DISCUSSION_INPUTS.md`
- Audit commands: `12_AUDIT_COMMAND_LOG.md`
