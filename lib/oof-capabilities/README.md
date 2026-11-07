# Trusted capability core 1.0

Three adapters expose the existing Knowledge Navigator, Problem Discovery and
Cross-Architecture Reasoning. These are capabilities, not autonomous agents.
Definitions declare contracts, tools, permissions, limits, failure handling and
audit requirements. Caller authority cannot be expanded by the adapter. All
three built-in adapters require read-only Knowledge permission and expose no
external tool. The generic core never loads plugins or arbitrary agent code.

Inputs and outputs are copied and validated. Results are frozen. Handoffs need
an internal validated receipt, a permitted source contract, and the same session.
Audit entries contain digests and status rather than raw conversation. The ring
is bounded; the application receives its own request evidence. The host is
responsible for retaining authorized private audit evidence.

Input/output sizes, tool calls and elapsed time are checked. Trusted synchronous
code is not preempted: late output is rejected after it returns. This is not a
CPU sandbox for untrusted JavaScript. No external actions, network tools,
unlimited recursive chains, paid service or background execution are introduced.
