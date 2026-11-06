# LaRA v2.4 — review package

This folder contains the complete prepared candidate as a Git bundle and the implementation audit. It does not activate the bundled data in the source tree or deploy to Render.

- Published implementation basis: `42cabb23cd022dc8744959d62ef8d832b1cf985c`.
- Bundled complete candidate: `207535f60e866973ac7f39a6c1f1def5052a733c`.
- Candidate tree: `dad245fd54014b3fb2f3758cf99de33262a51a24`.
- Bundle SHA-256: `98136bbe09e8e7aae652d0e65b4e4b07120e501458367d3c8872eff4be249edc`.
- Audit SHA-256: `e95676422e193aa8d409f88f535f90f91e0fcdbe1fb52294e5d8e2364b9cce16`.

The bundle was verified with `git bundle verify`. It includes the pending generated Knowledge refresh and a new automated incident assessment while preserving old history. It contains no ignored credentials or private test transcripts. The PDF describes the state before this archive upload.

## Import into an existing clone

Fetch the published feature branch first, download `LaRA-v2.4-review.bundle`, and run:

```sh
git fetch origin codex/lara-groq-v21
git bundle verify LaRA-v2.4-review.bundle
git fetch ./LaRA-v2.4-review.bundle HEAD:refs/heads/review/lara-v24-complete
```

The bundle requires the already published commits `42cabb23cd022dc8744959d62ef8d832b1cf985c`, `02ff4d3732ad6e46b99963bd6cfe0c6fe76ea62d`, and `6d456f7fdbd2f98a3e1482792c13713c52f0361d`.

## Remaining acceptance issues

Local validation: 191 Node tests, 128 Python tests, 22 HTTP cases, and memory smoke passed. Published CI remains incomplete: source-commit provenance and historical V1/V2 references to draft RPAS need remediation. The new local assessment fixes the latest interpretation, but does not resolve validation of all historical assessments. Full multilingual/model acceptance and the A/B/C benchmark remain incomplete after a Groq quota block. Prototype acceptance and production readiness are false.

Direct push of the full candidate currently needs local Git authentication. The GitHub blob API rejected the approximately 62 MB history file. The compressed Git bundle allows the complete candidate to be stored and reviewed here without changing the application data format, canonical authority or history. Keep PR draft and unmerged.
