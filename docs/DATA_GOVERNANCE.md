# DeepVital research data governance

## Scope and status

This document records project-level safeguards supported by the repository. It does
not claim to be an institutional policy, ethics approval, data-use agreement, or
legal determination. Requirements of MIMIC-IV and any future restricted dataset
remain controlling.

## Data classification and storage

- `data/raw/` is reserved for source clinical resources.
- `data/interim/` is reserved for temporary identifier-bearing transformations.
- `data/processed/` is reserved for canonical observations, hourly tables, windows,
  split manifests, and other derived patient-level products.
- These locations are local-only and ignored by Git.
- Public tests and demonstrations use synthetic data.
- Public `reports/` artifacts must be aggregate-only and must not contain patient,
  admission, stay, window, timestamp, or FHIR-reference values.

Fingerprints are one-way integrity values; they are not a basis for treating
restricted data as public or deidentified.

## Data minimization and privacy

Processing should use only variables required by the defined research task. Direct
names and other unnecessary identifiers must not be extracted into modeling
products. Local identifiers required to enforce patient/admission/stay boundaries
must not be printed, logged, embedded in examples, or included in public reports.
Re-identification attempts and linkage for purposes outside authorized research are
prohibited.

## Version control and publication boundary

Raw, interim, processed, serialized-model, environment, and secret files are
excluded through `.gitignore`. Before publication or review, tracked files should
be checked for prohibited data classes and identifier-like content. Aggregate
counts may be versioned when they satisfy the public-metadata validator and do not
permit patient reconstruction.

No restricted clinical data may be publicly redistributed through source control,
release archives, notebooks, issue attachments, screenshots, logs, or synthetic
examples. Dataset terms may also govern derived artifacts and trained models and
must be reviewed before distribution.

## Credentials and access

Credentials and database URLs must be supplied through environment variables and
must not be committed. `.env.example` contains placeholders only. Any database use
should apply least privilege and read-only access where feasible. Legacy database
scripts must not be treated as an authorized clinical ingestion pathway without
separate review.

Access to local clinical products should be limited to authorized researchers with
a defined purpose. Future confirmatory or external datasets should be stored and
processed in the access-controlled environment required by their provider and
institution.

## Provenance and auditability

Canonical generation records the source-code commit, pre-run working-tree state,
generation timestamp, configuration hash, input fingerprint, and output
fingerprint. Publication regeneration should use `--require-clean-worktree`.
Experiment roles and data reuse are recorded in `EXPERIMENT_REGISTRY.md`; the
historical holdout access count remains four.

## Retention and disposal principles

Retention periods are not established by this repository. Before processing a
restricted dataset, the research team should document the applicable agreement,
minimum necessary retention, backup scope, access review, secure deletion method,
and handling of derived tables and models. Data should not be retained merely for
convenience after the authorized purpose and required retention period end.

Deletion must be deliberate, documented, and consistent with provider and
institutional requirements. Source clinical data must never be modified or deleted
by pipeline commands.

## Future external and confirmatory data

Before any independent dataset is accessed, the team should document authorization,
population and site independence, permitted variables and outputs, transfer and
storage controls, retention, incident response, and publication constraints.
Development-patient overlap must be tested locally without exposing identities.
The confirmatory protocol, model, features, threshold, and fingerprints must be
frozen before first outcome evaluation.

## Incident handling

The repository does not define an institutional incident-response process. Any
suspected disclosure, credential exposure, unauthorized access, or accidental Git
tracking should stop further dissemination and be escalated to the relevant data
controller, institution, and dataset provider under their established procedures.
