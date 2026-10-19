# OOF Website Security Operations

## Production edge configuration

The current static site is served by GitHub Pages. Configure an authorized edge proxy or migrate the static site to a headers-capable host before claiming site-wide header or DDoS coverage.

Apply these response headers to public HTML, JavaScript, CSS, JSON, SVG, and other public assets after validating the site in a staging configuration:

```text
Strict-Transport-Security: max-age=31536000
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: accelerometer=(), camera=(), geolocation=(), microphone=(), payment=(), usb=()
Cross-Origin-Opener-Policy: same-origin
Content-Security-Policy: default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; object-src 'none'
```

The static pages include inline scripts and styles. A production CSP rollout must therefore be tested with report-only mode first and use nonces or hashes where required; do not deploy a stricter script policy blindly.

Configure edge request-rate and concurrency controls for dynamic services, not for public static methodology pages. Use behavior and endpoint cost, not User-Agent, nationality, or country. Return HTTP 429 with `Retry-After` for the protected dynamic routes. Keep `robots.txt`, `sitemap.xml`, canonical pages, and intended retrieval files reachable.

## LaRA deployment settings

- Set `NODE_ENV=production` and keep secrets only in the Render environment.
- Set a strong `LARA_ADMIN_TOKEN`; do not expose it in the browser, logs, or repository.
- Leave `LARA_TRUST_PROXY=false` unless the deployed service has one trusted ingress that rewrites forwarding headers. When confirmed, set it to `true` so limits use the forwarded client address.
- Start with `LARA_RATE_LIMIT_PER_MINUTE=20`, `LARA_CHAT_CONCURRENCY=4`, and `LARA_REQUEST_TIMEOUT_MS=15000`. Adjust only from observed service behavior.
- Keep allowed browser origins restricted to the two OOF HTTPS origins using `LARA_ALLOWED_ORIGINS`.

## Monitoring and retention

Review service availability, 429 events, repeated failed administrative requests, malformed requests, server errors, and unexpected changes to public content. Store only the minimum metadata needed for operations. Do not retain raw chats, credentials, authorization headers, or unnecessary personal data in operational logs. Restrict access to administrators and apply a documented retention period.

## Content integrity and recovery

- Use reviewed commits and required CI checks before publishing changes.
- Preserve GitHub repository history and a separate periodic backup of repository releases and configuration.
- Test restoration into an isolated environment before relying on a backup.
- Treat canonical methodology content as immutable unless an authorized content change is reviewed and published through the normal repository workflow.

## Incident response

1. Record the time, affected route, observed behavior, and minimal non-sensitive evidence.
2. Limit or disable only the affected dynamic endpoint; do not block the public methodology site broadly.
3. Preserve relevant logs under restricted access.
4. Correct the configuration or code in a reviewed change, then run the security baseline and normal regression tests.
5. Verify crawler access, sitemap access, canonical URLs, and public methodology pages after remediation.
6. Document the outcome and any remaining risk.
