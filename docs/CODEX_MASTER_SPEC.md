You are acting as a senior clinical machine-learning engineer, research software
engineer, MLOps engineer, and scientific-methodology reviewer.

Your task is to audit, repair, extend, test, and document the existing DeepVital
repository. Do not replace the project blindly. First inspect every existing file,
understand what already works, identify defects and methodological weaknesses, and
then improve it incrementally.

PROJECT PURPOSE
===============

DeepVital is a research-only clinical AI platform for:

"Explainable early prediction of sustained hypotension in ICU patients using
multivariate vital-sign time series."

The main scientific question is:

Can the previous 12 hours of routinely collected ICU vital signs predict sustained
hypotension during the following 6 hours?

Primary outcome:
- Mean arterial pressure (MAP) < 65 mmHg
- for at least two consecutive hourly observations
- within the next six hours

This application is being developed as:
1. A reproducible research portfolio.
2. A potential doctoral-project prototype.
3. Evidence of interdisciplinary competence in medicine, ICT, clinical data science,
   machine learning, software engineering, and health technology.
4. A project methodologically aligned with research interests at the University of
   Oulu.

It is NOT a medical device and must never be presented as ready for clinical use.

SCIENTIFIC ALIGNMENT
====================

Translate the following research principles into actual software features.

1. PHYSIOLOGICAL SIGNAL ANALYSIS AND SENSOR FUSION
   Inspired by work associated with Tapio Seppänen:
   - Combine multiple physiological signals.
   - Preserve clinically meaningful signal structure.
   - Avoid overly aggressive normalization or imputation.
   - Compare methods rather than presenting one neural network in isolation.
   - Distinguish controlled retrospective performance from real-world performance.
   - Explicitly assess generalization, robustness, reproducibility, missing data,
     temporal context, and sensor variability.

2. EXPLAINABLE CONCEPT-DRIFT MONITORING
   Inspired by Pekka Siirtola's feature-relevance work:
   - Detect changes in input distributions.
   - Detect changes in missingness and charting frequency.
   - Compare current feature relevance with a trusted reference model.
   - Attempt to explain likely causes of drift using predefined drift signatures.
   - Require human review; never retrain automatically.
   - Clearly state that feature relevance is model-dependent and is not causal.

3. HEALTH-TECHNOLOGY EVALUATION BY MATURITY
   Inspired by work associated with Miia Jansson:
   - Organize the project according to Technology Readiness Levels.
   - TRL 5: retrospective model validation.
   - TRL 6: silent or real-time model testing.
   - TRL 7: workflow implementation.
   - TRL 8: clinical-outcome evaluation.
   - TRL 9: model integration.
   - Current project target: a strong retrospective research prototype around TRL 5,
     not clinical deployment.
   - Include discrimination, calibration, transparent confidence, reliability,
     safety, usability, implementation considerations, and clinical utility planning.

NON-NEGOTIABLE CLINICAL AND METHODOLOGICAL RULES
================================================

1. Use ICU-stay identifiers:
   - subject_id
   - hadm_id
   - stay_id
   - timestamp

2. Never allow a time window to cross:
   - ICU stays
   - hospital admissions
   - patients

3. Split train, validation, and test data by patient, not by individual windows.

4. Do not use backward filling (`bfill`) anywhere.

5. Forward filling may be used only with an explicit configurable maximum duration,
   default two hours.

6. Compute every imputation statistic, scaler, feature-selection decision,
   calibration model, threshold, and hyperparameter using training or validation data
   only. Never fit anything on the test set.

7. Labels must use future data only. Predictors must use current and historical data
   only.

8. Do not use future interventions, future laboratory values, future diagnoses, or
   future charting information as predictors.

9. Add missingness indicators and time-since-last-observation features.

10. Retain original values before normalization so that preprocessing can be audited.

11. Validate and harmonize units, especially temperature and oxygen variables.

12. Use physiological plausibility ranges, but log every value removed or converted.

13. Do not upload or commit MIMIC-IV patient-level data.

14. Generate synthetic demo data for the public application and tests.

15. All public predictions must display:
   "Research demonstration only — not for clinical decision-making."

INITIAL VARIABLES
=================

Use these initial physiological variables:

- heart_rate
- respiratory_rate
- systolic_bp
- diastolic_bp
- mean_arterial_pressure
- oxygen_saturation
- temperature
- oxygen_flow or supplemental_oxygen_indicator

Support known MIMIC-IV item IDs through a configurable mapping file.

Do not assume that oxygen flow is equivalent to FiO2 or to the NEWS2 oxygen variable.
Document this limitation.

REQUIRED SOFTWARE ARCHITECTURE
==============================

Maintain a clean Python package with approximately this structure:

deepvital/
├── configs/
│   ├── sensors.yaml
│   ├── cohort.yaml
│   ├── modeling.yaml
│   └── drift.yaml
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── synthetic/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── RESEARCH_PROTOCOL.md
│   ├── COHORT_DEFINITION.md
│   ├── DATA_DICTIONARY.md
│   ├── DATA_GOVERNANCE.md
│   ├── MODEL_CARD.md
│   ├── TRL_EVALUATION_PLAN.md
│   ├── OULU_ALIGNMENT.md
│   ├── LIMITATIONS.md
│   └── REPRODUCIBILITY.md
├── models/
├── notebooks/
├── reports/
│   ├── figures/
│   ├── tables/
│   └── metrics/
├── scripts/
├── src/deepvital/
│   ├── data/
│   ├── features/
│   ├── labeling/
│   ├── models/
│   ├── evaluation/
│   ├── explainability/
│   ├── drift/
│   ├── api/
│   └── dashboard/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── README.md

Adapt this structure to the existing repository instead of creating needless duplicate
modules.

DATA INGESTION
==============

Implement two interchangeable data sources:

1. CSV or Parquet input for development and testing.
2. PostgreSQL input for the authorized local MIMIC-IV environment.

Use environment variables for database credentials.

Create a cohort-building command that:
- reads the selected MIMIC-IV measurements;
- groups by subject_id, hadm_id, and stay_id;
- standardizes timestamps to UTC;
- aggregates duplicate measurements hourly using the median;
- validates units;
- creates an auditable data-quality report;
- outputs a processed Parquet dataset;
- never writes credentials or protected data into logs.

Create a cohort-flow report containing:
- initial ICU stays;
- exclusions;
- stays with insufficient observation history;
- stays with insufficient future follow-up;
- final number of patients;
- final number of stays;
- number of windows;
- positive-event prevalence.

LABELING
========

Implement a thoroughly tested sustained-hypotension label.

At prediction time t:
- use the interval t+1 through t+6 hours;
- label positive when MAP is below 65 mmHg for at least two consecutive hourly
  observations;
- require a complete future observation horizon for the primary analysis;
- permit alternative definitions only through configuration;
- generate sensitivity analyses for:
  a. one low-MAP observation,
  b. two consecutive observations,
  c. three consecutive observations,
  d. MAP thresholds of 60, 65, and 70 mmHg.

Unit tests must prove that:
- current MAP is not part of the future label;
- future measurements never enter input features;
- incomplete future horizons are handled explicitly;
- windows never cross an ICU stay.

FEATURE ENGINEERING
===================

For every physiological variable create:

- observed value;
- missingness mask;
- hours since last real measurement;
- rolling mean;
- rolling minimum;
- rolling maximum;
- rolling standard deviation;
- short-term slope;
- difference from the patient's preceding baseline.

Use only backward-looking windows.

Create optional clinically interpretable derived features:
- pulse pressure;
- shock index;
- MAP trend;
- heart-rate trend;
- oxygen-saturation trend.

Do not use a derived feature when its source variables are missing without recording
that missingness.

MODELS
======

Implement and compare the following models:

0. Clinical/simple reference models:
   - last observed MAP;
   - linear MAP trend;
   - configurable clinical threshold rule.

1. Logistic regression with class weighting.

2. Gaussian Naive Bayes or another simple probabilistic Bayesian baseline suitable for
   sensor fusion and incomplete information.

3. Histogram Gradient Boosting using scikit-learn.
   Do not require XGBoost unless it is made optional.

4. LSTM or GRU model in PyTorch.

Do not claim that deep learning is superior. The purpose is to test whether temporal
deep learning provides meaningful improvement over simpler models.

Use reproducible seeds and configuration files.

Handle class imbalance using training data only. Report event prevalence and do not
use accuracy as the principal metric.

EVALUATION
==========

For validation and untouched test sets calculate:

- AUROC;
- AUPRC;
- Brier score;
- calibration intercept and slope when feasible;
- expected calibration error;
- calibration plot;
- sensitivity;
- specificity;
- positive predictive value;
- negative predictive value;
- F1 score;
- confusion matrix;
- alert rate per 100 patient-hours;
- event prevalence;
- lead time before the event;
- decision-curve analysis when feasible.

Select thresholds using validation data only.

Provide:
- threshold optimized for Youden index;
- threshold targeting high sensitivity;
- threshold targeting a configurable alert rate.

Calculate 95% confidence intervals using patient-level bootstrap, never window-level
bootstrap.

Add subgroup analyses when variables are available:
- sex;
- age groups;
- ICU type;
- admission type.

Clearly label subgroup analyses as exploratory.

CALIBRATION
===========

Support post-hoc calibration using validation data only:
- Platt scaling;
- isotonic regression where sample size permits.

Store the uncalibrated and calibrated results separately.

The dashboard must make calibration visible, not only AUROC.

EXPLAINABILITY
==============

Implement global and local explanations.

For conventional models:
- coefficient plots;
- permutation importance;
- optional SHAP support if installed.

For temporal neural networks:
- temporal occlusion or permutation analysis;
- feature-by-hour importance heatmap;
- ablation analysis.

For a single synthetic patient show:
- 12-hour physiological timeline;
- prediction probability;
- uncertainty/confidence information;
- top contributing variables;
- important time intervals;
- missing-data indicators;
- a non-causal explanation disclaimer.

Do not describe feature importance as causal.

CONCEPT-DRIFT MODULE
====================

Create a reference profile from the training data.

For a new evaluation batch calculate:
- Population Stability Index;
- Kolmogorov-Smirnov statistic where appropriate;
- Wasserstein distance for continuous features;
- missingness-rate changes;
- charting-frequency changes;
- prediction-probability distribution changes;
- event-prevalence changes when labels exist;
- calibration and performance degradation when labels exist;
- feature-relevance changes compared with the reference model.

Implement predefined potential drift signatures such as:
- increased missingness;
- altered measurement frequency;
- temperature unit mismatch;
- oxygen-unit mismatch;
- case-mix change;
- low-MAP distribution shift;
- heart-rate distribution shift;
- label-prevalence shift.

Return:
- detected drift;
- severity;
- affected variables;
- likely predefined cause;
- supporting statistics;
- recommended human review action.

Do not retrain automatically.

Document that:
- drift explanations are hypotheses;
- different models may produce different feature relevances;
- natural clinical variability can mimic drift.

APPLICATION
===========

Keep FastAPI as the inference and research API.

Add a Streamlit scientific dashboard unless an equivalent dashboard already exists.

Dashboard sections:

1. Project overview
   - clinical question;
   - intended use;
   - non-clinical-use warning;
   - current TRL target.

2. Cohort and data quality
   - cohort-flow diagram;
   - patient/stay/window counts;
   - missingness;
   - unit conversions;
   - physiological outliers;
   - outcome prevalence.

3. Patient timeline
   - synthetic 12-hour time series;
   - missingness display;
   - predicted risk;
   - selected decision threshold;
   - local explanation.

4. Model comparison
   - simple baseline;
   - Bayesian baseline;
   - logistic regression;
   - gradient boosting;
   - LSTM/GRU;
   - AUROC and AUPRC;
   - calibration;
   - confidence intervals.

5. Explainability
   - global importance;
   - feature-by-time heatmap;
   - model limitations.

6. Drift monitoring
   - drift indicators;
   - affected features;
   - likely causes;
   - human-review recommendation.

7. TRL and clinical-evaluation roadmap
   - TRL 5 retrospective validation;
   - requirements before TRL 6 silent testing;
   - workflow, usability, safety, and prospective-validation gaps;
   - no claims of clinical effectiveness.

The public dashboard must use synthetic data only.

API
===

Provide versioned endpoints:

GET  /health
GET  /api/v1/model-info
POST /api/v1/predict
POST /api/v1/batch-predict
POST /api/v1/drift/analyze

The prediction response must include:
- calibrated risk probability;
- risk category;
- threshold used;
- prediction horizon;
- model version;
- data-quality warnings;
- missing variables;
- explanation summary;
- intended-use warning.

Do not return false precision. Round probabilities appropriately.

REPRODUCIBILITY AND MLOPS
=========================

Add:
- deterministic random seeds;
- configuration-driven experiments;
- saved model metadata;
- Git commit hash in experiment metadata when available;
- dataset fingerprint, not patient-level data;
- model version;
- training timestamp;
- Python and package versions;
- structured logs;
- experiment result JSON;
- generated figures and tables;
- a reproducible Makefile;
- Docker and Docker Compose;
- GitHub Actions for linting and tests.

Do not add a heavy platform such as Kubernetes.

MLflow may be included only if it remains optional and does not complicate local use.

TESTING
=======

Use pytest.

Create tests for:
- future-only labeling;
- no backward filling;
- maximum forward-fill duration;
- physiological-range filtering;
- temperature unit conversion;
- no patient overlap between data splits;
- no stay crossing;
- train-only imputation/scaling;
- deterministic synthetic-data generation;
- API request validation;
- API prediction response;
- drift detection using intentionally shifted synthetic data;
- missing-data handling;
- model serialization and loading.

Add at least one end-to-end test using a very small synthetic dataset.

DOCUMENTATION
=============

Write documentation in clear academic English.

README.md must include:
- clinical question;
- scientific rationale;
- architecture diagram using Mermaid;
- quick start;
- synthetic demo;
- MIMIC-IV setup instructions without redistributing data;
- methodological safeguards;
- results section automatically populated from saved metrics;
- limitations;
- roadmap;
- explicit research-only disclaimer.

Create docs/OULU_ALIGNMENT.md with a traceability table:

Research principle | DeepVital implementation | Evidence generated | Remaining gap

Include:
- physiological signal analysis and sensor fusion;
- Bayesian baseline;
- temporal modeling;
- structure-preserving preprocessing;
- robustness and reproducibility;
- feature-relevance drift detection;
- human-AI review;
- transparent confidence;
- calibration;
- safety;
- TRL-based evaluation;
- implementation planning.

Do not state that the University of Oulu endorses DeepVital.
Do not imply collaboration with any named researcher.
Describe only methodological alignment with publicly available research.

Create docs/TRL_EVALUATION_PLAN.md describing:
- current retrospective prototype;
- criteria to complete TRL 5;
- prerequisites for silent TRL 6 testing;
- unresolved ethical, regulatory, usability, interoperability, and clinical-validation
  requirements.

Create docs/RESEARCH_PROTOCOL.md in a manuscript-ready format:
- background;
- objective;
- population;
- predictors;
- outcome;
- exclusion criteria;
- preprocessing;
- model development;
- validation;
- statistical analysis;
- missing data;
- subgroup analysis;
- sensitivity analysis;
- ethics and governance;
- limitations.

SECURITY AND DATA GOVERNANCE
============================

- Never log patient identifiers.
- Never expose PostgreSQL publicly.
- Keep secrets in environment variables.
- Provide .env.example without real credentials.
- Validate API input.
- Limit uploaded file size.
- Do not implement authentication unless needed for the local research prototype, but
  document production authentication requirements.
- Ensure public examples are synthetic.
- Add data-retention and deletion notes.
- Explain that MIMIC-IV access rules remain applicable to derived data and models when
  relevant.

IMPLEMENTATION PROCESS
======================

Work in phases.

PHASE 0 — AUDIT
1. Inspect the repository.
2. Run existing tests.
3. Identify broken imports, incomplete code, leakage risks, and duplicated logic.
4. Create AUDIT.md.
5. Present a concise implementation plan before major refactoring.

PHASE 1 — DATA AND LABEL VALIDITY
Implement identifiers, cohort building, unit handling, preprocessing, labeling, and
tests.

PHASE 2 — BASELINES AND EVALUATION
Implement simple, Bayesian, logistic, and gradient-boosting baselines with complete
evaluation and calibration.

PHASE 3 — TEMPORAL MODEL
Implement the LSTM/GRU and compare it fairly against baselines.

PHASE 4 — EXPLAINABILITY AND DRIFT
Implement local/global explanations and the human-reviewed drift module.

PHASE 5 — APPLICATION AND DOCUMENTATION
Complete FastAPI, Streamlit, Docker, CI, research documentation, and synthetic demo.

After each phase:
- run tests;
- show files changed;
- state assumptions;
- report remaining problems;
- do not claim success unless the commands actually pass.

ACCEPTANCE CRITERIA
===================

The project is acceptable only when:

1. `pytest` passes.
2. Linting passes.
3. A synthetic end-to-end run completes.
4. Models train without accessing test data during fitting or threshold selection.
5. The API serves a synthetic prediction.
6. The dashboard starts successfully.
7. Drift is detected on a deliberately shifted synthetic batch.
8. Results and calibration plots are generated.
9. Docker Compose starts the API and dashboard.
10. No protected MIMIC-IV data or credentials are committed.
11. README and research documentation accurately reflect the implemented code.
12. The software clearly states that it is not for clinical decision-making.

START NOW
=========

Begin with PHASE 0 only.

Inspect the current repository, run the available tests, and create:
- AUDIT.md
- a prioritized implementation plan
- a proposed final repository tree
- a list of blocking questions only when absolutely necessary

Do not begin a full rewrite before completing the audit.
