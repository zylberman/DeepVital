# Declarations and ethics status

| Declaration | Status | Repository evidence | Required author input |
|---|---|---|---|
| Ethics approval/exemption | Missing | Repository explicitly asserts none | Institution, board, identifier, decision/date, or justified public/deidentified-data exemption |
| Deidentified-data basis | Partial | MIMIC demo and privacy safeguards documented | Official MIMIC/PhysioNet wording and local institutional determination |
| PhysioNet compliance/training | Missing | Authorized access mentioned only | Credentialing/course status and agreement applicable to actual source |
| Data availability | Draftable | Restricted inputs excluded; aggregate reports public | Confirm exact dataset URL/version and access instructions |
| Code availability | Draftable | `https://github.com/zylberman/DeepVital.git`, commit/tag verified | Confirm public release URL and archival DOI if created |
| Code license | Missing | No project-level `LICENSE` | Select and add license before public reuse claims |
| Data license | Missing in publication-ready form | Provider terms acknowledged | Cite exact MIMIC-IV Demo/FHIR license and redistribution restrictions |
| Funding | Missing | No assertion | Funder/grant or “no specific funding” confirmation |
| Conflicts of interest | Missing | No assertion | Author declarations |
| Author contributions | Missing | No author list | CRediT roles agreed by all authors |
| Acknowledgements | Missing | No assertion | Contributors/infrastructure/data providers |
| Generative AI disclosure | Missing | This evidence packet was AI-assisted | Authors must disclose according to venue policy and retain human accountability |
| ORCID | Missing | No records | Each author as applicable |
| Affiliations | Missing | Repository declines to assert | Exact institutional affiliations |
| Corresponding author | Missing | No record | Name and contact |
| Coauthors | Missing | No record | Determine authorship using accepted criteria; do not infer from Git alone |

## Draft data-availability boundary

“The public repository contains code, configurations, frozen aggregate reports,
and synthetic tests. Patient-level MIMIC-IV FHIR resources, derived hourly tables,
windows, OOF predictions, and private fold assignments are not redistributed.
Eligible researchers must obtain the source data under the provider’s current
access and data-use requirements.”

This text must be checked against current PhysioNet/MIMIC terms before use.

## Draft code-availability boundary

“The audited code state is Git commit
`58c0ab118329bf5a30f6591a6163faf2f89ae007`, tagged
`phase3-final-closure-v1`, at `https://github.com/zylberman/DeepVital`.”

Do not claim an archival DOI until one exists. No Zenodo integration or DOI was
found during this audit.
