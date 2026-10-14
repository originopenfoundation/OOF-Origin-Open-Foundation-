# LaRA Communication Intelligence Test v1.0

These tools capture baseline evidence without changing the assistant's runtime or prompts. They are deliberately separate from the deterministic `*.test.js` suite. An HTTP 200 or source match is not a conversational PASS.

Use a disposable checkout for local server testing: the real runtime creates analytics/learning files. Start it with the intended deployment configuration. For a preview baseline, set `NODE_ENV=production`, `LLM_PROVIDER=none`, and a sufficient local-only rate limit. Do not change the registry readiness report to enable inference. Wait for `/_lara/status` before collecting evidence.

```powershell
node --test tests/lara/*.test.js
node tests/lara/communication-audit.cjs --base http://127.0.0.1:4194 --out <private-output>/baseline.json
node tests/lara/communication-faults.cjs <private-output>/faults.json
node tests/lara/communication-audit.cjs --base https://oof-origin-open-foundation.onrender.com --out <private-output>/live.json --live-sample
```

The collector sends Origin `https://originopenfoundation.org`, the existing approved frontend. Override it in code if testing an explicitly configured alternate frontend; never weaken the server's origin policy. Public sampling sends ten synthetic prompts, at least 3.5 seconds apart. Local full collection sends 65 prompts across A–K, including the continuous six-turn G session and twenty-turn K session. D, G, H and K retain the actual anonymous session token only in process memory. Other cases start fresh. No enquiries are submitted and no real identities are created. Engineering probes test input errors, admin authorization, hostile origins, consent, nonexistent recognition and session reset.

Evidence includes exact inputs and responses, active style/language/route, source object/resource identifiers, retrieval status, provider, HTTP status and report-only state. Optional `AUDIT_BUILD_COMMIT` and `AUDIT_CONFIGURATION` label the tested deployment. For remote tests, use UNKNOWN unless the actual deployed revision is known. Do not infer a remote model name from a local environment template.

Each successful transport begins as `PENDING_MANUAL_REVIEW`. Review the actual answer against the embedded rubric, record PASS/FAIL/PARTIAL/BLOCKED with reasons, and retain the original response. Score applicable dimensions 0–5 only after semantic review. A missing real model leaves real-LLM tests BLOCKED and scores null. Never convert fallback answers into model-generated evidence. Any fabricated authority, unauthorized execution, sensitive disclosure or boundary bypass blocks overall PASS.

Fault diagnostics are supplementary and explicitly labelled: real adapter access to an intentionally closed local port, invalid configuration, expired session, semantic-validator synthetic input, and exact personality selection requests. The fabricated validator input is never represented as an actual LaRA utterance. Missing-registry HTTP and conflicting-knowledge fixtures require a separate disposable deployment; these tools never alter the canonical registry to construct malicious evidence.

Keep full evidence private: existing canonical HTML can contain forwarded email/contact metadata. Do not commit raw response JSON, session tokens, keys or contact information. Publish only sanitized summaries. Preserve baseline and post-fix runs separately. This collector makes no automatic final intelligence decision and can be rerun after an explicitly identified fix.

Baseline on 2026-10-14: latest repository commit `aefa6011de425c69990f8927bef9a07f269ca3cb`; local 2219 indexed resources versus public Render 1954, deployed revision unknown. Provider absent and public report-only active. 22/22 deterministic LaRA tests pass; actual conversations fail relevance, topic continuity, tone and multilingual explanations. A greeting returns an unrelated ArtData excerpt; explanatory governance questions route to assessment templates. Diagnostic preview score 10/50, real-LLM score N/A. Decision: COMMUNICATION_FAILED for the executed preview; no claim about the quality of an untested model. Preserve and investigate source contact metadata and insufficient semantic validation before model activation.
