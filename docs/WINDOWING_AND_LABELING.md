# Hourly Preprocessing, Windowing, and Labeling

DeepVital is a retrospective research prototype, not a medical device. Phase 1B
does not train or evaluate a model.

## Hourly grid

Each ICU stay is processed independently. The grid begins at the hour containing
the FHIR ICU Encounter `period.start` and ends at the hour containing `period.end`.
Canonical observations outside the exact period are excluded and counted.

Multiple normalized values for the same stay, variable, and hour are aggregated by
the median. For every variable/hour the private hourly table stores:

- raw hourly median;
- real-observation indicator;
- number of real measurements;
- hours since the last real measurement in the same stay;
- observed or bounded-forward-filled value;
- forward-fill indicator;
- missingness indicator.

All eight variables currently have a configurable two-hour forward-fill limit.
There is no backward filling, future-dependent interpolation, or population-value
imputation.

## Predictor window

At prediction time `t`, the sequence representation contains exactly the closed
trailing grid:

```text
t-11, t-10, ..., t-1, t
```

The private window table preserves six sequence fields per variable and hour:
value, observed indicator, measurement count, missing indicator, hours since last
real observation, and forward-fill indicator.

Tabular features use the same trailing 12 hours only:

- current and previous values;
- one-hour change;
- rolling mean, median, minimum, maximum, standard deviation, and linear slope;
- observed count and missing proportion;
- hours since last real observation;
- pulse pressure and shock index when their inputs and denominator are valid.

Invalid derived features remain missing and have explicit missing indicators.

## Primary outcome

The label uses only real hourly MAP aggregates in `t+1` through `t+6`.
Forward-filled MAP is not used for outcome assessment. Positive means at least two
consecutive future MAP values strictly below 65 mmHg. MAP equal to 65 does not
qualify. Two isolated low values do not qualify.

The primary label requires all six future MAP hours. Missing future MAP makes the
label indeterminate and excludes the window; it is never silently labeled negative.

Alternative thresholds, inclusive comparison, nonconsecutive definitions, and one-
or three-hour duration definitions are documented in `configs/labeling.yaml` but
are not generated as primary labels.

## Actual demo result

- 12,502 hourly rows;
- 10,185 candidate prediction times after temporal-boundary checks;
- 1,215 excluded for insufficient future MAP assessment;
- 8,970 eligible labeled windows;
- 1,774 positive and 7,196 negative windows;
- event prevalence 19.78%.

Overlapping windows are correlated and do not represent unique clinical events.
