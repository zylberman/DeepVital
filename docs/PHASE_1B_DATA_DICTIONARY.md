# Phase 1B Private Dataset Dictionary

These local files contain identifier-bearing research data and are not public
artifacts.

## Hourly table

Base columns:

| Column | Definition |
|---|---|
| `subject_id` | Local patient identifier |
| `hadm_id` | Local hospital-admission identifier |
| `stay_id` | Local ICU-stay identifier |
| `hour` | UTC clock-hour timestamp |

For every configured variable `{variable}`:

| Column pattern | Definition |
|---|---|
| `{variable}_observed_value` | Median of real values charted in the hour |
| `{variable}_observed` | 1 when at least one real measurement exists |
| `{variable}_measurement_count` | Number of real measurements aggregated |
| `{variable}_value` | Observed or at most two-hour forward-filled value |
| `{variable}_missing` | 0 when observed in the hour; 1 otherwise |
| `{variable}_hours_since` | Hours since last real observation; empty if none |
| `{variable}_forward_filled` | 1 only when the current value was carried forward |

## Window table

Base columns:

| Column | Definition |
|---|---|
| `subject_id`, `hadm_id`, `stay_id` | Local grouping identifiers |
| `prediction_time` | Hour `t` at the end of the predictor window |
| `window_id` | Deterministic local hash; private and not included in reports |
| `split` | Patient-level train, validation, or test assignment |
| `label` | Future-only sustained-hypotension outcome |

For offsets `h_m11` through `h0`, each variable has:

| Column pattern | Definition |
|---|---|
| `{variable}_{offset}_value` | Predictor value available at that hour |
| `{variable}_{offset}_observed` | Real-observation indicator |
| `{variable}_{offset}_measurement_count` | Real measurements in the hour |
| `{variable}_{offset}_missing` | Whether the hour lacked a real measurement |
| `{variable}_{offset}_hours_since` | Hours since the last real measurement |
| `{variable}_{offset}_forward_filled` | Bounded-forward-fill indicator |

The label is based exclusively on real MAP values at `t+1` through `t+6`; future
values are not stored as predictor columns.

Each variable also has closed trailing-window tabular summaries: current, previous,
change, mean, median, minimum, maximum, standard deviation, slope, observed count,
missing proportion, and current time since the last real measurement. Pulse
pressure and shock index are included with missing indicators.
