# DeepVital Phase 0 Audit

> **Historical document.** This Phase 0 audit describes the repository before the
> implemented Phase 1 and Phase 2 work. It is preserved as an audit trail and must
> not be read as the current project state. See `PROJECT_STATUS.md` and
> `RESEARCH_PROTOCOL.md`.

**Audit date:** 2026-07-26  
**Scope:** Repository state at commit `3d7a92a` plus the uncommitted project
instructions present in the working tree.  
**Status:** Phase 0 only. No clinical database was contacted, no patient-level file
was opened, and no implementation or data file was changed.

DeepVital is currently an early research scaffold, not an executable clinical
machine-learning pipeline and not a medical device. It must not be used for patient
care or described as clinically validated.

## Executive summary

The repository contains two standalone FHIR-to-PostgreSQL loaders, a demonstration
LSTM module, one database exploration notebook, Docker Compose configuration, and a
master specification. It does not yet contain the cohort, preprocessing, labeling,
splitting, training, evaluation, API, or drift implementations required by the
specification. There is no test suite, package metadata, CI configuration, README,
research protocol, or cohort definition.

The most urgent risks are:

1. Database credentials are committed in source, Compose configuration, and the
   notebook.
2. Both ETL loaders replace destination tables and therefore perform destructive
   writes.
3. The patient loader copies names and dates of birth into PostgreSQL even though
   those direct identifiers are unnecessary for the stated prediction task.
4. The vital-sign loader retains only a generic patient reference and does not
   preserve `subject_id`, `hadm_id`, and `stay_id`; safe ICU-stay windowing is
   therefore impossible.
5. No future-only sustained-hypotension label, patient-level split, bounded
   imputation, unit normalization, plausibility filtering, or leakage test exists.
6. Patient-level MIMIC-IV demo files are present locally under ignored `data/`.
   They are not tracked by Git, but their governance, provenance, access controls,
   and removal/retention policy are undocumented.

Phase 1 should not train a model. It should first establish a synthetic, tested,
stay-aware data and label pipeline.

## Repository inventory

| Component | Current state | Audit assessment |
|---|---|---|
| `etl_chartevents.py` | Parses compressed FHIR observations into memory and replaces a PostgreSQL table | Unsafe credentials and write behavior; incomplete identifiers, mappings, validation, and audit trail |
| `etl_fhir_to_sql.py` | Parses FHIR patients, including names and birth dates, then replaces a PostgreSQL table | Collects unnecessary direct identifiers; unsafe credentials and write behavior |
| `app/model.py` | Untrained two-branch PyTorch demonstration with one LSTM input channel | Forward pass is syntactically valid, but this is not a training/evaluation implementation |
| `notebooks/01_exploracion_sensores.ipynb` | Queries local PostgreSQL using a placeholder patient identifier | Embedded credentials, schema mismatch, saved output, and unsafe exploratory pattern |
| `docker-compose.yml` | Starts PostgreSQL and pgAdmin with fixed credentials and host port bindings | Insecure defaults; PostgreSQL is exposed on all host interfaces by default |
| `requirements.txt` | Unpinned runtime package names | Not reproducible; omits test/lint/notebook/plot packages used or expected |
| `docs/CODEX_MASTER_SPEC.md` | Detailed intended architecture and safeguards | Aspirational; most described components do not exist |
| `AGENTS.md`, `AGENTS.mdn` | Working-tree instructions | `AGENTS.mdn` is malformed/incomplete and duplicates instructions |
| Local `data/` | Ignored MIMIC-IV demo archive and extracted FHIR resources | Not tracked, but still patient-level material requiring local governance |
| Local virtual environments | `venv/` and `notebooks/venv/` | Large, duplicate, and not fully ignored by the current `.gitignore` |

Tracked files at audit time are `.DS_Store`, `.gitignore`, `app/model.py`,
`docker-compose.yml`, `etl_chartevents.py`, `etl_fhir_to_sql.py`,
`notebooks/01_exploracion_sensores.ipynb`, and `requirements.txt`. The master
specification and instruction files are untracked in the inspected working tree.

## Current repository structure

Generated caches, local virtual environments, Git internals, and the contents of
ignored patient-level `data/` are omitted. Their presence and governance status are
covered elsewhere in this audit.

```text
deepvital-project/
├── .gitignore
├── AGENTS.md
├── AGENTS.mdn
├── app/
│   └── model.py
├── data/                                  # ignored; local MIMIC-IV demo material
├── docker-compose.yml
├── docs/
│   ├── AUDIT.md
│   └── CODEX_MASTER_SPEC.md
├── etl_chartevents.py
├── etl_fhir_to_sql.py
├── notebooks/
│   └── 01_exploracion_sensores.ipynb
└── requirements.txt
```

## Findings

Severity labels express research validity, privacy, security, and reproducibility
risk, not clinical deployment readiness.

### Critical

#### C-01: Credentials are hard-coded and committed

- `etl_chartevents.py:7`, `etl_fhir_to_sql.py:7`, the notebook, and
  `docker-compose.yml:8-10,21-22` contain fixed usernames/passwords.
- The same predictable password protects PostgreSQL and pgAdmin.
- PostgreSQL and pgAdmin are published to host ports (`5432` and `5050`).

**Impact:** Credential disclosure and unauthorized local/network access are
possible. A database URL can also leak through exceptions or notebook output.

**Required remediation:** Rotate any credential that has been used; load secrets
from environment variables; supply only non-secret placeholders in
`.env.example`; bind development services to loopback unless a documented need
exists; remove credentials from notebook history. Secret removal from Git history
requires a separate, explicitly approved operation.

#### C-02: ETL uses destructive table replacement

- `etl_chartevents.py:55` and `etl_fhir_to_sql.py:45` call `to_sql` with
  `if_exists="replace"`.
- Engine creation occurs at import time, and there is no read-only mode,
  transaction policy, target confirmation, or environment guard.

**Impact:** Running either loader can drop and recreate an existing table, losing
schema constraints and data.

**Required remediation:** Do not run these scripts against clinical databases.
Refactor ingestion to produce a local interim artifact by default. Any database
write path must be explicit, least-privileged, non-destructive, transactional, and
tested against a disposable synthetic database.

#### C-03: Direct identifiers are unnecessarily extracted and stored

- `etl_fhir_to_sql.py:19-40` extracts patient IDs, full names, and dates of birth.
- These fields are not required for the stated vital-sign prediction objective.

**Impact:** Avoidable privacy exposure and an unnecessarily identifiable research
dataset.

**Required remediation:** Exclude names entirely. Define the minimum necessary
demographic fields, pseudonymization boundary, data retention, access controls,
and prohibited logging before processing authorized clinical data.

#### C-04: Stay-safe cohort construction is impossible with the current schema

- The vital loader records `patient_id`, timestamp, sensor code, value, and unit,
  but not `subject_id`, `hadm_id`, or `stay_id`.
- Encounter references are not resolved and ICU admission/discharge bounds are not
  enforced.

**Impact:** Windows may cross admissions or ICU stays, labels may use observations
from another episode, and patient-level splits cannot be verified.

**Required remediation:** Make the three identifiers mandatory, resolve encounters
explicitly, reject ambiguous records, and test every grouping/window boundary.

### High

#### H-01: Primary outcome and temporal boundaries are absent

There is no label implementation for MAP below 65 mmHg at two consecutive hourly
observations in `t+1` through `t+6`, no complete-horizon rule, and no 12-hour
backward-looking predictor construction.

**Risk:** Any future model implementation could include current/future MAP or other
future charting in predictors.

#### H-02: No patient-level train/validation/test split

There is no splitting code or overlap assertion. Consequently, preprocessing fit
scope, threshold selection, calibration, and untouched test evaluation are also
undefined.

**Risk:** Patient, admission, stay, and test contamination.

#### H-03: Missing-data handling is absent

There is no bounded forward fill, explicit prohibition test for backward fill,
missingness indicator, time-since-last-real-measurement feature, or train-only
imputer. The ETL silently drops records missing timestamp or value and does not
report exclusion counts.

**Risk:** Informative missingness is discarded and later ad hoc imputation could
introduce temporal leakage.

#### H-04: Sensor mapping, unit normalization, and plausibility checks are absent

The first coding entry is accepted without validating coding system, display name,
or sensor mapping. Units are stored verbatim. There is no conversion logic,
physiological range filtering, preservation of original values, or conversion/
removal audit log.

**Risk:** Fahrenheit/Celsius, oxygen-flow/FiO2, blood-pressure, and SpO2
misinterpretation can invalidate features and labels. Oxygen flow must not be
treated as FiO2 or the NEWS2 oxygen variable.

#### H-05: Local patient-level data governance is undocumented

Ignored MIMIC-IV demo material is present under `data/` (approximately 99 MB).
Git currently ignores `data/`, which reduces accidental commits, but there is no
data-governance document, pre-commit safeguard, provenance record, checksum
workflow, retention policy, or validation that notebook outputs contain no patient
rows. The tracked notebook contains a saved output object, although this audit did
not render or reproduce it.

**Risk:** Accidental disclosure through notebooks, logs, screenshots, archives, or
future Git changes.

#### H-06: No clinically meaningful evaluation pipeline

No baseline model, training code, calibration, threshold selection, metrics,
patient-level bootstrap, subgroup analysis, or saved experiment metadata exists.
The demonstration LSTM emits uncalibrated random predictions and labels values over
75% as “critical.”

**Risk:** The wording in `app/model.py:65-69` can be mistaken for clinical output
despite an untrained model and lacks the required research-only warning.

### Medium

#### M-01: ETL robustness and auditability are inadequate

- Entire compressed files are accumulated in memory.
- Empty inputs lead to a likely `KeyError` at timestamp conversion.
- JSON, timestamp, numeric, and coding errors lack record-level reason counts.
- Duplicate observations are not hourly aggregated by median.
- No input schema/version check, checksum, deterministic output, or cohort-flow
  report exists.
- Printed success counts are aggregate only; no structured, privacy-safe logs exist.

#### M-02: Model code is incomplete

- The model assumes exactly five tabular features and one sensor channel.
- Padding/masks, irregular sampling, missingness, reproducible seeds, training,
  serialization, calibration, model metadata, and inference validation are absent.
- `torch.optim` is unused.
- A sigmoid is embedded in the model, which can encourage an incorrect loss choice
  if later paired with `BCEWithLogitsLoss`.
- Hidden states are assigned but unused.

No defect was observed in the basic tensor dimensions of the demonstration forward
pass, but that does not establish scientific validity.

#### M-03: Notebook and ETL schemas disagree

The loader writes `vital_signs(timestamp, sensor_code, value, ...)`, while the
notebook queries `signos_vitales(fecha_hora, codigo_sensor, valor, ...)`. The
notebook therefore cannot consume the loader's documented output without an
unseen translation layer. It also encourages substituting a real patient ID in a
saved notebook.

#### M-04: Packaging and dependency management are incomplete

There is no `pyproject.toml`, installable package, lock/constraint file, Python
version declaration, CLI, Makefile, Dockerfile, or CI. Dependencies are unpinned.
Matplotlib is imported by the notebook but absent from `requirements.txt`.
The active repository virtual environment has runtime packages but lacks pytest and
ruff; a system pytest is available.

#### M-05: Docker configuration is not reproducible or hardened

Images are mutable tags, services have no health checks, database initialization
references a missing `db_init/`, pgAdmin is always enabled, and no application
service exists. Compose's top-level `version` field is obsolete in modern Compose.

#### M-06: Documentation contradicts implementation

The master specification describes FastAPI, a dashboard, configurable sensors,
cohort reports, four model families, evaluation, explainability, drift detection,
tests, Docker, and extensive documentation, none of which is implemented. FastAPI
is only a dependency. There is no README, `RESEARCH_PROTOCOL.md`,
`COHORT_DEFINITION.md`, architecture document, model card, limitations document, or
data-governance document.

### Low

#### L-01: Repository hygiene

`.DS_Store` is tracked. Virtual environments are not ignored by name. A checkpoint
notebook exists locally. `AGENTS.mdn` is malformed, contains an incomplete code
fence/command (`pytest -`), and duplicates `AGENTS.md`. These are maintenance
issues; Phase 0 does not delete or rewrite them.

## Leakage and contamination assessment

No implemented dataset builder or training pipeline exists, so leakage cannot be
measured empirically. The absence of code is not evidence of safety.

| Safeguard | Current evidence | Status |
|---|---|---|
| Windows grouped by subject/admission/stay | Required identifiers absent from vital table | Fails by design |
| Predictors use only times `<= t` | No window code | Not implemented |
| Labels use only `t+1` to `t+6` | No label code | Not implemented |
| Complete six-hour horizon | No label code | Not implemented |
| Patient-disjoint splits | No split code | Not implemented |
| Train-only imputer/scaler/feature selection | No preprocessing/training code | Not implemented |
| Validation-only calibration/threshold selection | No evaluation code | Not implemented |
| Untouched test set | No split/evaluation code | Not implemented |
| No backward filling | No imputation code or test | Unverified |
| Maximum two-hour forward fill | No imputation code or configuration | Not implemented |

## Methodological risks

- The absence of a stay-aware cohort and window builder permits future
  patient/admission/ICU-stay boundary violations in any ad hoc analysis.
- The primary future-only label is absent, so temporal leakage controls have not
  been established.
- Patient-level data splitting and overlap assertions are absent; train,
  validation, and test contamination cannot be ruled out.
- Missingness, bounded forward fill, training-only preprocessing, unit
  normalization, and physiological plausibility handling are absent.
- No baseline comparison, calibration, validation-only threshold selection,
  patient-level confidence interval, or untouched-test evaluation exists.
- The LSTM demonstration is untrained and uncalibrated; its random output is not
  evidence of predictive performance.

## Technical risks

- Embedded credentials, exposed service ports, import-time engine construction,
  and destructive table replacement make the current ETL unsafe to execute.
- Loader/notebook schema disagreement, missing input validation, in-memory loading,
  and missing error/audit reporting make ingestion fragile.
- There is no installable package, dependency lock, test/lint configuration, CI,
  application implementation, or reproducible experiment entry point.
- Local caches and duplicate virtual environments are not fully excluded by the
  repository hygiene rules.

## Documentation gaps

- `README.md`, `RESEARCH_PROTOCOL.md`, `COHORT_DEFINITION.md`,
  `DATA_GOVERNANCE.md`, architecture, model-card, limitations, TRL, and
  reproducibility documents are absent.
- The master specification describes components that do not exist; it must not be
  treated as implementation evidence.
- The research-only limitation is not displayed by the model demonstration or any
  public prediction surface.
- Authorized data provenance, access, retention, derived-data handling, notebook
  output policy, and incident response are undocumented.
- `AGENTS.mdn` is malformed and duplicates the authoritative `AGENTS.md`.

## Test and static-check evidence

Commands were run from the repository root without opening patient-level files or
contacting a database.

| Command | Exact result |
|---|---|
| `./venv/bin/python -m compileall -q -x '(^|/)(venv|data)/' .` | Completed with exit code 0 and no output |
| `./venv/bin/python -m pytest -q` | Failed: `No module named pytest` |
| `./venv/bin/ruff check .` | Could not start: executable absent |
| `pytest -q` | Exit code 5: `no tests ran in 0.01s` |
| `ruff check .` | Could not start: `command not found: ruff` |

The compile check establishes only that the inspected Python source parses. No test
has passed because no tests were collected. No training, ETL, Docker, database, or
notebook execution was attempted.

## Missing tests

Phase 1 requires synthetic unit tests for:

- exact future-only sustained-hypotension labeling, including current-MAP exclusion,
  consecutive-hour logic, alternative thresholds/durations, and incomplete horizon;
- no patient/admission/stay crossing;
- patient-disjoint and deterministic train/validation/test splits;
- bounded forward fill and explicit absence of backward fill;
- missingness masks and time since the last real observation;
- train-only fitting of imputers/scalers/feature selection;
- sensor-code mapping, duplicate hourly median aggregation, timezone handling,
  temperature conversions, oxygen-unit rejection, and preservation/audit of source
  values;
- physiological plausibility filtering and reason counts;
- empty, malformed, ambiguous-encounter, missing-unit, and duplicate inputs;
- deterministic synthetic generation and a small end-to-end cohort build.

Later phases require model, calibration, threshold, metric, serialization, API,
drift, and dashboard tests. Those should not be pulled into Phase 1 prematurely.

## Prioritized implementation plan

### Phase 1A — governance and safe project foundation

1. Rotate used credentials; remove hard-coded secrets from runtime files and use
   environment variables.
2. Add README research-only language, data-governance documentation, `.env.example`,
   stronger ignore rules, Python packaging, pytest/ruff configuration, and synthetic
   test fixtures.
3. Quarantine legacy destructive ETL behind an explicit guard until replaced.
4. Define typed canonical schemas and configurable sensor mappings.

### Phase 1B — data and label validity

1. Implement file-based synthetic CSV/Parquet ingestion first.
2. Require `subject_id`, `hadm_id`, `stay_id`, and UTC timestamp; aggregate duplicates
   within stay and hour using median.
3. Normalize audited units, preserve raw values, filter audited physiological
   implausibilities, and report cohort/data-quality flow.
4. Implement stay-bounded hourly grids, a configurable maximum two-hour forward
   fill, missingness masks, and time-since-observation features without backward
   filling.
5. Implement the 12-hour historical window and future-only six-hour sustained-MAP
   label.
6. Implement patient-level splits and leakage assertions.
7. Stop after the synthetic end-to-end tests, lint, and documentation pass.

### Later phases

Only after Phase 1 passes should the project add simple reference models, Bayesian
and logistic baselines, gradient boosting, temporal neural models, validation-only
calibration/thresholding, untouched-test evaluation, explainability, drift
monitoring, FastAPI/dashboard surfaces, and optional authorized read-only MIMIC
ingestion.

## Proposed target tree

This tree adapts the specification without preserving duplicate legacy scripts as
parallel production paths:

```text
deepvital-project/
├── configs/
│   ├── cohort.yaml
│   ├── modeling.yaml
│   └── sensors.yaml
├── data/
│   ├── raw/.gitkeep
│   ├── interim/.gitkeep
│   ├── processed/.gitkeep
│   └── synthetic/.gitkeep
├── docs/
│   ├── AUDIT.md
│   ├── COHORT_DEFINITION.md
│   ├── DATA_GOVERNANCE.md
│   └── RESEARCH_PROTOCOL.md
├── notebooks/
├── reports/
├── scripts/
│   ├── build_dataset.py
│   └── generate_synthetic_data.py
├── src/deepvital/
│   ├── config.py
│   ├── data/
│   │   ├── ingest.py
│   │   ├── quality.py
│   │   ├── schema.py
│   │   └── split.py
│   ├── features/
│   │   └── preprocessing.py
│   └── labeling/
│       └── hypotension.py
├── tests/
│   ├── fixtures/
│   ├── test_ingest.py
│   ├── test_labeling.py
│   ├── test_preprocessing.py
│   └── test_splitting.py
├── .env.example
├── .gitignore
├── Dockerfile
├── Makefile
├── README.md
├── docker-compose.yml
└── pyproject.toml
```

Modeling, evaluation, explainability, drift, API, and dashboard subpackages should
be added only in the phases that implement them.

## Assumptions and unresolved issues

- The path supplied by the user was interpreted as a request to create the missing
  Phase 0 audit.
- The local MIMIC-IV demo directory was treated as patient-level data. File names,
  sizes, ignore status, and repository tracking state were inspected; patient rows
  and identifiers were not opened or printed.
- The saved notebook output was not rendered. It requires a privacy review before
  the notebook can be retained or shared.
- It is unknown whether the committed credentials have been used elsewhere; assume
  compromise and rotate them.
- Git history rewriting, data deletion, credential rotation, dependency
  installation, database access, and Phase 1 implementation were outside this
  audit and were not performed.
- The repository has pre-existing uncommitted/untracked instruction and
  documentation files. They were preserved.
- The intended authorized data source and exact FHIR-to-MIMIC identifier mapping
  remain to be specified before any real-data ingestion work.

## Recommended next action

Begin Phase 1 with the governance and synthetic-data foundation only: rotate
credentials outside the repository, define canonical identifiers and sensor/unit
mappings, add synthetic fixtures, and implement/test stay-safe preprocessing and
future-only labels. Do not train a model or connect to MIMIC-IV until those tests
pass and the governance boundary is documented.
