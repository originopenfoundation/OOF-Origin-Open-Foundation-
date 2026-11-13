# LaRA v2.7.1 capability matrix

| Capability | Existing state | Evidence | Acceptance | Repair / blocker |
|---|---|---|---|---|
| Public authorization | Fail closed | Live status: no scopes, report-only | BLOCKED | Legitimate canonical approval workflow only |
| Groq configuration | Configured | Live status llm_configured=true | NOT-RUN integration | Authorized isolated multi-turn run required |
| Knowledge retrieval | Implemented | Automated suite exit 0 | AUTOMATED-VERIFIED | Real model grounding test required |
| Browser widget | Implemented | Live profile selection and voice controls | BROWSER-VERIFIED | Independent engine/mobile acceptance required |
| STT/TTS controls | Implemented | Browser contract tests | AUTOMATED-VERIFIED | Physical microphone/speaker acceptance required |
| First run | Platform risk disclosed | Render Free cold-start notice | BLOCKED measurement | Three cold and three warm measurements needed |
| Agents/scheduler | Restricted/bounded | Existing agent and scheduler tests | AUTOMATED-VERIFIED | Persistent free-tier scheduling is not guaranteed |
| Affordia | Synthetic isolation | Tenant contract tests | AUTOMATED-VERIFIED | No real patient data or public pilot |

