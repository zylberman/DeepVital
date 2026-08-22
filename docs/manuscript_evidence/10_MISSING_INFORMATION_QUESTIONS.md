# Missing information: author questions

## Priority 1 — required before preprint

1. Who are the authors, their exact affiliations, ORCIDs, and corresponding author?
2. What CRediT contributions did each author make, and have all authors approved authorship?
3. What ethics approval, exemption, or institutional determination applies? Provide institution, identifier, date, and approved wording.
4. Under which exact PhysioNet/MIMIC credentialing and data-use terms was the local FHIR demo obtained?
5. What funding and conflicts-of-interest statements are accurate?
6. What generative-AI disclosure is required by the target venue for this audit and later drafting?
7. Which code license will govern the repository?
8. What is the target preprint server/journal, and which reporting/declaration format does it require?

## Priority 2 — scientific reporting

9. What population is the intended target beyond the demo (adult ICU broadly, a specific ICU type, or another scope)?
10. Is a privacy-safe aggregate count of patients with at least one positive window available from the frozen cohort without altering Phase 3?
11. Are median and IQR of eligible windows per patient already preserved in a governed artifact? The public report contains only mean and range.
12. Are demographics and clinically relevant baseline descriptors available and permitted for aggregate reporting?
13. What external clinical references justify the MAP<65 mmHg, two-consecutive-hour endpoint for the intended population?
14. Was the +0.020 relevance margin supported by expert consensus, literature, simulation, or investigator judgement? Document the rationale without changing it.
15. Are fitted Phase 3 coefficients and point-level OOF predictions preserved in a governed location, and may aggregate coefficient/model details be published?

## Priority 3 — publication infrastructure

16. Will the code release be archived with Zenodo or another DOI service?
17. Which official MIMIC-IV FHIR citation/version URL should be used?
18. Who should be acknowledged for data access, infrastructure, or methodological review?
19. What retention and secure-disposal rules applied to the local restricted data?
20. Is independent statistical/clinical review planned before journal submission?
