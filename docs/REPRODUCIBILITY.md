# DeepVital reproducibility

DeepVital separates public software reproducibility from reproduction of the
clinical-data experiment. Python 3.12 is the tested reference version for the
public workflow.

> Synthetic data are intended only for software demonstration and do not
> represent a clinically valid population.

## Publicly reproducible workflow

An external user can install the declared dependencies, run the automated tests,
generate fully artificial vital signs, and complete the isolated synthetic
demonstration without MIMIC-IV access, PostgreSQL, patient-level files, or the
Phase 2 developmental holdout.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
make check
make demo
```

`make demo` writes only to `artifacts/synthetic_demo/`, which is ignored by Git.
The default run creates:

```text
artifacts/synthetic_demo/
├── raw_vitals.csv
├── hourly_vitals.csv
├── windows.csv
├── split_summary.json
├── validation_metrics.json
├── holdout_metrics.json
└── demo_summary.json
```

The demo generates fictitious patients and hourly vital signs, adds artificial
missingness and MAP decreases, builds 12-hour trailing windows, labels sustained
hypotension in the following 6 hours, and splits by fictitious patient. A dummy
classifier and logistic regression are trained on the synthetic training split.
Model and Youden-threshold selection use synthetic validation only; the selected
configuration is then applied to a synthetic holdout. No demo metric is evidence
of clinical utility.

## What requires authorized data

The following steps require authorized local access to MIMIC-IV-on-FHIR and are
not reproduced by the public demo:

- extraction of MIMIC-IV FHIR resources;
- construction of the actual ICU cohort and private split manifest;
- exact reproduction of the persisted Phase 1 and Phase 2 reports.

## Canonical cohort and historical boundary

The only official Phase 1B construction command is:

```bash
python scripts/build_canonical_cohort.py \
  --canonical-input data/processed/canonical_vitals.csv \
  --fhir-dir data/mimic-iv-clinical-database-demo-on-fhir-2.1.0/fhir
```

It uses administrative ICU Encounter periods and writes canonical-v1 artifacts
without overwriting historical reports. `reports/canonical_cohort_metadata.json`
records aggregate counts and SHA-256 fingerprints. Hashes are one-way integrity
tokens; no clinical identifier is written to public metadata.

`source_code_commit` identifies the checked-out commit at command start.
`working_tree_dirty_before_run` captures whether that source tree already contained
uncommitted changes before any output was written. `generation_timestamp` records
the run time. The metadata can be committed later; it deliberately does not claim
that its source commit is the same commit that eventually incorporates the report.

Publication regeneration should use `--require-clean-worktree`. In strict mode the
command captures Git state and aborts before constructing or writing any output if
`working_tree_dirty_before_run` would be true. The current canonical metadata
records `working_tree_dirty_before_run: false` and source commit
`79bb0564f75382eb787e3ccfb298733bdd31d9f2`.

The deprecated `scripts/build_phase_1b_dataset.py` route is observation-bounded and
requires `--allow-legacy-builder`. It exists only for historical reproduction.

## Evaluation reproducibility roles

- Historical metrics are `development_holdout_v1`; they remain unchanged and the
  recorded access count remains four.
- `scripts/run_internal_nested_cv.py` performs development-only patient-grouped
  nested cross-validation. Preprocessing and candidate selection occur inside the
  corresponding training folds; thresholds come from inner predictions. Clinical
  benchmarks use the identical folds and windows. Each outer fold keeps its own
  inner-selected threshold; pooled threshold-0.5 results are descriptive and no
  final threshold is frozen.
- The internal report verifies that each patient belongs to one outer fold, all of
  that patient's windows remain together, and the OOF prediction count equals the
  eligible-window count. Ranking-only clinical scores exclude Brier score and log
  loss and include neutral-risk and complete-case availability analyses.
- No confirmatory dataset currently exists. `scripts/evaluate_confirmatory.py`
  accepts only `--dataset-role confirmatory-test`, verifies protocol/cohort/model
  hashes, requires frozen model metadata and a private development manifest, and
  rejects patient overlap.
- The first valid confirmatory run consumes the registered cohort. Identical later
  runs are recorded as technical reproductions; changed hashes are rejected.

Raw and processed clinical tables remain outside version control. Aggregate
reports document the completed experiment without redistributing patient-level
records.

## What should not be repeated casually

`scripts/evaluate_baseline_models.py` accesses the Phase 2 developmental holdout,
overwrites persisted evaluation reports, and increments its access counter. It is
not an installation check and must not be run as part of public reproducibility.
The persisted Phase 2 results should not be modified to demonstrate that the
software works.

Use `make check` for code verification and `make demo` for an end-to-end example.

## Four distinct activities

| Activity | Data | Purpose | Writes Phase 2 results? |
| --- | --- | --- | --- |
| Unit tests | Synthetic fixtures and temporary paths | Verify software contracts | No |
| Synthetic demo | Generated fictitious vital signs | Exercise an isolated end-to-end workflow | No |
| Clinical baseline training | Authorized local cohort, training and validation splits | Fit and select the Phase 2 baselines | Yes |
| Developmental-holdout evaluation | Authorized local developmental holdout | Produce the existing internal development evaluation | Yes |

The first two activities are safe public workflows. The latter two belong to the
documented clinical-data experiment and require both authorized data and deliberate
methodological review.

## Custom synthetic output

The generator and demo accept explicit sizes and seeds:

```bash
python scripts/generate_synthetic_demo.py \
  --patients 30 \
  --hours 48 \
  --seed 20260726 \
  --output artifacts/synthetic_demo/raw_vitals.csv

python scripts/run_synthetic_demo.py \
  --patients 30 \
  --hours 48 \
  --seed 20260726 \
  --output-dir artifacts/synthetic_demo
```

The generated values are constrained to broad physiological ranges to support
software testing, but their distributions are not intended to emulate a real ICU
population.
