# Executive evidence status

## Audit scope and verdict

This packet audits DeepVital Phase 3 at Git commit
`58c0ab118329bf5a30f6591a6163faf2f89ae007` (`main`, tag
`phase3-final-closure-v1`). The repository supports drafting an original
development-study manuscript, but not a claim of external, confirmatory,
prospective, or clinical validation.

**Manuscript readiness:** ready for structured drafting after author-supplied
ethics, authorship, affiliation, funding, conflict-of-interest, licensing, and
data-access statements are completed. These omissions block a public preprint
submission package, not interpretation of the frozen Phase 3 analysis.

## Ten confirmed facts

1. The data source is the MIMIC-IV Clinical Database Demo on FHIR 2.1.0.
2. The canonical source represents 100 patients, 128 admissions, and 140 ICU stays.
3. Ninety-two patients contributed 8,970 eligible, overlapping prediction windows.
4. There were 1,774 positive windows and 7,196 negative windows (19.777%).
5. Predictors covered `t-11` through `t`; the outcome covered `t+1` through `t+6`.
6. The primary outcome was observed hourly MAP <65 mmHg for at least two consecutive future hours, requiring all six future MAP hours.
7. Phase 3 used deterministic 5-outer/3-inner patient-grouped cross-validation and one outer OOF prediction per window, with zero patient overlap.
8. The frozen candidate was L2 logistic regression with 18 predictors; the comparator was `map_mean_6h`.
9. Candidate-minus-comparator delta AUPRC was 0.0075286864432581035 (paired patient-bootstrap 95% CI 0.0004996287013002788 to 0.01712977187518211).
10. The delta did not reach the preregistered +0.020 development relevance margin; the candidate did not advance and `map_mean_6h` was retained for parsimony.

## Principal limitations

- This is a 100-patient demo source and an internal development analysis.
- The effective independent unit is the patient; 8,970 correlated windows are not 8,970 independent observations.
- Complete future-MAP ascertainment may select intensively monitored periods.
- Primary BP sources were pooled by hourly median; source-specific sensitivities do not establish a clinically validated precedence rule.
- `missing_as_low` and `missing_as_not_low` failed because their generated datasets included patients absent from the frozen manifest; Phase 3 was not rerun.
- Runtime requirements are mostly unpinned; exact clinical reproduction requires restricted inputs and the private fold manifest.
- No external or confirmatory cohort exists.

## Blocking information

### Before preprint

- Author list, affiliations, corresponding author, ORCIDs, contributions, funding, conflicts, acknowledgements, and generative-AI disclosure.
- Venue-appropriate ethics/exemption and PhysioNet/MIMIC data-use wording.
- A project code license and verified code/data availability statements.
- Primary bibliographic citations for MIMIC-IV, MIMIC-IV FHIR, TRIPOD+AI, PROBAST+AI, and the clinical MAP threshold.

### Before journal submission

- Completed TRIPOD+AI checklist against the selected journal format.
- Formal PROBAST+AI assessment by qualified reviewers independent of code authorship where feasible.
- Locked software environment or archived environment metadata sufficient for exact computational reproduction.
- Journal-specific reporting of sample-size rationale and correlated-window implications.

## Recommended next step

Resolve the author-only questions in `10_MISSING_INFORMATION_QUESTIONS.md`, then
draft Methods and Results from `11_MANUSCRIPT_SOURCE_PACKET.md` without rerunning
Phase 3 or altering the frozen evidence.
