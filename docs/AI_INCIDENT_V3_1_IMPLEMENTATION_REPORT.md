# OOF Global AI Incident Intelligence V3.1 implementation report

Date: 2026-10-09  
Audit baseline: `bd57c91b`  
Dataset at implementation: 262 public incident records

## Finding disposition

| Audit finding | State | Implementation |
| --- | --- | --- |
| Incident tests used a fixed record count | Resolved | Tests derive the expected count from the public canonical store. |
| Incident tests were absent from compatibility CI | Resolved | `tests.test_ai_incidents` runs in compatibility and daily-sync workflows. |
| Initial UI showed zero values before data arrived | Resolved | Metrics use an indeterminate state and the UI distinguishes loading, success, empty, and error. |
| Retry lost context | Resolved | Retry reloads in place and preserves the current query and filters. |
| Every analytical route reused the same incident list | Resolved | Architecture, industry, country, and trend routes render purpose-specific aggregate views. |
| Initial load downloaded every full assessment | Resolved | Initial load uses one 25-record summary projection; complete assessments load only when expanded. |
| No lightweight global filter index | Resolved | `incident-index.json` contains the summary projection used only when a cross-dataset filter requires it. |
| Map depended only on color and pointer input | Resolved | Country paths have labels and keyboard behavior, with a parallel country table and visible focus. |
| Geographic coverage was ambiguous | Resolved | The interface publishes total, geographically assigned, and location-unspecified counts. |
| Evidence corroboration was unclear | Resolved in model and UI | Independent source groups and corroboration state remain explicit; no corroboration is invented. Current records remain predominantly single-source. |
| Incident records had no stable indexable detail URL | Resolved | Every public record has a human-readable canonical HTML detail page and a lazy JSON detail projection. |
| Incident details lacked structured discovery metadata | Resolved | Detail pages include unique metadata, breadcrumb data, canonical URLs, and Report structured data. |
| Generated public projection could silently drift | Resolved | Validation checks totals, duplicate IDs/slugs, source URL shape, missing details, and detail identity. |

## Public data architecture

- `summary.json`: dataset-level metrics and scope.
- `map.json`: country-level map counts without repeated full assessments.
- `aggregations.json`: architecture, industry, country, trend, and evidence summaries.
- `incidents-page-N.json`: 25 lightweight incident summaries per page.
- `incident-index.json`: lightweight all-record index loaded only for cross-dataset filtering.
- `incident-details/<slug>.json`: one full record fetched on demand.
- `ai-incidents/incidents/<slug>/index.html`: static, indexable incident detail page.

## Performance gate

Measured compressed first-view payload for incident data, map geometry, registry, incident JavaScript, and incident CSS: approximately 338 KB. This is below the 500 KB compressed target. The first incident page is approximately 10 KB compressed; full automated assessments are excluded from initial loading.

## Trust and interpretation boundaries

- Source facts remain separate from automated analysis.
- Known facts, reported claims, material unknowns, evidence gaps, and governance interpretation are displayed as separate sections.
- Architecture relevance does not assert architecture failure, legal fault, liability, or regulatory non-compliance.
- Automated output remains explicitly non-approved unless an authorized review sets `oofApproved`.
- Country and trend counts describe the public dataset, not global prevalence.

## Release gates

- Canonical/public projection count match: required.
- Duplicate ID and slug check: required.
- Valid source reference check: required.
- Public detail identity check: required.
- Representative 20-record route/detail/date-order test: required.
- Automated analysis validation: required.
- AI compatibility and discovery validation: required.
- Keyboard and responsive browser verification: required before deployment.

## Residual limitations

- Most current records have one independent source group, so independent corroboration is not established for those records.
- Industry is absent from many upstream records and is shown as unspecified rather than inferred.
- Map geography remains country-level; records without an established country remain discoverable in the monitor and are counted separately.
- Automated architecture and severity analysis remains preliminary and is not an OOF Approved Assessment.
