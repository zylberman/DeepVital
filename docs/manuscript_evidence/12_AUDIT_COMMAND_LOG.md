# Audit command log

Audit date: 2026-08-13. Commands were read-only except creation of files in this
directory and subsequent validation of those files. No clinical analysis,
training, holdout evaluation, branch operation, or scientific artifact generation
was executed.

## Repository and inventory

```bash
find .. -name AGENTS.md -print
sed -n '1,260p' AGENTS.md
git status --short
git branch --show-current
git rev-parse HEAD
git log -n 10 --oneline --decorate
git remote -v
git tag --list --sort=creatordate
rg --files
```

Results: clean `main`; commit `58c0ab1`; tags `phase3-preregistered-v1`,
`phase3-development-results-v1`, and `phase3-final-closure-v1`; 170 inventoried
paths; GitHub remote `https://github.com/zylberman/DeepVital.git`.

## Evidence inspection

Commands included `sed`/`rg` reads of README, current methods/results, frozen Phase
3 protocol/configuration, closure/model card/limitations, cohort/FHIR/governance/
reproducibility documents, producer code under `src/deepvital/`, scripts, tests,
CI, requirements, and structured reports. Python one-liners parsed JSON/CSV and
printed aggregate keys/values only. No patient identifiers or rows were printed.

Key structured sources inspected:

```text
reports/canonical_cohort_metadata.json
reports/canonical_v1/*.json
reports/internal_nested_*.csv/json
reports/phase3_*.json/csv
reports/archive/phase3_protocol_registration_v1.json
models/baselines/model_selection.json
```

## Environment and quality baseline

```bash
.venv/bin/python --version
.venv/bin/python -m pip freeze | sort
PATH="$PWD/.venv/bin:$PATH" make check
git diff --check
```

Results: Python 3.12.9; Ruff 0.16.0 passed; pytest 9.1.1 reported 101 passed,
0 failed, 53 warnings in 3.01 seconds. Warnings: 12 Joblib/NumPy deprecations and
41 scikit-learn logistic `penalty` future warnings. Pip warned that its user cache
was not writable; this did not affect installed-package inspection or tests.

## Technical limitations

- The audit did not access patient-level inputs, the private fold manifest, model
  coefficients, or OOF prediction rows.
- It did not run `scripts/run_phase3.py`, model training, clinical evaluation, or
  the synthetic demo.
- Official bibliographic metadata were not web-verified in this internal-first pass;
  primary-source searches are listed as pending.
- Exact line numbers may move in future commits; JSON keys and CSV row/column
  locators are preferred in the ledger.
- Requirements are not fully version-pinned; `pip freeze` records only the local
  audit environment, not a versioned lock file.
