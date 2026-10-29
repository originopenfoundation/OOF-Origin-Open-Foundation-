# OOF Problem Discovery core 1.0 (LaRA v2.2)

Deterministic, bounded incident framing before methodology navigation. Reuses
the existing consumer Knowledge view and navigator. No second registry, model
client, network request, persistent case database or UI dependency.

`discover({text, previous, evidence, verifyEvidence, criterion})` returns
`{result, state, navigation_query, changed_problem}`. Keep `state` only within
the existing expiring, isolated session. An explicit new problem clears prior
case context. At most six redacted user turns are retained; no case is saved
by the learning subsystem. Explicit knowledge/navigation modes leave discovery.

The seven stages are observation classification, problem framing, assumption
examination, competing hypothesis generation, evidence classification, root
validation and structured output. Domain rules cover authorization, software,
autonomy, energy, water and asset-value claims; unmatched domains stay unresolved.
Rules are conservative candidate explanations, not a general causal inference
solver or proof of real-model intelligence. Automatic detection is English/SK
focused; all other languages can select the explicit discovery mode. Template
output is EN/SK (some rule descriptions remain English). Multilingual quality
requires separate real-response review.

Machine-readable schema: `schemas/oof-problem-discovery.v1.schema.json`.
Versioned JSON contract: `schema_version: "1.0"`; `validate(result)` rejects
unknown states, missing provenance, dangling evidence IDs and unsafe or
promoted draft references. Every finding points to provenance records with
source and evidence kind. Retrieved Knowledge is a reference, not proof of a
visitor's incident. `knowledge_references` preserve the existing navigator's
source hash, identity, ranking, lifecycle, primary/supporting relevance and
existing declared relationships. REPORT_ONLY is preserved.

User prose, apparent measurements and HTTP evidence fields cannot validate a
root cause. The HTTP adapter intentionally does not accept evidence attestation.
Applications embedding the core may provide a verifier over trusted receipts,
explicit evidence-to-hypothesis/assumption bindings, and a reproducible criterion.
Only independently verified supporting evidence plus a passing criterion can
produce VALIDATED. Verified contradiction takes precedence. A verifier is an
application trust boundary; never implement it as a check of a user-supplied
`verified` flag. LLM confidence never contributes to status.

The current LaRA discovery response is deterministic, available even without
inference, and introduces zero additional model calls. Structured output is
visible in the existing widget and SSE result. It is not sent externally.
Existing chat policy, consent, secrets, quota/cooldown and generation gates stay
in place. Protected requests are handled by the existing boundary responses.

Verification:

```
node --test tests/lara/discovery.test.js
node tools/lara_discovery_acceptance.cjs evidence/discovery-v22.json
```

These engineering checks do not attest Groq availability or model quality.
