# LaRA Knowledge Navigator and lifecycle reconciliation

Select **Knowledge Navigator** in the existing widget and describe the operational problem. The same chat endpoint accepts `mode: "navigator"`. Its `navigation` field includes resolved object IDs, source URLs and hashes, lifecycle and authority states, deterministic ranking reasons, and the next step. It uses the shared Knowledge Layer, without a second database or model call.

Ranking weights are inspectable in `lara/knowledge/navigator.js`: title matches, structured metadata, declared parent/architecture identity, and exact acronyms. Specific domain anchors constrain broad terms such as control. Results remain evidence-based suggestions, not approvals. Sources are taken only from the existing hash-verified read-only view; disabled, missing, changed, quarantined and withdrawn resources cannot become navigation recommendations. Linguistic expansions are search vocabulary, not methodology membership.

The structured architecture index supports `data-oof-status` on architecture headings. Explicit non-final states without approved membership produce a non-blocking `PENDING` validation result. Published visibility is distinct from approval. Unknown states and false canonical membership remain blocking. Existing approval, identity, duplicate review, citation and REPORT_ONLY gates remain in force.

SLGA is explicitly `in-progress` in its existing source. It remains discoverable as supporting material; it is absent from the approved architecture list. Source-backed children and relationships inherit the pending boundary. Direct and follow-up lifecycle questions use the verified status rather than free-form model inference. No missing standards, modules or approvals are generated.

Reproduce offline checks:

```sh
node --test tests/lara/*.test.js
python -m unittest discover -s tests -p test_architecture_lifecycle.py -v
python -m unittest discover -s tests -p test_knowledge_infrastructure.py -v
python tools/validate_knowledge_infrastructure.py
node tools/lara_navigation_acceptance.cjs navigation-evidence.json
```

The HTTP acceptance probe starts a private loopback server with provider `none`, verifies navigation URLs through the actual server, tests SLGA continuity and session isolation, and includes a clearly labelled conflict fixture. It refuses a checkout containing `.env`. Fixture and deterministic results are never live-model acceptance evidence.

Live Groq probes require separate owner authorization for the private test environment and approved public/synthetic inputs. Keep the existing free-tier-only provider/model policy and resume checkpoints. Do not read credentials, enable billing, merge the PR or deploy as part of offline acceptance. Public communication approval is a separate governed decision.
