# Phase 1B Completion Audit

> **Historical document.** This audit covers the legacy 8,872-window route. It is
> preserved for traceability and is not the canonical cohort report.

**Audit date:** 2026-07-26  
**Scope:** Hourly aggregation, missingness, retrospective windows, future MAP label,
and patient-level splitting  
**Status:** Complete for the local demo; no model training performed

## Leakage review

| Check | Evidence | Result |
|---|---|---|
| No backward fill | Hourly code only carries `last_real_value` forward | Pass |
| Forward fill limited | Configured maximum is two hours | Pass |
| Stay isolation | Canonical input is streamed as complete patient/admission/stay groups | Pass |
| Trailing rolling features | Feature functions receive only sliced history through `t` | Pass |
| Predictor boundary | Sequence offsets end at `h0` | Pass |
| Outcome boundary | Future MAP list starts at index `t+1` | Pass |
| Current MAP excluded | Label receives only the six future MAP aggregates | Pass |
| Future missingness | Incomplete future MAP returns indeterminate and is excluded | Pass |
| Patient split | Deterministic `subject_id` assignment with runtime overlap assertion | Pass |
| Identifier privacy | Manifest is private; public reports contain aggregates only | Pass |

## Accounting

The requested identities are partition identities and therefore use addition:

```text
12,309 hourly rows × 8 variables
= 76,190 observed + 8,846 forward-filled + 13,436 unfilled
= 98,472 cells

10,008 candidates = 8,872 created + 1,136 incomplete-future-MAP exclusions

8,872 created = 1,759 positive + 7,113 negative
```

All are asserted at runtime and covered by synthetic tests.

## Split summary

| Split | Assigned patients | Patients with windows | Admissions | ICU stays | Windows | Positive | Negative | Prevalence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Train | 70 | 63 | 84 | 90 | 5,636 | 1,088 | 4,548 | 19.30% |
| Validation | 15 | 14 | 15 | 16 | 1,685 | 452 | 1,233 | 26.82% |
| Test | 15 | 15 | 18 | 19 | 1,551 | 219 | 1,332 | 14.12% |

Patient overlap is zero.

## Remaining limitations

- The audited legacy grid spans supported observation hours rather than confirmed
  administrative ICU bounds; the two existing Phase 1B paths should be unified.
- Invasive and non-invasive BP values are pooled by median without source priority.
- Complete future MAP may select more frequently monitored periods.
- Windows overlap and are statistically correlated.
- The small deterministic split is not outcome-stratified and has differing
  prevalence.
- No preprocessing transformation or model has been fit.
