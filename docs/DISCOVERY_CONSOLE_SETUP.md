# Search Console, Bing and IndexNow setup

This repository publishes one XML sitemap at:

`https://originopenfoundation.org/sitemap.xml`

## Google Search Console

1. Sign in with the Google account that should own the property.
2. Add the Domain property `originopenfoundation.org`.
3. Select **Verify** in Search Console. Public DNS already contains a Google verification TXT value; it will validate the property when the signed-in account is the account that issued it.
4. If Google issues a different TXT value, add it alongside the existing TXT records in the authoritative DNS zone. Do not replace the existing SPF or Google verification values.
5. Open **Sitemaps** and submit `https://originopenfoundation.org/sitemap.xml`.

Use a Domain property rather than a URL-prefix property so `www`, HTTP, HTTPS and all verified subdomains are covered by the same ownership record.

## Bing Webmaster Tools

1. Sign in to Bing Webmaster Tools with the designated owner account.
2. Add `https://originopenfoundation.org/` as the site, or import the already verified Google Search Console property.
3. If importing is unavailable, verify ownership with the DNS record supplied by Bing.
4. Open **Sitemaps** and submit `https://originopenfoundation.org/sitemap.xml`.

## IndexNow

The deployed IndexNow verification file is:

`https://originopenfoundation.org/6ff7528f813141d19583be3c43890829.txt`

The `Submit IndexNow after Pages deployment` GitHub Actions workflow sends the current sitemap URL list to `https://api.indexnow.org/indexnow` after a successful production Pages deployment from `main1`. It verifies locally that the public key file is present and contains the matching key before making the request. A missing or altered key file makes the workflow fail instead of silently reporting a successful submission.

The submission uses the canonical URLs from `sitemap.xml` and therefore covers the same complete, crawlable public URL set as the sitemap.

After this change is deployed, confirm the `Submit published sitemap URLs to IndexNow` step reports `HTTP 200` or `HTTP 202`. It may also be started manually from **Actions -> Submit IndexNow after Pages deployment -> Run workflow**.

## Ownership boundary

Google Search Console and Bing Webmaster Tools verification records are issued only after an authenticated owner adds the domain inside those services. This repository cannot generate or validate those account-bound records. Once a site owner completes the two verification steps above, sitemap submission can be confirmed directly in each console.
