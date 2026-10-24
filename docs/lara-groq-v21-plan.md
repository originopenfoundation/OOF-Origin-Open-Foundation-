# LaRA v2.1 implementation plan

1. Verify PR9/10, exact tree and main1; preserve current HTTP security while reconciling PR10.
2. Add approved Groq route to existing shared transport; pin endpoint/model, keep fallback disabled, enforce free-account attestation and safe data handling.
3. Separate communication scopes behind existing authority gate; public policy stays review-only without explicit registry approval.
4. Add strict model identity and bounded quota diagnostics; redact Groq credentials across input, output and evidence.
5. Add resumable real-model evidence collection and preserve all 104 unexecuted scenario statuses.
6. Run existing/new Node, Knowledge, build, language and 256 MiB server checks.
7. Publish a clean PR on current main1 and produce PDF audit. Render deployment requires separate authorization.
