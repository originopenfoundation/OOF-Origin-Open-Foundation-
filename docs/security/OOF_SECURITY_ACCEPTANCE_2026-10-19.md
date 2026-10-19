# OOF Security Baseline Acceptance

Date: 2026-10-19

## Implemented and verified

- Public discovery remains allowed in `robots.txt`; live checks confirmed the robots file, sitemap, canonical sample pages, and intended crawler requests return successfully.
- LaRA now enforces bounded per-route request limits without inspecting crawler user agents or geolocation. Over-limit responses carry HTTP 429 and `Retry-After`.
- LaRA limits concurrent chat work, request body size, request duration, header size, and requests per keep-alive socket.
- LaRA emits security headers for its responses and keeps administrative routes restricted to the server host plus bearer authentication.
- Private runtime files remain excluded from Git and are denied by the local static server.
- A security disclosure policy, `security.txt`, source validator, focused unit tests, and a read-only GitHub Actions security-baseline workflow are included.

## Verification commands and results

```text
python tools/validate_security_baseline.py
node --test tests/lara/*.test.js
python tools/audit_live_discovery.py --base-url https://originopenfoundation.org/
```

Results on 2026-10-19: security baseline passed; 41 LaRA tests passed; live discovery audit completed 15 checks with zero errors. A local HTTP verification confirmed security headers on the LaRA status route, a 403 response for an unapproved origin, and a 404 response for `.env`.

## Not verified by repository tests

- Edge WAF, DDoS controls, and static-site headers, because the public static site is presently delivered by GitHub Pages and those controls require authorized hosting or edge configuration.
- Render production environment variables, ingress trust settings, log retention, administrator access, and backup restoration.
- GitHub organization branch protection, secret scanning, backup policy, and required-review settings.

## Production readiness

The repository-owned application baseline is ready for review. Production security is not fully accepted until the P1 edge-header and DDoS controls, plus the Render and GitHub administrator checks, are applied and verified as described in the operations guide.
