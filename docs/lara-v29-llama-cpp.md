# LaRA v2.9 local inference

Start a locally installed llama-server with a compatible, separately licensed GGUF model:
`llama-server -m path/to/model.gguf --alias lara-local --host 127.0.0.1 --port 8080 -c 8192`.

Set these server environment variables before starting LaRA:

- LLM_PROVIDER=llama.cpp
- LLM_MODEL=lara-local
- LLM_BASE_URL=http://127.0.0.1:8080/v1
- LLM_FALLBACK_PROVIDER=none
- LLM_STREAM=true to request upstream SSE. LaRA assembles the bounded stream before checking the answer and returning it.
- Optional LLM_TIMEOUT (milliseconds), LLM_MAX_TOKENS, LLM_CONTEXT_BYTES and LLM_MAX_CONCURRENT.
- Optional LLM_LOCAL_API_KEY if the local server requires it.

Use an existing authorized local review flow. Production public egress remains governed by LaRA's existing Groq policy. The local provider accepts literal loopback endpoints and rejects redirects and configured fallback.

Upstream [server API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) and [MIT license](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE). Review the exact model's license independently before use.
