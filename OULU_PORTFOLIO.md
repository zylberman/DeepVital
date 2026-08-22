# DeepVital: Research Portfolio for the University of Oulu

## Project overview

DeepVital is a reproducible methodological research pipeline for the early
prediction of sustained hypotension from longitudinal intensive-care vital
signs represented through FHIR-compatible clinical resources.

The project demonstrates clinical problem formulation, temporal data
processing, patient-grouped evaluation and reproducible Python research
software. It is intended for methodological research and software
demonstration. It is not a clinically validated decision-support system or a
medical device.

## Clinical problem

At each hourly prediction time, DeepVital uses information from the preceding
12 hours to estimate whether sustained hypotension will occur during the
following six hours.

The primary outcome is defined as an observed mean arterial pressure below
65 mmHg for at least two consecutive future hours. Measurements at the
prediction time are used only as predictors; future measurements are reserved
exclusively for outcome construction.

## Data source and structure

The source is the MIMIC-IV Clinical Database Demo on FHIR 2.1.0. DeepVital
processes FHIR-compatible Patient, Encounter and Observation resources and
reconstructs relationships between patients, hospital admissions, ICU stays
and physiological observations.

The public repository does not distribute MIMIC-IV patient-level data.

The canonical cohort contains:

* 100 source patients.
* 128 represented hospital admissions.
* 140 ICU stays.
* 92 patients contributing to the formal evaluation.
* 8,970 eligible prediction windows.
* 1,774 positive windows.
* Eight physiological variables.
* Eighteen prespecified predictors in the frozen Phase 3 logistic candidate.

The physiological variables are heart rate, respiratory rate, systolic blood
pressure, diastolic blood pressure, mean arterial pressure, peripheral oxygen
saturation, temperature and oxygen flow.

## Temporal processing

Every hourly grid and prediction window is constructed within a single patient,
hospital admission and ICU stay.

DeepVital implements:

* Median aggregation of multiple measurements within the same variable-hour.
* Twelve-hour retrospective observation windows.
* A six-hour future prediction horizon.
* No backward filling or future-dependent interpolation.
* Forward filling limited to two hours.
* Explicit missingness and time-since-last-observation variables.
* Exclusion of windows without complete future MAP ascertainment for the
  primary analysis.

## Evaluation design

The formal internal development evaluation used patient-grouped nested
cross-validation:

* Five outer folds for performance estimation.
* Three inner folds for model development.
* Zero patient overlap between training and evaluation folds.
* All windows from the same patient retained in the same fold.
* One outer out-of-fold prediction for each eligible window.
* Preprocessing fitted only within the corresponding training data.
* Candidate and threshold selection restricted to inner-fold information.
* Uncertainty estimated using 1,000 patient-clustered bootstrap replicates.

Patients, rather than individual windows, were resampled during bootstrap
estimation.

## Phase 3 results

| Strategy                                  |  AUROC |  AUPRC |
| ----------------------------------------- | -----: | -----: |
| Six-hour mean MAP comparator              | 0.8416 | 0.6219 |
| Frozen 18-predictor L2 logistic candidate | 0.8448 | 0.6294 |

The logistic candidate achieved an AUPRC difference of `+0.00753` relative to
the six-hour mean MAP comparator. The paired patient-bootstrap 95% interval was
`+0.00050` to `+0.01713`.

The positive difference did not reach the prespecified `+0.020` development
relevance margin. Therefore, the logistic candidate did not advance, and the
six-hour mean MAP comparator was retained as the parsimonious development
strategy.

This result is reported without claiming clinically meaningful superiority.

## Leakage prevention

DeepVital reduces temporal and patient-level leakage through:

* Patient-grouped data partitions.
* ICU-stay-bounded grids and windows.
* Separation of retrospective predictors from future outcome measurements.
* Fold-local preprocessing and imputation.
* Inner-fold model and threshold selection.
* No patient overlap between development and evaluation folds.
* Automated tests for patient separation and temporal boundaries.

## Reproducibility

The repository includes:

* Modular Python source code.
* Version-controlled configurations.
* Documented data lineage and cohort construction.
* A research protocol and evaluation documentation.
* Aggregate reports without patient-level prediction rows.
* 101 automated tests.
* Ruff code-quality checks.
* GitHub Actions continuous integration.
* A public end-to-end synthetic demonstration.
* Clean-environment verification at commit
  `3e1ffa4b88039a13f62d0f133c18ee4fc4998f7d`.

The clean verification produced 101 passing tests and successfully executed the
documented synthetic demonstration using fully artificial data.

## Limitations

* Only 92 patients contributed to the formal evaluation.
* Multiple overlapping windows originate from the same patients.
* The analysis uses a single demonstration clinical data source.
* The evidence is internal development evidence.
* External, prospective and confirmatory validation have not been performed.
* Complete future MAP ascertainment may introduce selection bias.
* Missingness may reflect clinical and operational processes.
* Blood-pressure measurement sources are currently pooled without a clinically
  validated source-priority rule.
* The system has not been evaluated for clinical workflow integration, patient
  benefit or deployment.
* DeepVital uses tabulated hourly vital signs rather than raw physiological
  waveforms.

## Skills transferable to physiological sensing research

DeepVital demonstrates experience in:

* Formulating clinically meaningful prediction problems.
* Processing FHIR-compatible healthcare data.
* Constructing physiological time series.
* Temporal alignment, aggregation and windowing.
* Managing missing observations.
* Preventing patient-level and temporal leakage.
* Designing patient-grouped evaluation.
* Statistical performance estimation and clustered uncertainty analysis.
* Building tested and documented Python research software.
* Reporting results without overstating clinical significance.

These skills are transferable to ECG, PPG and multimodal physiological sensing
research. However, DeepVital itself does not demonstrate raw-waveform filtering,
beat detection, camera-based physiological measurement or multisensor
synchronisation.

## Author

Byron Mena Acosta
Independent Researcher, Ecuador
ORCID: https://orcid.org/0009-0005-8809-202X
