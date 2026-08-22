# Synthetic Demo Verification

## Verification summary

* Verification date: 2026-08-22 (UTC)
* Verified commit: `3e1ffa4b88039a13f62d0f133c18ee4fc4998f7d`
* Environment: clean temporary clone with a newly created virtual environment
* Python: 3.12.9
* Ruff: 0.16.0
* pytest: 9.1.1
* Automated checks: Passed
* Synthetic demonstration: Passed
* MIMIC-IV patient-level data used: No

## Clean-environment procedure

The repository was cloned into a new temporary directory at the verified commit.
Only files tracked by Git were included. A new Python 3.12 virtual environment was
created, and all declared development dependencies were installed from scratch.

The Python executable used for verification belonged to the temporary clone rather
than to the original development environment.

## Installation and verification commands

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
make check
make demo
```

## Automated-check results

The following command was executed:

```bash
make check
```

Ruff completed successfully:

```text
python -m ruff check .
All checks passed!
```

pytest completed successfully:

```text
python -m pytest -q
101 passed, 53 warnings in 38.44s
```

Warning summary:

* `tests/test_evaluation_protocol.py`: 12 warnings.
* `tests/test_phase3_implementation.py`: 41 warnings.
* The warnings did not cause test failures or a non-zero exit status.

Final result:

* Ruff: Passed.
* pytest: 101 tests passed.
* Exit status: 0.

## Synthetic-demonstration results

The documented public demonstration was executed with:

```bash
make demo
```

This command runs:

```bash
python scripts/run_synthetic_demo.py
```

The demonstration completed successfully and reported:

```text
data_source: fully_synthetic
patient_overlap: 0
input_window_hours: 12
label_horizon_hours: 6
```

The synthetic data are intended only for software demonstration and do not
represent a clinically valid population.

## Generated outputs

The demonstration generated the following seven files under
`artifacts/synthetic_demo/`:

1. `raw_vitals.csv`
2. `hourly_vitals.csv`
3. `windows.csv`
4. `split_summary.json`
5. `validation_metrics.json`
6. `holdout_metrics.json`
7. `demo_summary.json`

The output directory is ignored by Git and does not modify the persisted clinical
reports.

## Confirmation of synthetic data use

The verification was performed from a clean clone containing only files tracked
in the verified commit. No local MIMIC-IV data, PhysioNet credentials,
patient-level files, private split manifests or clinical-data directories were
copied into the verification environment.

The default synthetic route generates fictitious patients and hourly vital signs.
It introduces artificial missingness and MAP decreases, constructs 12-hour
retrospective windows, labels sustained hypotension during the following six
hours, and partitions the artificial cohort by fictitious patient.

The demo writes only to `artifacts/synthetic_demo/`. It does not read from the
clinical data tree or overwrite Phase 1, Phase 2 or Phase 3 results.

## Scope and limitations

This verification confirms that:

* The declared dependencies can be installed in a new environment.
* Ruff and the complete automated test suite pass.
* The public synthetic demonstration executes end to end.
* The demonstration uses fully artificial data.
* The synthetic patient partitions have no patient overlap.

This verification does not:

* Reproduce the MIMIC-IV clinical experiment.
* Recompute the canonical clinical cohort.
* Independently verify the persisted Phase 1, Phase 2 or Phase 3 results.
* Access restricted MIMIC-IV-on-FHIR resources.
* Provide external or prospective validation.
* Establish clinical validity, utility or readiness for deployment.

The synthetic metrics are software-demonstration outputs and must not be
interpreted as evidence of clinical performance.

