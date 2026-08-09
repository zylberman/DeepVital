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
Alternative MAP thresholds, duration requirements, source-pooling rules, and
incomplete-horizon strategies remain planned sensitivity analyses.

Forward filling is limited and explicitly represented, but missingness may be
clinically and operationally informative. A neutral score of 0.5 for uncalculable
benchmarks is predeclared and transparent, yet it can affect threshold metrics.
Complete-case results provide sensitivity context rather than eliminating this
limitation.

## Statistical limitations

Patients contribute multiple overlapping windows. Patient-grouped folds and
patient-cluster bootstrap preserve patient-level clustering, but they do not make
windows independent or create additional patients. Confidence intervals may remain
unstable in this small cohort, and window-weighted metrics give greater influence
to patients contributing more windows.

Several models and benchmarks are compared. The paired bootstrap estimates
uncertainty in prespecified differences but is not a multiplicity-adjusted formal
confirmatory testing framework. Proportions of bootstrap differences above zero are
descriptive, not posterior probabilities or adjusted p-values.

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
The present nested cross-validation is internal validation. No independent
confirmatory test, external dataset, other institution, temporal validation cohort,
or prospective evaluation has been completed. Transportability cannot be inferred.

## Calibration limitations

The clinical sigmoid outputs are ranking scores rather than calibrated
probabilities; Brier score and log loss do not apply to them. The nested ML outputs
are probabilities but have not undergone post-hoc calibration. Calibration
strategy and sample-size requirements remain unresolved before freezing a model.

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
