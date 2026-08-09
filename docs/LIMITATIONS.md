# DeepVital limitations

## Data limitations

The current source is a 100-patient MIMIC-IV-on-FHIR demonstration dataset. Only
92 patients contribute eligible windows. This sample is not intended to represent
the diversity, scale, devices, charting practices, or case mix of routine ICU care.
Future restricted datasets may require credentialing, data-use agreements, ethics
review, and local governance that are not established by this repository.

The configured code and unit mappings are locally audited but are not definitive
clinical ontology validation. Invasive, non-invasive, and alternate arterial-
pressure sources are pooled within hourly medians without an established source-
priority rule. Oxygen flow does not represent FiO2.

## Methodological limitations

Complete observation of all six future MAP hours is required for the primary
outcome. This rule may preferentially retain more intensively monitored periods.
Phase 3 evaluated prespecified MAP thresholds, duration requirements, and two BP-
source alternatives. However, the `missing_as_low` and `missing_as_not_low`
incomplete-future-MAP sensitivities failed because their datasets contained patients
absent from the frozen fold manifest. The formal run was not repeated to repair
them. Any later investigation is post-Phase-3 supplementary technical work and
cannot replace the original preregistered result.

Forward filling is limited and explicitly represented, but missingness may be
clinically and operationally informative. A neutral score of 0.5 for uncalculable
benchmarks is predeclared and transparent, yet it can affect threshold metrics.
Complete-case results provide sensitivity context rather than eliminating this
limitation.

## Statistical limitations

The 92 eligible patients contribute 8,970 multiple, overlapping windows. These are
patient-clustered repeated observations, not 8,970 independent patients.
Patient-grouped folds and patient-cluster bootstrap preserve patient-level
clustering, but they do not make windows independent or create additional patients.
Confidence intervals may remain unstable in this small cohort, and window-weighted
metrics give greater influence to patients contributing more windows.

Several models and benchmarks are compared. The paired bootstrap estimates
uncertainty in prespecified differences but is not a multiplicity-adjusted formal
confirmatory testing framework. Proportions of bootstrap differences above zero are
descriptive, not posterior probabilities or adjusted p-values.

The Phase 3 `+0.020` delta-AUPRC advancement margin was a prespecified development
relevance rule. It is not a p-value threshold and is not a clinically validated
minimal important difference. Failure to reach it supports parsimony under this
development protocol; it does not show that the logistic candidate was useless or
had no incremental signal.

## Clinical limitations

The outcome is a retrospective MAP pattern rather than an adjudicated clinical
event. It does not incorporate hypotension mechanism, treatment context, artifact
review, symptoms, organ injury, or clinician intent. Predictive association and
feature importance must not be interpreted causally.

No decision-curve analysis, alert-burden study, lead-time utility assessment,
workflow evaluation, human-factors assessment, or clinical-impact trial establishes
benefit. DeepVital must not be used for direct care.

## Validation limitations

All 100 demo patients are development data. The original holdout was accessed four
times and is historical development evidence, not an untouched confirmatory test.
The nested and Phase 3 cross-validation results are internal development evidence.
No independent
confirmatory test, external dataset, other institution, temporal validation cohort,
or prospective evaluation has been completed. Transportability cannot be inferred.

## Calibration limitations

The retained `map_mean_6h` sigmoid output is a ranking score rather than a calibrated
probability; Brier score and log loss do not apply to it. Phase 3 fitted the sole
allowed Platt development recalibration for the logistic candidate, but the
candidate did not advance. Its calibrated metrics and operating points are not
evidence of deployment calibration or clinical threshold validity.

## Reproducibility limitations

Canonical metadata provide code-state and data/configuration fingerprints, but the
private clinical dataset cannot be redistributed. Exact clinical reproduction
therefore requires authorized access and matching local inputs. Runtime
dependencies are not fully pinned. Twelve current deprecation warnings originate
inside Joblib under the installed NumPy version; tests pass and no functional
failure is observed, but compatibility should be monitored during dependency
locking or upgrades.

The project has no project-level software license. Historical documents describe
earlier states and require status labels and the documentation index to avoid being
misread as current evidence.

## Deployment limitations

The repository does not establish a validated inference service, monitoring
program, authenticated clinical integration, regulated quality system, cybersecurity
case, usability evidence, prospective safety case, or post-deployment governance.
No claim of production, regulatory, or medical-device readiness is supported.
