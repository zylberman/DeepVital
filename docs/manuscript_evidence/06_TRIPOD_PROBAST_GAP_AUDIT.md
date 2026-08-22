# Preliminary TRIPOD+AI and PROBAST+AI gap audit

This is an internal preliminary mapping, not a formal certification. Item wording
must be checked against the current official instruments before submission.

## TRIPOD+AI-oriented reporting audit

| Domain/item | Status | Repository evidence | Required action |
|---|---|---|---|
| Title identifies prediction study and development role | Partial | Working title; Phase 3 docs | State internal development explicitly |
| Abstract | Absent | No manuscript | Draft structured abstract after declarations |
| Background and objective | Covered | `RESEARCH_PROTOCOL.md`, Phase 3 protocol | Add external citations |
| Source/setting | Partial | Demo FHIR version and resources documented | Add clinical dates, access and official citation |
| Eligibility and flow | Partial | Aggregate flow/counts available | Patient-level mutually exclusive exclusions unavailable |
| Outcome definition/timing | Covered | Config, code, protocol | Cite clinical rationale externally |
| Predictor definition/timing | Covered | Locked list and derivation contract | Use supplementary dictionary |
| Sample-size rationale | Partial | Fixed demo cohort and counts | Explain convenience/development size and effective patient count |
| Missing data | Covered | Bounded forward fill; fold imputation; indicators | Quantify predictor-level missingness succinctly |
| Model specification | Covered | Frozen logistic configuration and C grid | Report fitted strategy as development candidate |
| Internal validation | Covered | 5×3 patient grouping; OOF invariants | Provide fold diagram |
| Performance measures | Covered | Structured reports | Explain ranking-score metrics and unavailable probability losses |
| Calibration | Covered/limited | Cross-fitted candidate calibration | Do not imply comparator calibration or clinical threshold validity |
| Model comparison | Covered | Paired clustered bootstrap | State no confirmatory hypothesis test |
| Results with uncertainty | Covered | Exact pooled and paired results | Add tables/figures sourced from frozen reports |
| Participant/predictor distributions | Partial | Aggregate missingness and counts | Baseline demographic/clinical descriptors absent |
| Full model availability | Partial | Model form and features public; coefficients/patient predictions not public | Decide safe model-sharing and provide coefficients if permitted |
| Limitations | Covered | `LIMITATIONS.md` | Preserve demo and correlated-window caveats |
| Registration/protocol | Covered | tags, hashes, archived registration | Cite identifiers in manuscript |
| Data/code availability | Partial | GitHub URL; restricted data boundary | Finalize statements and license |
| Funding/COI/authorship | Absent | Not asserted | Author completion required |

## PROBAST+AI-oriented risk-of-bias/applicability audit

| Domain | Judgement | Evidence | Concern/action |
|---|---|---|---|
| Participants—risk of bias | High/unclear | Complete demo source; administrative ICU periods | Demo convenience cohort; limited representativeness; patient-level exclusions not fully reported |
| Participants—applicability | High concern | 100-patient MIMIC demo | Does not represent broad ICU populations/sites/devices |
| Predictors—risk of bias | Low to moderate | Prespecified 18 features; available by `t`; fold preprocessing | BP pooling provisional; missingness reflects charting practice |
| Predictors—applicability | Moderate/high concern | Routine vitals and configured FHIR codes | Code mappings/source behavior may not transport |
| Outcome—risk of bias | Moderate | Future-only strict rule; observed MAP only | Complete-horizon selection; retrospective proxy, not adjudicated event |
| Outcome—applicability | Moderate concern | MAP<65 for two hours | Clinical meaning/treatment context not captured |
| Analysis—risk of bias | Moderate | Nested grouped CV, fixed protocol, paired cluster bootstrap | Only 92 independent patients; many correlated windows; no external validation |
| Analysis—overfitting control | Covered for development | Inner tuning, fold preprocessing, one OOF/window | Effective sample size and events per patient incompletely described |
| Missing data analysis | Partial | Bounded forward fill, indicators, fold imputation | Failed incomplete-future-MAP sensitivities remain unresolved |
| Calibration | Partial | Candidate cross-fitted Platt calibration | Retained comparator is ranking-only; no external calibration |
| Comparator | Covered | Prespecified `map_mean_6h` | Strong simple baseline appropriately retained |
| Optimism/validation | Partial | Nested CV and preregistration | Same demo remains development data; generalization unknown |
| Overall risk of bias | At least moderate; potentially high | Strong leakage safeguards but small convenience cohort | Formal independent PROBAST+AI review required |
| Overall applicability | High concern outside demo context | No external/prospective evidence | Restrict claims to internal development evidence |

## Priority gaps

1. Complete author/ethics/data-use declarations and official citations.
2. Add participant descriptors and patient-level event counts if a privacy-safe,
   preregistered descriptive extraction can be performed without altering Phase 3.
3. Explain effective sample size: 92 patients, not 8,970 independent observations.
4. Provide a journal-specific TRIPOD+AI checklist and independent PROBAST+AI review.
5. Do not repair or replace failed sensitivities inside the Phase 3 record.
