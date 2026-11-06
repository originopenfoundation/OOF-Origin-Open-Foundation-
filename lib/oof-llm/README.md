# OOF Universal LLM Library v2.0

Dependency-free CommonJS inference library for Node 22-24. `require('./lib/oof-llm')` loads without LaRA, a registry database, consumer conversations or a model framework.

```js
const {createClient, ModelRegistry} = require('./lib/oof-llm');
const client = createClient({
  consumer_id: 'LaRA',
  env: process.env, // explicit server-side route/key; never frontend configuration
  instructions: trustedConsumerInstructions,
  validateOutput: (answer, input) => consumerValidation(answer, input)
});
const response = await client.generate({
  question: 'Explain this evidence.', language: 'English',
  passages: externallyResolvedEvidence, history: explicitlyTransferredHistory,
  signal: abortController.signal
});
```

Consumers own their governing instructions, authorization, personality, retrieval, authority decisions and session state. Each client owns its provider adapters, cooldown and metrics. No history or provider key is globally shared. The library never resolves canonical authority or stores permanent user memory. Consumer identifiers are application scoping, not authentication.

`ModelRegistry.register(metadata)` accepts no credential fields; `.select(requirements)` separates advertised and evidence-backed verified languages, permitted consumers, context, privacy, free/paid policy, availability, reliability and latency. Selection is a deterministic metadata decision, not a provider health probe. A client refuses a selected model that differs from its explicitly configured route; callers must configure the approved route deliberately. Unknown/paid models are excluded unless payment permission is explicit. No model is enabled by examples or documentation.

`AICommunicationGateway.generateDetailed` preserves configured provider/model plus provider-reported model, bounded usage data when returned, request latency, context truncation and actual fallback usage. Reported identity is an API claim, not hardware attestation. Missing usage/cost remains null; it is never invented. Text output is checked before LaRA's existing SSE delivery, so provider-native token streaming is not claimed. Structural/consumer validation is not complete factual verification.

Environment: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, optional `LLM_BASE_URL`, timeout/token/context/concurrency limits, and explicit `LLM_FALLBACK_*`. External routes require HTTPS; local compatible inference may use loopback HTTP. Requests reject redirects, enforce a 64 KiB response bound, normalize safe errors, cancel on disconnect, and apply bounded cooldown for 429. Default retry count is zero; only explicitly configured bounded fallback is attempted.

Activation: `node tools/lara_real_model_probe.cjs private-evidence.json` sends two actual synthetic prompts using server environment and saves only responses/diagnostics, never the key. No configured route yields BLOCKED. This tool's results must be reviewed for returned identity and usefulness. A controlled fixture must never be described as a real model. `tools/lara_multilingual_audit.cjs` captures eight scenarios for every discovered published language through the existing LaRA API, without inventing quality scores.

## Candidate evaluation snapshot - 19 October 2026

The live [OpenRouter catalog](https://openrouter.ai/api/v1/models) listed Gemma 4 26B A4B/31B `:free` routes with 262,144 context and zero token prices, and `qwen/qwen3-32b` with 131,072 context as a paid route. These are catalog claims, not verified LaRA language quality or guaranteed capacity. No production candidate is selected until endpoint, account permissions, licensing and actual quality are established. No paid request was made.

[Qwen3-32B](https://huggingface.co/Qwen/Qwen3-32B) is Apache 2.0; Gemma uses [Google Gemma terms](https://ai.google.dev/gemma/terms), not an assumed Apache license. Commercial use is subject to the selected model's actual terms and provider processing agreement, not granted by this implementation. 24B/32B-class inference belongs on an appropriate external GPU host; no weights were downloaded into Render and no inference framework was installed.

[OpenRouter provider logging](https://openrouter.ai/docs/guides/privacy/provider-logging) varies by endpoint; a free route does not imply zero retention or no training. Verify provider selection/account restrictions before sending user data. [Rate limits](https://openrouter.ai/docs/api_reference/limits) depend on account and route; 429 cooldown is implemented, but no account capacity or reliability is verified without a configured endpoint. Existing redaction, public-source access and consumer consent boundaries remain mandatory.
