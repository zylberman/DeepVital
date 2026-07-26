# DeepVital — Project Status

## 1. Project objective

DeepVital is a research-only clinical machine-learning project for the early
prediction of sustained hypotension in ICU patients using multivariate
vital-sign time series.

The default prediction task is:

- Observation window: previous 12 hours.
- Prediction horizon: next 6 hours.
- Primary event: MAP below 65 mmHg for at least two consecutive hourly
  observations.

DeepVital is not a medical device and is not intended for clinical
decision-making.

---

## 2. Available data

The project currently uses:

**MIMIC-IV Clinical Database Demo on FHIR 2.1.0**

Characteristics:

- 100 randomly selected patients.
- FHIR R4 resources.
- 30 gzip-compressed NDJSON files.
- One complete FHIR resource per NDJSON line.
- Approximate FHIR directory size: 50 MB.
- Emergency department resources are distributed separately from the main
  hospital and ICU resources.

Raw data location:

```text
data/mimic-iv-clinical-database-demo-on-fhir-2.1.0/fhir
