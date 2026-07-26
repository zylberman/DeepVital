DeepVital project instructions for Codex

This repository contains DeepVital, a research-only clinical machine learningproject for early prediction of sustained hypotension from ICU vital-sign timeseries.

DeepVital is not a medical device and must never be described as ready forclinical use or direct patient-care decisions.

Files to read first

Before changing code, read:

README.md

docs/CODEX_MASTER_SPEC.md, if present

docs/AUDIT.md, if present

docs/RESEARCH_PROTOCOL.md, if present

docs/COHORT_DEFINITION.md, if present

Required workflow

Work phase by phase.

Before editing:

Inspect the existing implementation.

Run the relevant tests.

Summarize the planned changes.

Reuse working code instead of rewriting the repository unnecessarily.

After editing:

Run the relevant tests.

Report the exact commands executed.

Report the exact test results.

List every file created, changed, renamed, or deleted.

State all assumptions.

State unresolved issues.

Do not claim success unless the relevant commands actually completed successfully.

Do not begin a later phase until the current phase has been implemented, tested,and documented.

Data safety

Never commit MIMIC-IV patient-level data.

Never expose patient-level rows in logs, screenshots, examples, or reports.

Never print or log patient identifiers.

Never store passwords, tokens, database URLs, or secrets in source code.

Use environment variables for credentials.

Keep .env out of version control.

Use synthetic data for public tests, examples, and demonstrations.

Do not execute destructive SQL.

Do not modify or delete source clinical data.

Do not connect to a real clinical database unless explicitly instructed.

Use read-only database access whenever possible.

Clinical and methodological safeguards

Use subject_id, hadm_id, and stay_id for real ICU data.

Never allow windows to cross patients, admissions, or ICU stays.

Split train, validation, and test sets by patient.

Do not use backward filling.

Limit forward filling with an explicit configurable maximum duration.

Record missingness indicators.

Record time since last real measurement.

Use future data only for outcome labels.

Use current and historical data only for predictors.

Prevent temporal leakage.

Fit imputers using training data only.

Fit scalers using training data only.

Fit feature selection using training data only.

Fit calibration using validation data only.

Select decision thresholds using validation data only.

Keep the test set untouched until final evaluation.

Do not report accuracy as the main metric for an imbalanced outcome.

Report event prevalence, AUROC, AUPRC, Brier score, calibration, sensitivity,specificity, positive predictive value, and negative predictive value.

Do not describe feature importance as causal.

Do not retrain automatically after detecting drift.

Require human review for drift alerts and model updates.

Outcome definition

The primary DeepVital outcome is sustained hypotension in the next 6 hours:

mean arterial pressure below 65 mmHg;

for at least 2 consecutive hourly observations;

using only observations after the prediction time.

The previous 12 hours are used as the default input window.

Any alternative label definition must be configurable and documented.

Software quality

Prefer clear, typed, modular Python.

Add docstrings where they improve understanding.

Add unit tests for clinically important logic.

Keep configuration outside hard-coded model logic when practical.

Preserve backward compatibility unless a documented defect requires a change.

Avoid unnecessary dependencies.

Do not add Kubernetes or other heavy infrastructure.

Keep Docker deployment simple and reproducible.

Keep public examples synthetic.

Verification commands

Run the commands supported by the repository. Prefer:

pytest -q
ruff check .

When applicable, also run:

python scripts/generate_synthetic_data.py
python scripts/build_dataset.py
python scripts/train_baseline.py

Do not say that tests pass unless the command output confirms it.

Phase 0: audit rules

During Phase 0:

Inspect the complete repository.

Run existing tests.

Identify broken imports and incomplete code.

Identify temporal leakage risks.

Identify patient, admission, and ICU-stay leakage risks.

Identify incorrect missing-data handling.

Identify train, validation, and test contamination.

Identify unit-conversion risks.

Identify missing tests.

Identify documentation inconsistencies.

Identify security and data-governance risks.

Create docs/AUDIT.md.

Do not connect to PostgreSQL or MIMIC-IV.

Do not perform a large refactor.

Do not begin Phase 1.

Do not delete existing files.

Phase 1: data and label validity rules

During Phase 1:

Add support for subject_id, hadm_id, and stay_id.

Prevent windows from crossing ICU stays.

Add configurable sensor mappings.

Add unit normalization and audit logging.

Add physiological plausibility filtering.

Add limited forward filling without backward filling.

Add missingness indicators.

Add time-since-last-measurement features.

Add future-only sustained-hypotension labels.

Add patient-level splitting.

Add cohort-flow reporting.

Add synthetic fixtures and tests.

Do not connect to the real MIMIC-IV database unless explicitly approved.

Stop after Phase 1.

Communication style

Be concise, explicit, and technically honest.

When uncertain:

state the uncertainty;

explain the assumption;

avoid inventing results;

ask only blocking questions.

Always distinguish among:

code that has been written;

code that has been tested;

code that has passed;

code that still requires validation.
