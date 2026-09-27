# OOF Knowledge Infrastructure 1.0

## Implementation status

The infrastructure runs in report-only parallel mode. It does not change page text, canonical URLs, the existing search index, or production consumer behavior.

## Delivered

- Separate object and representation registries.
- Stable object IDs from valid OriginID values and approved architecture or hierarchy coordinates.
- Duplicate OriginID quarantine with a human-review report.
- Separate authoritative and discovery relationships.
- Explicit authority role, authority domain, visibility, allowed-consumer, language, and provenance fields.
- Deterministic exact, relationship, and lexical retrieval indexes.
- Versioned JSON schemas and a public manifest with content hashes.
- Candidate entity review for 39 deterministic groups; no automatic merge.
- Validation for identity, hierarchy, provenance, visibility, retrieval, deterministic builds, and report-only parity.
- GitHub Actions rebuild and validation.

## Retrieval order

1. Cache.
2. Exact identifier, canonical URL, or unambiguous normalized name.
3. Governed relationship lookup.
4. Lexical retrieval.
5. Optional semantic retrieval in a later approved phase.
6. AI reasoning only after deterministic retrieval paths are exhausted.

The current site search remains the public fallback.

## Governance holds

- Seven duplicate OriginID groups affecting 15 representations require human review.
- Thirty-nine candidate entity groups require authority review.
- Unresolved representations remain separate and are not silently merged.
- No bulk URL rename is applied.
- No LaRA integration or public API is enabled.

## Phase 6 recommendation

Do not start production consumer cutover until duplicate OriginID and candidate entity reviews are resolved and retrieval parity is accepted by OOF authority.
