#!/usr/bin/env python3
"""Generate indexable static entry routes for the incident intelligence UI."""

from pathlib import Path
import argparse
import html
import json
import re

import ai_incidents
import build_ai_compatibility as discovery


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_BLOCK_RE = re.compile(r"<!-- OOF AI DISCOVERY START -->.*?<!-- OOF AI DISCOVERY END -->\s*", re.S)
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


def generated_page_signature(value: str) -> tuple[str, tuple[str, ...]]:
    """Compare generated body content while allowing discovery metadata injection."""
    value = DISCOVERY_BLOCK_RE.sub("", value)
    value = re.sub(r"<head\b.*?</head>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", value, flags=re.I | re.S)
    links = tuple(re.findall(r"<a\b[^>]*\bhref=[\"']([^\"']+)", value, flags=re.I))
    visible = re.sub(r"<[^>]+>", " ", value)
    visible = re.sub(r"\s+", " ", html.unescape(visible)).strip()
    return visible, links


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


def confidence_markup(analysis: dict) -> str:
    dimensions = analysis.get("confidenceDimensions") or {}
    labels = {
        "sourceCorroboration": "Source corroboration",
        "extractionCompleteness": "Extraction completeness",
        "methodologicalAssignment": "Methodological assignment confidence",
    }
    items = []
    for key, label in labels.items():
        value = dimensions.get(key) or {}
        if not value:
            continue
        items.append(
            '<div><dt>' + text(label) + '</dt><dd>' + text(value.get("level") or "Not assessed") + '</dd>'
            '<p>' + text(value.get("disclosure")) + '</p></div>'
        )
    if not items:
        return ""
    return '<section><h2>Assessment confidence dimensions</h2><dl class="oof-confidence-dimensions">' + "".join(items) + '</dl></section>'


def source_evidence_markup(record: dict, analysis: dict) -> str:
    snapshot = analysis.get("evidenceSnapshot") or {}
    sources = snapshot.get("sources") or record.get("sources") or []
    rows = []
    for source in sources:
        url = text(source.get("url"))
        publisher = text(source.get("publisher") or "Identified public source")
        heading = f'<a href="{url}" rel="noopener noreferrer">{publisher}</a>' if url else publisher
        rows.append(
            f'<li>{heading}<span>{text(source.get("authority") or source.get("sourceType") or "Source type not classified")} · '
            f'{text(source.get("publicationTime") or source.get("publicationDate") or "Publication date not specified")}</span></li>'
        )
    status = text(snapshot.get("publicEvidenceStatus") or "Evidence Insufficient")
    return f'<section><h2>Evidence and sources</h2><p><b>Evidence status:</b> {status}</p><ul class="oof-evidence-sources">{"".join(rows)}</ul></section>'


def report_markup(analysis: dict) -> str:
    report = analysis.get("oofIncidentReport") or {}
    source_url = text(report.get("sourceUrl"))
    source_name = text(report.get("sourceAttribution") or "Identified public source")
    source = f'<a href="{source_url}" rel="noopener noreferrer">{source_name}</a>' if source_url else source_name
    return (
        '<section class="oof-incident-report"><h2>Original OOF® Incident Report</h2>'
        f'<p>{text(report.get("report") or "No structured OOF incident report is available for this record.")}</p>'
        f'<p><b>Original incident source:</b> {source}</p>'
        f'<p class="oof-evidence-limitation">{text(report.get("uncertaintyStatement"))}</p></section>'
    )


def failure_classification_markup(analysis: dict) -> str:
    classification = analysis.get("systemFailureClassification") or {}
    components = classification.get("components") or []
    if components:
        entries = "".join(
            '<article><h3>' + text(component.get("label")) + '</h3>'
            '<p><b>Evidence signals:</b> ' + text(", ".join(component.get("matchedTerms") or []) or "Not specified") + '</p>'
            '<p>' + text(component.get("rationale")) + '</p></article>'
            for component in components
        )
    else:
        entries = '<p>No system component is sufficiently indicated by the available record.</p>'
    return (
        '<section><h2>Relevant system components and failure mechanisms</h2>'
        f'<p><b>Classification state:</b> {text(classification.get("status") or "UNRESOLVED")}</p>'
        f'<div class="oof-system-components">{entries}</div>'
        f'<p class="oof-evidence-limitation">{text(classification.get("limitation"))}</p></section>'
    )


def external_mapping_markup(analysis: dict) -> str:
    mapping = analysis.get("externalTechnicalMappings") or {}
    items = mapping.get("mappings") or []
    if items:
        rows = []
        for item in items:
            url = text(item.get("canonicalUrl"))
            label = text(f'{item.get("framework")} {item.get("identifier")}')
            heading = f'<a href="{url}" rel="noopener noreferrer">{label}</a>' if url else label
            rows.append(f'<li>{heading}<p>{text(item.get("rationale"))}</p></li>')
        body = '<ul class="oof-external-mappings">' + "".join(rows) + '</ul>'
    else:
        body = '<p>No external technical identifier is asserted for this incident.</p>'
    return '<section><h2>External technical mappings</h2>' + body + f'<p class="oof-evidence-limitation">{text(mapping.get("limitation"))}</p></section>'


def prevention_markup(analysis: dict) -> str:
    guidance = analysis.get("preventionGuidance") or {}
    if not guidance:
        return '<section><h2>Prevention guidance</h2><p class="oof-evidence-limitation">Case-specific prevention guidance is withheld because the publication gate did not pass.</p></section>'
    methodology = []
    for item in guidance.get("relevantMethodology") or []:
        label = text(item.get("name") or item.get("objectId"))
        url = text(item.get("canonicalUrl"))
        methodology.append(f'<a href="{url}">{label}</a>' if url else label)
    applicability = guidance.get("couldThisHappenToYourSystem") or {}
    implementation = guidance.get("whatShouldBeImplemented") or {}
    verification = guidance.get("howCanProtectionBeVerified") or {}
    cards = [
        ("Could This Happen to Your System?", [
            ("Applicability", applicability.get("applicability")),
            ("Known versus inferred", applicability.get("knownVsInferred")),
        ]),
        ("What Should Be Implemented?", [
            ("Control objective", implementation.get("controlObjective")),
            ("Governance boundary", implementation.get("governanceBoundary")),
            ("Protective mechanism", implementation.get("protectiveMechanism")),
            ("Expected protective behavior", implementation.get("expectedBehavior")),
        ]),
        ("How Can Protection Be Verified?", [
            ("Test objective", verification.get("testObjective")),
            ("Prerequisite", verification.get("prerequisite")),
            ("Test action", verification.get("testAction")),
            ("Expected safe behavior", verification.get("expectedSafeBehavior")),
            ("Evidence to retain", verification.get("evidenceToRetain")),
            ("Failure condition", verification.get("failureCondition")),
        ]),
    ]
    markup = []
    for heading, entries in cards:
        rows = "".join(f'<p><b>{text(label)}:</b> {text(value)}</p>' for label, value in entries if value)
        markup.append(f'<article><h3>{text(heading)}</h3>{rows}</article>')
    methodology_text = ", ".join(methodology) if methodology else "Methodology depth is not yet justified by the evidence."
    return (
        f'<section><h2>Prevention guidance</h2><p><b>Guidance state:</b> {text(guidance.get("status") or "EVIDENCE_LIMITED")}</p>'
        f'<div class="oof-prevention-grid">{"".join(markup)}</div>'
        f'<p><b>Relevant OOF® methodology:</b> {methodology_text}</p>'
        f'<p class="oof-evidence-limitation">{text(guidance.get("evidenceLimitation"))}</p></section>'
    )


def commercial_markup() -> str:
    return (
        '<section class="oof-commercial-cta"><h2>Need a Complete Prevention Architecture?</h2>'
        '<p>OOF® Architecture &amp; Prevention Engineering provides system-specific depth beyond this public, evidence-bounded guidance.</p>'
        '<ul><li>System-specific risk and architecture assessment</li><li>Architecture blueprint and implementation framework</li>'
        '<li>Verification and acceptance-testing framework</li><li>Governance integration and documentation</li></ul>'
        '<p>This service does not certify compliance or eliminate all risk.</p><a href="/Contact.html">Discuss Architecture &amp; Prevention Engineering</a></section>'
    )


def checklist_markup(analysis: dict) -> str:
    items = analysis.get("practicalChecklist") or []
    if not items:
        return ""
    rows = "".join(f'<li><b>{text(item.get("item"))}</b>{text(item.get("verification"))}</li>' for item in items)
    return f'<section><h2>Practical verification checklist</h2><ol class="oof-checklist">{rows}</ol></section>'


def related_markup(records: list[dict]) -> str:
    if not records:
        return ""
    cards = []
    for record in records[:4]:
        analysis = record.get("automatedAnalysis") or {}
        status = (analysis.get("evidenceSnapshot") or {}).get("publicEvidenceStatus") or "Evidence Insufficient"
        cards.append(
            '<article><h3><a href="/ai-incidents/incidents/' + text(public_slug(record)) + '/">' + text(record.get("title")) + '</a></h3>'
            f'<p>{text(record.get("country") or "Location not specified")} · {text(status)}</p></article>'
        )
    return f'<section><h2>Related governance failure patterns</h2><div class="oof-related-incidents">{"".join(cards)}</div></section>'


def history_markup(history: list[dict]) -> str:
    if not history:
        return ""
    rows = [f'Version {item.get("analysisVersion")} · {item.get("engineVersion")} · {item.get("createdAt")} · {item.get("reassessmentReason") or "Assessment update"}' for item in reversed(history)]
    return list_markup("Assessment history", rows)


def build_incident_detail(record: dict, related: list[dict] | None = None, history: list[dict] | None = None) -> str:
    analysis = record.get("automatedAnalysis") or {}
    evidence = analysis.get("incidentEvidence") or {}
    severity = (analysis.get("severityAssessment") or {}).get("level") or record.get("severity") or "Insufficient evidence"
    canonical = f"https://originopenfoundation.org/ai-incidents/incidents/{public_slug(record)}/"
    description = re.sub(r"\s+", " ", str(record.get("summary") or record["title"])).strip()[:155]
    source = (record.get("sources") or [{}])[0]
    report = analysis.get("oofIncidentReport") or {}
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
<dl class="oof-incident-detail-facts"><div><dt>Event date</dt><dd>{text((record.get('occurredAt') or record.get('reportedAt') or 'Unknown')[:10])}</dd></div><div><dt>Country</dt><dd>{text(record.get('country') or 'Location not specified')}</dd></div><div><dt>Severity</dt><dd>{text(severity)}</dd></div><div><dt>Evidence status</dt><dd>{text((analysis.get('evidenceSnapshot') or {}).get('publicEvidenceStatus') or 'Evidence Insufficient')}</dd></div></dl>
<section class="oof-detail-disclosure"><h2>Assessment status</h2><p>{text(disclosure)}</p><p>{text(report.get('uncertaintyStatement'))}</p></section>
{report_markup(analysis)}
{source_evidence_markup(record, analysis)}
<section><h2>Incident overview</h2><p>{text(record.get('summary') or 'No public source summary is available.')}</p></section>
<section><h2>AI involvement</h2><p><b>System:</b> {text(record.get('system') or 'Not established')}</p><p><b>Technology:</b> {text(record.get('technology') or record.get('aiSystemType') or 'Not established')}</p></section>
{confidence_markup(analysis)}
{list_markup('Known facts from the incident record', evidence.get('knownFacts') or [])}
{list_markup('Reported claims', evidence.get('reportedClaims') or [])}
{list_markup('Material unknowns', evidence.get('materialUnknowns') or [])}
<section><h2>Primary governance problem</h2><p>{text(analysis.get('primaryGovernanceProblem') or 'The available evidence does not support a more specific preliminary governance interpretation.')}</p></section>
{architecture_markup(analysis)}
<section><h2>Failure mechanism</h2><p>{text(analysis.get('incidentGovernanceInsight') or 'Available evidence does not yet support a case-specific failure mechanism.')}</p></section>
{failure_classification_markup(analysis)}
{external_mapping_markup(analysis)}
{prevention_markup(analysis)}
{checklist_markup(analysis)}
{commercial_markup()}
{related_markup(related or [])}
{list_markup('Preliminary governance questions', analysis.get('governanceQuestions') or [])}
{list_markup('Evidence gaps and limitations', analysis.get('evidenceGaps') or analysis.get('uncertainties') or [])}
<section><h2>Verification and correction</h2><p>Submit attributable evidence or a correction for review. Submission does not imply acceptance, publication, or an OOF® Approved Assessment.</p><div class="oof-detail-actions"><a href="/ai-incidents/verify/?incident={text(public_slug(record))}">Help verify this incident</a><a href="/ai-incidents/report/">Report another AI incident</a></div></section>
{history_markup(history or [])}
<p><a href="/ai-incidents/incidents/">Return to the public incident index</a></p>
</article></main><div id="footer"></div><script src="/header.js"></script><script>
fetch("/header.html").then(r=>r.text()).then(v=>{{document.getElementById("header").innerHTML=v;if(window.normalizePageLinks)window.normalizePageLinks();}});
fetch("/footer.html").then(r=>r.text()).then(v=>{{document.getElementById("footer").innerHTML=v;if(window.normalizePageLinks)window.normalizePageLinks();}});
</script></body></html>'''


def build_submission_page(mode: str) -> str:
    verify = mode == "verify"
    title = "Help Verify an AI Incident" if verify else "Report an AI Incident"
    description = (
        "Provide attributable evidence or a correction for an existing public incident record."
        if verify else "Send an attributable public source for a candidate AI incident."
    )
    subject = "OOF AI incident evidence submission" if verify else "OOF AI incident report"
    fields = (
        "Include the incident ID or page URL, evidence URL, publisher, publication date, what the evidence supports or disputes, and your contact details."
        if verify else "Include a source URL, publisher, publication date, event date, location, system or organization, a concise description, and your contact details."
    )
    canonical = f"https://originopenfoundation.org/ai-incidents/{mode}/"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{title} | OOF®</title><meta name="description" content="{text(description)}" /><link rel="canonical" href="{canonical}" />
<link rel="stylesheet" href="/style.css" /><link rel="stylesheet" href="/assets/css/oof-ai-incidents.css?v=7" /></head><body><div id="header"></div>
<main class="oof-incident-app oof-incident-detail"><article><nav class="oof-detail-breadcrumb" aria-label="Breadcrumb"><a href="/index.html">OOF®</a><span>/</span><a href="/ai-incidents/">AI Incident Intelligence</a><span>/</span><span>{title}</span></nav>
<header><h1>{title}</h1><p class="oof-detail-lede">{description}</p></header>
<section><h2>What to include</h2><p>{fields}</p><p>Do not send confidential, personal, privileged, or unlawfully obtained material.</p></section>
<section class="oof-detail-disclosure"><h2>Submission status</h2><p>This site does not claim to provide an automated submission backend. The email action below opens your mail client so the evidence can be reviewed manually. Submission does not imply acceptance or publication.</p></section>
<p class="oof-detail-actions"><a href="mailto:contact@originopenfoundation.org?subject={text(subject).replace(' ', '%20')}">Prepare email submission</a><a href="/ai-incidents/">Return to incident intelligence</a></p>
</article></main><div id="footer"></div><script src="/header.js"></script><script>fetch("/header.html").then(r=>r.text()).then(v=>{{document.getElementById("header").innerHTML=v;}});fetch("/footer.html").then(r=>r.text()).then(v=>{{document.getElementById("footer").innerHTML=v;}});</script></body></html>'''


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


def build(check: bool = False) -> None:
    mismatches = []
    generated_targets: list[Path] = []

    def emit(target: Path, value: str) -> None:
        if check:
            if not target.exists() or generated_page_signature(target.read_text(encoding="utf-8")) != generated_page_signature(value):
                mismatches.append(str(target.relative_to(ROOT)))
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")
        generated_targets.append(target)

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
        emit(target, page)
    payload = json.loads((ROOT / "data" / "ai-incidents" / "incident-store.json").read_text(encoding="utf-8"))
    analyses = json.loads((ROOT / "data" / "ai-incidents" / "analysis-store.json").read_text(encoding="utf-8"))
    public_records = ai_incidents.public_records(payload.get("incidents", []))
    detail_count = 0
    for record in public_records:
        analysis = record.get("automatedAnalysis") or {}
        pattern = (analysis.get("governanceFailurePattern") or {}).get("patternKey")
        architecture_id = ((analysis.get("architectureAnalysis") or {}).get("primaryArchitecture") or {}).get("architectureId")
        related = []
        for candidate in public_records:
            if candidate["id"] == record["id"]:
                continue
            candidate_analysis = candidate.get("automatedAnalysis") or {}
            candidate_pattern = (candidate_analysis.get("governanceFailurePattern") or {}).get("patternKey")
            candidate_architecture = ((candidate_analysis.get("architectureAnalysis") or {}).get("primaryArchitecture") or {}).get("architectureId")
            if (pattern and candidate_pattern == pattern) or (architecture_id and candidate_architecture == architecture_id):
                related.append(candidate)
        related.sort(key=lambda item: str(item.get("occurredAt") or item.get("reportedAt") or ""), reverse=True)
        history = sorted(
            [item for item in analyses.get("assessments", []) if item.get("incidentId") == record["id"]],
            key=lambda item: item.get("analysisVersion", 0),
        )
        target = ROOT / "ai-incidents" / "incidents" / public_slug(record) / "index.html"
        emit(target, build_incident_detail(record, related, history))
        detail_count += 1
    emit(ROOT / "ai-incidents" / "report" / "index.html", build_submission_page("report"))
    emit(ROOT / "ai-incidents" / "verify" / "index.html", build_submission_page("verify"))
    directory = ROOT / "ai-incidents" / "incidents" / "index.html"
    emit(directory, build_incident_directory(public_records))
    expected_directories = {public_slug(record) for record in public_records}
    for child in directory.parent.iterdir():
        if not child.is_dir() or child.name in expected_directories:
            continue
        if check:
            mismatches.append(str(child.relative_to(ROOT)))
        else:
            for generated_file in child.iterdir():
                if generated_file.is_file():
                    generated_file.unlink()
            child.rmdir()
    if not check:
        # Generated incident routes are public documents too. Hydrate their
        # discovery metadata here so a later regeneration cannot remove it.
        for record in discovery.inspect_pages(generated_targets):
            discovery.inject_metadata(record)
            discovery.inject_section_ids(record["path"])
            discovery.inject_semantic_structure(record["path"])
    if mismatches:
        raise SystemExit("Generated AI incident pages are stale:\n- " + "\n- ".join(mismatches[:50]))
    if check:
        print(f"Verified {len(ROUTES)} AI incident routes, the incident index, and {detail_count} incident detail pages.")
        return
    print(f"Generated {len(ROUTES)} AI incident routes, the incident index, and {detail_count} incident detail pages.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify generated pages without writing files")
    build(check=parser.parse_args().check)
