# LaRA v2.7.1 developer handoffs

## LARA-V271-GOV-01 - canonical public authorization
Capability: public generation. Error: `public_communication_scopes=[]`; runtime remains report-only. Required action: the authorized OOF governance owner must create, approve, publish and index `OOF-KO-LARA-PUBLIC-COMMUNICATION` using the existing canonical schema and correct policy digest. Verification: live status lists scopes and an invalid digest fails closed. Dependent public generation remains stopped.

## LARA-V271-GROQ-02 - authorized isolated conversation acceptance
Capability: real multi-turn Groq. Error: configured provider has not been integration-verified. Required action: run 10 synthetic five-turn conversations through an authorized isolated route with per-message provider consent. Record only status, latency, source correctness, consent and trace IDs. Verification: no secret or message content in the evidence.

## LARA-V271-VOICE-03 - physical audio acceptance
Capability: STT/TTS. Error: automated browser has no approved physical microphone/speaker test. Required action: test Chrome/Edge plus one independent engine on desktop and one mobile device, for Slovak, English, German, Mandarin Chinese and Japanese. Verification: device/browser/version, permission result, transcription, playback, pause/stop and fallback observations.

## LARA-V271-PERF-04 - cold/warm measurement
Capability: first-run latency. Error: no three-cold/three-warm production measurement series. Required action: collect timing data after Render inactivity and for consecutive requests. Verification: separate connection/startup/retrieval/provider/render times and identify any application-level defect. No paid plan change is authorized.

