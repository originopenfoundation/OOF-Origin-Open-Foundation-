#!/usr/bin/env python3
"""Generate indexable static entry routes for the incident intelligence UI."""

from pathlib import Path
import html
import json
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ai-incidents" / "index.html"
ROUTES = {
    "map": "Global AI Incident Map",
    "latest": "Latest AI Incidents",
    "critical": "Critical AI Incidents",
    "architectures": "AI Incident Architecture Intelligence",
    "industries": "AI Incidents by Industry",
    "countries": "AI Incidents by Country",
    "trends": "AI Incident Trends",
    "stress-tests": "OOF® Architecture Stress Tests",
    "methodology": "OOF® AI Incident Intelligence Methodology",
}


def text(value) -> str:
    return html.escape(str(value or ""), quote=True)


def public_slug(record: dict) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", f"{record.get('id', '')}-{record.get('title', '')}".casefold()).strip("-")
    return raw[:88].rstrip("-")


def list_markup(title: str, values: list) -> str:
    if not values:
        return ""
    return f'<section><h2>{text(title)}</h2><ul>{"".join(f"<li>{text(value)}</li>" for value in values)}</ul></section>'


def architecture_markup(analysis: dict) -> str:
    architecture = analysis.get("architectureAnalysis") or {}
    values = [architecture.get("primaryArchitecture"), *(architecture.get("contributingArchitectures") or [])]
    cards = []
    for item in filter(None, values):
        label = text(item.get("label") or item.get("architectureId", "").upper())
        href = text(item.get("canonicalUrl"))
        heading = f'<a href="{href}">{label}</a>' if href else label
        references = []
        for reference in item.get("relevantStandardsModules") or []:
            reference_label = f'{"Parent Standard" if reference.get("artifactType") == "ParentStandard" else "Core Module"}: {reference.get("name")}'
            reference_url = text(reference.get("canonicalUrl"))
            references.append(f'<li><a href="{reference_url}">{text(reference_label)}</a></li>' if reference_url else f'<li>{text(reference_label)}</li>')
        methodology = (
            f'<p><b>Canonical methodology ({text(item.get("methodologyDepth") or "verified")}):</b></p><ul>{"".join(references)}</ul>'
            if references else
            '<p class="oof-methodology-withheld">Deeper methodology is withheld because the available evidence does not justify a Parent Standard or Core Module.</p>'
            if item.get("methodologyDepth") == "Architecture" else ""
        )
        cards.append(
            '<article class="oof-incident-detail-architecture">'
            f'<h3>{heading}</h3><p class="oof-detail-role">{text(item.get("role"))} architecture</p>'
            f'<p>{text(item.get("whyItMattersHere") or item.get("reasonForRelevance"))}</p>'
            f'<p><b>Governance focus:</b> {text(item.get("governanceFocus"))}</p>{methodology}</article>'
        )
    if not cards:
        return ""
    return f'<section><h2>Architecture intelligence</h2><div class="oof-incident-detail-architectures">{"".join(cards)}</div></section>'


def build_incident_detail(record: dict) -> str:
    analysis = record.get("automatedAnalysis") or {}
    evidence = analysis.get("incidentEvidence") or {}
    severity = (analysis.get("severityAssessment") or {}).get("level") or record.get("severity") or "Insufficient evidence"
    canonical = f"https://originopenfoundation.org/ai-incidents/incidents/{public_slug(record)}/"
    description = re.sub(r"\s+", " ", str(record.get("summary") or record["title"])).strip()[:155]
    source = (record.get("sources") or [{}])[0]
    source_markup = ""
    if source.get("url"):
        source_markup = f'<p><a href="{text(source["url"])}" rel="noopener noreferrer">View source record from {text(source.get("publisher") or "the identified publisher")}</a></p>'
    disclosure = analysis.get("assessmentDisclosure") or "No automated governance assessment is available for this record."
    json_ld = {
        "@context": "https://schema.org", "@type": "Report", "url": canonical,
        "headline": record["title"], "description": description, "inLanguage": "en",
        "publisher": {"@id": "https://originopenfoundation.org/#organization"},
        "datePublished": record.get("reportedAt"),
        "about": ["AI incident intelligence", record.get("country"), record.get("industry")],
        "isBasedOn": source.get("url"),
        "breadcrumb": {
            "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "OOF®", "item": "https://originopenfoundation.org/"},
                {"@type": "ListItem", "position": 2, "name": "AI Incident Intelligence", "item": "https://originopenfoundation.org/ai-incidents/"},
                {"@type": "ListItem", "position": 3, "name": record["title"], "item": canonical},
            ],
        },
    }
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{text(record['title'])} | OOF® AI Incident Intelligence</title>
<meta name="description" content="{text(description)}" /><link rel="canonical" href="{canonical}" />
<link rel="stylesheet" href="/style.css" /><link rel="stylesheet" href="/assets/css/oof-ai-incidents.css?v=6" />
<script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False).replace('</', '<\\/')}</script></head>
<body><div id="header"></div><main class="oof-incident-app oof-incident-detail"><article>
<nav class="oof-detail-breadcrumb" aria-label="Breadcrumb"><a href="/index.html">OOF®</a><span>/</span><a href="/ai-incidents/">AI Incident Intelligence</a><span>/</span><span aria-current="page">Incident record</span></nav>
<header><p class="oof-incident-id">{text(record['id'])}</p><h1>{text(record['title'])}</h1><p class="oof-detail-lede">{text(record.get('summary') or 'No public summary is available.')}</p></header>
<dl class="oof-incident-detail-facts"><div><dt>Event date</dt><dd>{text((record.get('occurredAt') or record.get('reportedAt') or 'Unknown')[:10])}</dd></div><div><dt>Country</dt><dd>{text(record.get('country') or 'Location not specified')}</dd></div><div><dt>Severity</dt><dd>{text(severity)}</dd></div><div><dt>Evidence state</dt><dd>{text(evidence.get('evidenceState') or 'Insufficient evidence')}</dd></div></dl>
<section class="oof-detail-disclosure"><h2>Assessment status</h2><p>{text(disclosure)}</p>{source_markup}</section>
{list_markup('Known facts from the incident record', evidence.get('knownFacts') or [])}
{list_markup('Reported claims', evidence.get('reportedClaims') or [])}
{list_markup('Material unknowns', evidence.get('materialUnknowns') or [])}
<section><h2>Primary governance problem</h2><p>{text(analysis.get('primaryGovernanceProblem') or 'The available evidence does not support a more specific preliminary governance interpretation.')}</p></section>
{architecture_markup(analysis)}
{list_markup('Preliminary governance questions', analysis.get('governanceQuestions') or [])}
{list_markup('Evidence gaps and limitations', analysis.get('evidenceGaps') or analysis.get('uncertainties') or [])}
<p><a href="/ai-incidents/incidents/">Return to the public incident index</a></p>
</article></main><div id="footer"></div><script src="/header.js"></script><script>
fetch("/header.html").then(r=>r.text()).then(v=>{{document.getElementById("header").innerHTML=v;if(window.normalizePageLinks)window.normalizePageLinks();}});
fetch("/footer.html").then(r=>r.text()).then(v=>{{document.getElementById("footer").innerHTML=v;if(window.normalizePageLinks)window.normalizePageLinks();}});
</script></body></html>'''


def build_incident_directory(records: list[dict]) -> str:
    rows = []
    for record in sorted(records, key=lambda item: (str(item.get("occurredAt") or item.get("reportedAt") or ""), item["id"]), reverse=True):
        date = str(record.get("occurredAt") or record.get("reportedAt") or "Unknown")[:10]
        rows.append(
            '<li><a href="/ai-incidents/incidents/' + text(public_slug(record)) + '/">' + text(record["title"]) + '</a>'
            f'<span>{text(date)} · {text(record.get("country") or "Location not specified")}</span></li>'
        )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Public AI Incident Index | OOF®</title><meta name="description" content="Index of public AI incident records monitored by OOF® Global AI Incident Intelligence™." />
<link rel="canonical" href="https://originopenfoundation.org/ai-incidents/incidents/" /><link rel="stylesheet" href="/style.css" /><link rel="stylesheet" href="/assets/css/oof-ai-incidents.css?v=6" /></head>
<body><div id="header"></div><main class="oof-incident-app oof-incident-directory"><article><nav class="oof-detail-breadcrumb" aria-label="Breadcrumb"><a href="/index.html">OOF®</a><span>/</span><a href="/ai-incidents/">AI Incident Intelligence</a><span>/</span><span aria-current="page">Incident Index</span></nav>
<header><h1>Public AI Incident Index</h1><p>All {len(records)} public records, ordered by the best available event date. Inclusion does not constitute an OOF® Approved Assessment.</p></header>
<ol class="oof-incident-directory-list">{"".join(rows)}</ol></article></main><div id="footer"></div><script src="/header.js"></script><script>
fetch("/header.html").then(r=>r.text()).then(v=>{{document.getElementById("header").innerHTML=v;if(window.normalizePageLinks)window.normalizePageLinks();}});fetch("/footer.html").then(r=>r.text()).then(v=>{{document.getElementById("footer").innerHTML=v;if(window.normalizePageLinks)window.normalizePageLinks();}});
</script></body></html>'''


def build() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    for route, title in ROUTES.items():
        page = re.sub(r'<html lang="en" data-ai-incidents-view="[^"]+">', f'<html lang="en" data-ai-incidents-view="{route}">', source, count=1)
        page = re.sub(r"<title>.*?</title>", f"<title>{title} | OOF®</title>", page, count=1)
        page = re.sub(
            r'<link rel="canonical" href="[^"]+" />',
            f'<link rel="canonical" href="https://originopenfoundation.org/ai-incidents/{route}/" />',
            page,
            count=1,
        )
        target = ROOT / "ai-incidents" / route / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
    payload = json.loads((ROOT / "data" / "ai-incidents" / "incident-store.json").read_text(encoding="utf-8"))
    analyses = json.loads((ROOT / "data" / "ai-incidents" / "analysis-store.json").read_text(encoding="utf-8"))
    latest = {}
    for assessment in analyses.get("assessments", []):
        incident_id = assessment.get("incidentId")
        if incident_id and assessment.get("analysisVersion", 0) > latest.get(incident_id, {}).get("analysisVersion", 0):
            latest[incident_id] = assessment
    detail_count = 0
    public_records = []
    for record in payload.get("incidents", []):
        if record.get("publicationStatus") not in {"Monitored", "Published"}:
            continue
        record = dict(record)
        record["automatedAnalysis"] = latest.get(record["id"])
        public_records.append(record)
        target = ROOT / "ai-incidents" / "incidents" / public_slug(record) / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(build_incident_detail(record), encoding="utf-8")
        detail_count += 1
    directory = ROOT / "ai-incidents" / "incidents" / "index.html"
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.write_text(build_incident_directory(public_records), encoding="utf-8")
    expected_directories = {public_slug(record) for record in public_records}
    for child in directory.parent.iterdir():
        if not child.is_dir() or child.name in expected_directories:
            continue
        for generated_file in child.iterdir():
            if generated_file.is_file():
                generated_file.unlink()
        child.rmdir()
    print(f"Generated {len(ROUTES)} AI incident routes, the incident index, and {detail_count} incident detail pages.")


if __name__ == "__main__":
    build()
