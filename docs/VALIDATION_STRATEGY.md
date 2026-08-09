# Validation strategy

```mermaid
flowchart TD
    A["Development — completed"] --> B["Internal patient-grouped validation — completed"]
    B --> C["Frozen strategy — in progress"]
    C --> D["Independent confirmatory test — pending"]
    D --> E["External validation — not started"]
    E --> F["Prospective evaluation — not started"]
```

## Development — completed

The 100-patient MIMIC-IV-on-FHIR demo supports pipeline construction, feature and
outcome specification, conventional candidates, clinical benchmarks, and
historical development analyses. The former holdout is reclassified as development
evidence following four accesses.

## Internal patient-grouped validation — completed

Five-by-three nested cross-validation provides one out-of-fold prediction per
eligible window, with patients grouped across all folds. Results quantify internal
development performance and paired benchmark differences. They do not provide an
independent estimate of generalizability.

## Frozen strategy — in progress

The model strategy and final threshold are not frozen. The immediate decision is
whether six-hour mean MAP should remain the parsimonious development strategy or
whether further multivariable work demonstrates reproducible added value. Any
calibration method must be selected and fitted using development data only.

## Independent confirmatory test — pending

The confirmatory cohort must contain entirely new patients. Protocol, cohort,
features, model, threshold, and fingerprints must be frozen before access. The
inference-only evaluator is implemented but has not been executed.

## External validation — not started

External validation requires an independently sourced setting and assessment of
transportability across population, institution, devices, workflow, and charting
practice. A confirmatory split and external validation are not synonymous.

## Prospective evaluation — not started

Prospective work would require governance, ethics, privacy, interoperability,
usability, alert-burden, safety, workflow, and clinical-impact planning. No live or
silent prospective evaluation is currently justified by the available evidence.
