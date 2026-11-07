# Pending authority decision - scoped public inference

Status: PROPOSAL ONLY. No production policy change applied.

Current rule: `lara/server.js` computes public report-only from actual registry readiness. `lara/llm/policy.js` returns `allowed=false, reason=report_only` before model availability or scope selection. Registry readiness remains false due to duplicate OriginID and candidate identity review. Model credentials do not override that rule.

Requested decision: may independently permitted ordinary conversation, and explanation of already public integrity-checked supporting representations, use generation while canonical registry cutover remains report-only?

Proposed boundary for authorized review: ordinary conversation carries no canonical claims; supporting content remains explicitly non-canonical; unresolved identity is stated, not inferred; authoritative conflicts require clarification and preserve competing claims; quarantine/private/failed-hash content remains excluded. Restricted actions stay outside model permission. Canonical promotion and registry readiness do not change.

The existing explicit development+loopback review path can exercise this proposal with synthetic provider fixtures or separately authorized real inference. Current tests cover those technical branches, not policy approval. A governance owner must approve an explicit scope policy before public activation; do not add an environment bypass or set readiness manually.

Review record sources: `data/knowledge/reports/authority-review-queue.json`, `duplicate-origin-id-review.json`, `candidate-entity-review.json`, actual readiness report and full source provenance. Communication classifications are presentation labels, not new access grants.
