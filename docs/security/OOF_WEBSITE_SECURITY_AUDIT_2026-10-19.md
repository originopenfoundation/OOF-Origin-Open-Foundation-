# OOF Website Security and Bot Protection Audit

Date: 2026-10-19

## Scope and evidence

This review examined the repository, current production response headers, CI workflows, discovery files, and the LaRA service source. It did not perform load testing, credential rotation, administrator changes, or infrastructure changes.

## Confirmed architecture

- The public domain currently returns `Server: GitHub.com`, indicating GitHub Pages delivery for the static site.
- `CNAME` defines `originopenfoundation.org`.
- The static site has no server-side routes, authentication system, or repository-defined API.
- The LaRA browser client is configured to call a separate Render service. Its public endpoints are limited to status, chat, enquiry, identity, and session operations; administrative routes require a local server connection and bearer token.
- GitHub Actions rebuild and validate public discovery, AI incident, registry, and localization projections.

## Existing controls verified

- `robots.txt` allows public discovery and exposes the sitemap.
- Production `robots.txt` and `sitemap.xml` return HTTP 200.
- LaRA uses exact-origin CORS, HTTP-only strict-same-site session cookies, bounded request bodies, local-only administrative routing, timing-safe admin-token comparison, and private runtime-state exclusions.
- CI uses least-privilege `contents: read` permissions except workflows that need to publish generated public data.

## Findings

### P1: static-site response headers are not configurable in this repository

The production static response lacks a Content Security Policy, frame protection, permissions policy, and HSTS. GitHub Pages does not apply arbitrary repository header files. This must be resolved at an authorized edge or hosting layer; the required configuration is documented in the operational guide. No claim of production DDoS protection is made by this change.

### P1: Render production settings require administrator verification

The LaRA backend can enforce the repository protections, but its deployed environment values and Render service controls cannot be read from this repository. Before enabling `LARA_TRUST_PROXY=true`, an administrator must confirm that Render is the only direct ingress and that it overwrites inbound forwarding headers.

### P2: abuse controls previously lacked per-route Retry-After behavior and bounded limiter storage

This remediation adds bounded, route-specific in-memory limits, concurrency control for chat work, HTTP 429 with `Retry-After`, body-size validation before buffering, and server request/header/socket limits. These are application controls, not a replacement for edge DDoS protection.

### P2: security monitoring remains infrastructure-dependent

The application records limited operational events, but centralized retention, alerting, and access control are not verified here. The operational guide identifies the minimum review and retention policy.

### P3: no signed release or branch-protection evidence was available in the repository

Generated-site consistency is checked in CI. Repository branch protection, required reviews, secret scanning, and backup restoration must be verified in GitHub organization settings.

## Remediation applied in this repository

- Added `/.well-known/security.txt` and `SECURITY.md` for a public disclosure path.
- Added route-specific rate limits for LaRA chat, enquiries, identity operations, and session reset, without user-agent or geographic blocking.
- Added bounded limiter storage, request-size checks before allocation, an explicit chat concurrency ceiling, `Retry-After` for HTTP 429 responses, and HTTP request/header/keep-alive limits.
- Added backend security headers, including frame, content-type, referrer, permissions, opener, CSP, and production HSTS controls.
- Added automated source-level security baseline validation and focused unit tests.
- Added an operational security guide that separates verified application controls from administrator-owned production controls.

## Remaining production actions

See [OOF Website Security Operations](OOF_WEBSITE_SECURITY_OPERATIONS.md). The P1 edge-header and DDoS controls are not complete until an authorized production administrator applies and verifies them.
