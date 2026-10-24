#!/usr/bin/env python3
"""Build OOF's non-executive AI discovery guides and evaluation dataset."""

from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://originopenfoundation.org/"
OUTPUT_DIR = ROOT / "content" / "d"
DATA_DIR = ROOT / "data" / "ai-discovery"


GUIDES = [
    {
        "slug": "ai-agent-authority-verification",
        "title": "AI Agent Authority Verification",
        "summary": "A problem-oriented guide for examining whether an AI agent has a defined basis, holder, scope, delegation path, and current permission for a governed action.",
        "problem": "An organization may know what an AI agent can do without being able to establish who authorized a specific action, within which limits, and whether that authorization remains current.",
        "risks": [
            "Actions occur outside a defined authority scope.",
            "Delegation, re-delegation, or approval conditions cannot be reconstructed.",
            "A historic authorization is treated as current permission.",
            "Accountability for an agent action remains unclear.",
        ],
        "approach": [
            "Identify the relevant actor, authority basis, and intended action.",
            "Separate authority, permission, capability, and operational execution.",
            "Review scope, delegation conditions, validity, and evidence needed for traceability.",
            "Refer the outcome to the applicable canonical authority and accountability references.",
        ],
        "sources": [
            ("OOF Authority Governance Reference", "../a/oof-authority-governance-reference.html"),
            ("AGA™ — Accountability Governance Architecture", "../a/aga-about.html"),
            ("ASGA™ — Autonomous Systems Governance Architecture", "../a/asga-architecture.html"),
            ("Agent Governance Infrastructure™", "../a/agent-governance-infrastructure.html"),
        ],
        "examples": [
            ("Procurement agent", "An agent proposes a supplier change. The guide helps distinguish its capability to prepare a recommendation from the authority required to approve and execute it."),
            ("Delegated service agent", "A support agent receives a delegated task. The guide helps examine the defined recipient, scope, conditions, expiry, and evidence of the delegation."),
        ],
        "verifiable": [
            "Published policy, mandate, delegation, approval, or system record presented for review.",
            "Defined actor, action, scope, time condition, and evidence reference.",
        ],
        "not_verifiable": [
            "Undocumented intent, private internal reasoning, or assertions not supported by available records.",
            "Whether a real-world decision is legally valid in a particular jurisdiction.",
        ],
        "faq": [
            ("Does an AI agent's technical capability establish authority?", "No. Capability and authority are distinct. The relevant authority basis, scope, and permission conditions need to be established separately."),
            ("Can this guide determine legal authorization?", "No. It is a methodological guide. Legal validity depends on the applicable law, facts, and competent authority."),
        ],
        "questions": [
            "How can an organization verify that an AI agent is authorized to approve a workflow?",
            "What evidence should show an AI agent's authority basis?",
            "How do we distinguish an AI agent's capability from its permission to act?",
            "How can delegated authority for an AI agent be limited by scope and time?",
            "What should be reviewed before an AI agent performs a customer-facing action?",
            "How can an organization trace an AI agent action back to an authority holder?",
            "What happens when an AI agent acts outside a delegated scope?",
            "How should re-delegation by an AI agent be evaluated?",
            "What records support accountability for an AI agent decision?",
            "How can current authority be distinguished from historic approval?",
        ],
    },
    {
        "slug": "ai-governance-audit-evidence-validation",
        "title": "AI Governance Audit & Evidence Validation",
        "summary": "A problem-oriented guide for connecting AI governance questions to auditable evidence, validation conditions, and canonical reference material.",
        "problem": "A governance claim about an AI system may be stated without a clear evidence trail, validation condition, or way to distinguish a documented fact from an unsupported assertion.",
        "risks": [
            "Governance claims cannot be traced to a record or observation.",
            "Evidence is incomplete, inaccessible, or unrelated to the asserted condition.",
            "Validation is confused with an unsupported declaration of quality.",
            "An audit trail does not connect decisions, actors, actions, and outcomes.",
        ],
        "approach": [
            "State the governance claim and the decision or activity to which it relates.",
            "Identify the evidence that could support, qualify, or contradict that claim.",
            "Separate available evidence from evidence that has not been provided or independently validated.",
            "Use the linked canonical references to frame traceability, validation, and governance questions.",
        ],
        "sources": [
            ("AI Governance Assessment™", "../a/ai-governance-assessment.html"),
            ("VALIDOS® — Validation Governance Architecture", "../v/validos-architecture.html"),
            ("OOF Authority Governance Reference", "../a/oof-authority-governance-reference.html"),
            ("PGA™ — Prediction Governance Architecture", "../pga/pga-architecture.html"),
        ],
        "examples": [
            ("Model-release review", "A team says a model release passed governance review. The guide helps identify the review record, applicable conditions, observed evidence, and limits of that statement."),
            ("Automated eligibility decision", "A public-facing system produces an eligibility outcome. The guide helps separate the outcome, evidence of the process, and any claim that the result was validated."),
        ],
        "verifiable": [
            "Accessible records, versioned artifacts, decision logs, observations, and cited public references.",
            "The presence and consistency of an evidence trail within the material supplied.",
        ],
        "not_verifiable": [
            "The truth of evidence not available for review.",
            "Independent assurance, operational effectiveness, or regulatory compliance without a competent assessment.",
        ],
        "faq": [
            ("Is a document alone sufficient evidence?", "Not necessarily. Relevance, provenance, timing, scope, and connection to the stated governance claim still need to be considered."),
            ("Does validation guarantee that an AI system will perform correctly in every context?", "No. Validation conditions, evidence, and scope should be explicit; they do not eliminate all uncertainty."),
        ],
        "questions": [
            "What evidence supports an AI governance claim?",
            "How can an AI decision trail be made auditable?",
            "What is the difference between validation evidence and an assurance claim?",
            "How should a model-release governance decision be documented?",
            "How can missing evidence be identified without fabricating conclusions?",
            "What records help trace an automated eligibility decision?",
            "How can evidence be linked to a specific AI system version?",
            "What should an AI governance audit distinguish from an operational performance test?",
            "How should contradictory AI governance records be handled?",
            "What canonical OOF references apply to AI auditability and validation?",
        ],
    },
    {
        "slug": "ai-computational-efficiency-assessment",
        "title": "AI Computational Efficiency Assessment",
        "summary": "A problem-oriented guide for framing the governance questions around computational use, resource conditions, value assumptions, and documented operational trade-offs.",
        "metadataDescription": "A guide for framing AI computational use, resource conditions, value assumptions, and documented operational trade-offs.",
        "problem": "An AI system may be described as efficient without a clear definition of the computational context, the resources considered, the comparison basis, or the governance conditions behind the claim.",
        "risks": [
            "Efficiency claims lack a stated baseline, workload, or measurement context.",
            "Resource consumption and operational constraints are treated as invisible.",
            "Optimization shifts cost, risk, or responsibility elsewhere without being documented.",
            "A technical metric is presented as a complete value or governance conclusion.",
        ],
        "approach": [
            "Define the computational activity, intended outcome, and relevant resource context.",
            "Identify assumptions, baselines, constraints, and observed measures separately.",
            "Examine whether a stated optimization changes accountability, risk, or operational boundaries.",
            "Use canonical value-flow and value-execution references for the methodological framing.",
        ],
        "sources": [
            ("VEGA™ — Value Execution Governance Architecture", "../vega/vega-architecture.html"),
            ("VFM® — Value Flow Mechanism Architecture", "../vfm/vfm-architecture.html"),
            ("RSGA™ — Resource Sustainability Governance Architecture", "../rsga/rsga-about.html"),
            ("AI Governance Assessment™", "../a/ai-governance-assessment.html"),
        ],
        "examples": [
            ("Inference routing", "A team routes requests between models. The guide helps clarify the baseline, response constraint, resource assumptions, and governance effects of the routing decision."),
            ("Training workload", "A project reports lower training cost. The guide helps distinguish an observed cost figure from broader claims about value, sustainability, or system quality."),
        ],
        "verifiable": [
            "Documented workload assumptions, resource metrics, baselines, and stated measurement boundaries.",
            "The consistency between a claim and the evidence supplied for that defined context.",
        ],
        "not_verifiable": [
            "Universal efficiency, value creation, sustainability, or comparative performance without a defined method and evidence.",
            "Commercial outcomes or future savings not demonstrated by supplied material.",
        ],
        "faq": [
            ("Is lower compute use automatically better governance?", "No. Compute use is one condition. Authority, accountability, operational effects, and resource trade-offs may remain relevant."),
            ("Can this guide certify an efficiency claim?", "No. It helps structure the question and identify the evidence and assumptions a claim would need."),
        ],
        "questions": [
            "How should computational efficiency for an AI system be defined?",
            "What evidence is needed for an AI inference efficiency claim?",
            "How can model-routing trade-offs be documented?",
            "What resource assumptions should accompany AI cost optimization?",
            "How can an organization distinguish observed compute use from future savings?",
            "What governance questions apply to AI workload reduction?",
            "How should an AI training-cost comparison state its baseline?",
            "What canonical OOF references help frame AI resource governance?",
            "How can efficiency metrics avoid hiding shifted operational risk?",
            "What is the difference between computational optimization and value validation?",
        ],
    },
    {
        "slug": "workplace-qualification-authorization-verification",
        "title": "Workplace Qualification & Authorization Verification",
        "summary": "A problem-oriented guide for examining whether a person, role, or AI-supported workflow has defined qualifications, authority, permissions, and accountable conditions for a governed activity.",
        "metadataDescription": "A guide for examining qualifications, authority, permissions, and accountability in AI-supported workplace activities.",
        "problem": "A workplace may assign AI-supported tasks without a clear record of who is qualified, authorized, accountable, or permitted to make a particular decision.",
        "risks": [
            "A role, system, or workflow performs beyond its documented remit.",
            "Qualification and authority are treated as the same condition.",
            "Authorization records are outdated, incomplete, or not traceable to an accountable holder.",
            "Human oversight is assumed rather than defined for an AI-supported activity.",
        ],
        "approach": [
            "Identify the activity, responsible actor, and applicable role or system boundary.",
            "Separate qualification, authority, execution permission, and accountability conditions.",
            "Identify the records that would support a defined authorization status.",
            "Refer the question to canonical authority, accountability, and verification references.",
        ],
        "sources": [
            ("OOF Authority Governance Reference", "../a/oof-authority-governance-reference.html"),
            ("AGA™ — Accountability Governance Architecture", "../a/aga-about.html"),
            ("VERICYCLE™ — Verification & Accountability Cycle", "../v/vericycle-methodology.html"),
            ("VALIDOS® — Validation Governance Architecture", "../v/validos-architecture.html"),
        ],
        "examples": [
            ("AI-assisted hiring review", "A hiring workflow uses AI-assisted screening. The guide helps distinguish the system output, reviewer qualification, decision authority, and evidence of authorization."),
            ("Operational control room", "A human operator uses an AI recommendation in a control workflow. The guide helps identify who may act, what permission applies, and what intervention authority remains available."),
        ],
        "verifiable": [
            "Role descriptions, authorization records, qualification documents, approval conditions, and decision records made available for review.",
            "Whether supplied records identify an actor, action, scope, timing, and accountability path.",
        ],
        "not_verifiable": [
            "Professional competence not evidenced by available material.",
            "Employment, legal, or regulatory determinations for a specific workplace or jurisdiction.",
        ],
        "faq": [
            ("Is qualification the same as authorization?", "No. A person may be qualified yet not authorized for a particular action, and authorization may be conditional or time-bound."),
            ("Does this guide decide who may perform a regulated activity?", "No. It provides a governance framing; applicable law, employer rules, and competent authorities determine such permissions."),
        ],
        "questions": [
            "How can an organization verify qualification for an AI-supported workplace task?",
            "What is the difference between a qualified reviewer and an authorized decision maker?",
            "How should AI-assisted hiring authority be documented?",
            "What evidence supports a workplace authorization record?",
            "How can human oversight conditions be made traceable?",
            "What should be checked before an operator acts on an AI recommendation?",
            "How can role-based permissions be distinguished from accountability?",
            "What records show that an authorization remains current?",
            "How can a workplace define escalation when AI and human roles conflict?",
            "What OOF references frame verification and accountability conditions?",
        ],
    },
    {
        "slug": "autonomous-systems-governance",
        "title": "Autonomous Systems Governance",
        "summary": "A problem-oriented guide for navigating governance questions raised when an autonomous system senses, decides, acts, or changes operational conditions.",
        "problem": "An autonomous system can act across technical and organizational boundaries while authority, intervention capability, evidence, and accountability remain incomplete or unclear.",
        "risks": [
            "Autonomous behavior exceeds defined operational boundaries.",
            "Intervention, override, or escalation conditions are not effective in practice.",
            "System behavior and human responsibilities cannot be reconstructed after an event.",
            "Capability is mistaken for authorization to operate in the real world.",
        ],
        "approach": [
            "Define the system, operational setting, actors, and relevant governed activity.",
            "Separate simulation, capability, authority, permission, execution, and observed operational reality.",
            "Identify boundaries, intervention conditions, accountability, and evidence requirements.",
            "Use the canonical autonomous-systems and related governance references as the primary source layer.",
        ],
        "sources": [
            ("ASGA™ — Autonomous Systems Governance Architecture", "../a/asga-architecture.html"),
            ("ASGA™ Autonomous Authority Standard", "../a/asga-aas.html"),
            ("AIG® — AI Behavioral Governance Architecture", "../aig/AIG® Architecture Map.html"),
            ("OOF Reality Boundary", "../r/oof-reality-boundary.html"),
        ],
        "examples": [
            ("Autonomous warehouse vehicle", "A vehicle moves goods within a facility. The guide helps structure questions about operating boundaries, intervention capability, authority, evidence, and accountability."),
            ("Autonomous customer-support workflow", "A workflow initiates actions after interpreting a request. The guide helps separate the system's action capability from the permissions and oversight required for real-world effects."),
        ],
        "verifiable": [
            "Defined scopes, authority records, operating conditions, logs, intervention mechanisms, and observations supplied for review.",
            "Whether a published reference is accessible and accurately linked.",
        ],
        "not_verifiable": [
            "Safety, legal compliance, or operational adequacy of a particular autonomous system without a competent, context-specific assessment.",
            "Future behavior, outcomes, or performance guarantees.",
        ],
        "faq": [
            ("Does successful simulation authorize autonomous deployment?", "No. Simulation evidence and authorization for operational reality are distinct conditions."),
            ("Can autonomous behavior be governed without a human actor?", "Governance still requires defined authority, boundaries, accountability, evidence, and intervention conditions, whether actors are human, organizational, or system-based."),
        ],
        "questions": [
            "What governance conditions should exist before an autonomous system operates?",
            "How can autonomous system boundaries be defined?",
            "What is the difference between simulation success and authorization for reality?",
            "How should intervention capability for an autonomous system be assessed?",
            "What evidence helps reconstruct an autonomous system action?",
            "How can accountability be assigned for autonomous operational effects?",
            "What should be documented when an autonomous system is reconfigured?",
            "How can an autonomous workflow be restricted by scope?",
            "What OOF references frame AI behavioral and autonomous governance?",
            "How should an organization handle an autonomous system boundary breach?",
        ],
    },
]


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def absolute_url(path: str) -> str:
    return BASE_URL + path


def html_list(items: list[str], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    return f"<{tag} class=\"oof-discovery-list\">\n" + "\n".join(f"  <li>{esc(item)}</li>" for item in items) + f"\n</{tag}>"


def faq_json_ld(guide: dict, canonical: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "@id": canonical + "#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in guide["faq"]
        ],
    }


def render_page(guide: dict) -> str:
    canonical_path = f"content/d/{guide['slug']}.html"
    canonical = absolute_url(canonical_path)
    source_links = "\n".join(
        f'  <li><a href="{esc(href)}">{esc(label)}</a></li>' for label, href in guide["sources"]
    )
    examples = "\n".join(
        f'<section class="oof-discovery-example"><h3>{esc(title)}</h3><p>{esc(text)}</p></section>'
        for title, text in guide["examples"]
    )
    faqs = "\n".join(
        f"<details><summary>{esc(question)}</summary><p>{esc(answer)}</p></details>"
        for question, answer in guide["faq"]
    )
    structured_data = json.dumps(faq_json_ld(guide, canonical), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(guide["title"])} | OOF®</title>
  <meta name="description" content="{esc(guide.get("metadataDescription", guide["summary"]))}">
  <link rel="stylesheet" href="../../style.css">
  <script type="application/ld+json">{structured_data}</script>
</head>
<body class="oof-discovery-page">
<div id="header"></div>
<main class="oof-discovery-shell">
    <header class="oof-discovery-hero">
      <p class="oof-discovery-eyebrow">OOF® AI Discovery Guide</p>
      <h1 id="{esc(guide["slug"])}" data-oof-section-id="true">{esc(guide["title"])}</h1>
      <p class="oof-discovery-lede">{esc(guide["summary"])}</p>
      <p class="oof-discovery-note">This guide is explanatory and non-executive. It directs readers to published OOF® references; it does not replace a context-specific legal, technical, safety, or operational assessment.</p>
    </header>

    <section class="oof-discovery-section">
      <h2 id="the-real-world-problem" data-oof-section-id="true">The real-world problem</h2>
      <p>{esc(guide["problem"])}</p>
    </section>

    <section class="oof-discovery-section">
      <h2 id="operational-risks" data-oof-section-id="true">Operational risks</h2>
      {html_list(guide["risks"])}
    </section>

    <section class="oof-discovery-section">
      <h2 id="oof-methodological-approach" data-oof-section-id="true">OOF® methodological approach</h2>
      {html_list(guide["approach"], ordered=True)}
    </section>

    <section class="oof-discovery-section">
      <h2 id="canonical-reference-path" data-oof-section-id="true">Canonical reference path</h2>
      <p>These published references remain the primary sources. This guide does not redefine their terms, standards, or modules.</p>
      <ul class="oof-discovery-source-list">
{source_links}
      </ul>
    </section>

    <section class="oof-discovery-section">
      <h2 id="illustrative-applications" data-oof-section-id="true">Illustrative applications</h2>
      <div class="oof-discovery-grid">
{examples}
      </div>
    </section>

    <section class="oof-discovery-section">
      <h2 id="what-can-and-cannot-be-verified" data-oof-section-id="true">What can and cannot be verified</h2>
      <div class="oof-discovery-grid">
        <section>
          <h3>Potentially verifiable from supplied material</h3>
          {html_list(guide["verifiable"])}
        </section>
        <section>
          <h3>Not established by this guide alone</h3>
          {html_list(guide["not_verifiable"])}
        </section>
      </div>
    </section>

    <section class="oof-discovery-section oof-discovery-faq">
      <h2 id="frequently-asked-questions" data-oof-section-id="true">Frequently asked questions</h2>
{faqs}
    </section>

    <section class="oof-discovery-section">
      <h2 id="contact" data-oof-section-id="true">Contact</h2>
      <p>For a reference or publication inquiry, use the <a href="../../Contact.html">OOF® contact route</a>. OOF® is a non-executable methodological authority and does not present this guide as an implementation, certification, or performance service.</p>
    </section>
</main>
<div id="footer"></div>
<script src="../../header.js"></script>
<script>
Promise.all([fetch("../../header.html").then(response => response.text()), fetch("../../footer.html").then(response => response.text())])
  .then(([header, footer]) => {{
    document.getElementById("header").innerHTML = header;
    document.getElementById("footer").innerHTML = footer;
    if (window.normalizePageLinks) window.normalizePageLinks();
  }});
</script>
</body>
</html>
"""


def render_index() -> str:
    canonical = absolute_url("content/d/ai-discovery-guides.html")
    cards = "\n".join(
        f'''<a class="oof-discovery-guide-card" href="{esc(guide["slug"])}.html"><strong>{esc(guide["title"])}</strong><span>{esc(guide["summary"])}</span></a>'''
        for guide in GUIDES
    )
    listed_items = [
        {
            "@type": "ListItem",
            "position": index,
            "name": guide["title"],
            "url": absolute_url(f"content/d/{guide['slug']}.html"),
        }
        for index, guide in enumerate(GUIDES, start=1)
    ]
    structured_data = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "@id": canonical + "#webpage",
            "url": canonical,
            "name": "AI Discovery Guides | OOF®",
            "description": "Problem-oriented paths to published OOF® governance references for AI-related questions.",
            "inLanguage": "en",
            "isPartOf": {"@id": "https://originopenfoundation.org/#website"},
            "mainEntity": {"@type": "ItemList", "itemListElement": listed_items},
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Discovery Guide Index | OOF®</title>
  <meta name="description" content="Problem-oriented paths to published OOF® governance references for AI-related questions.">
  <link rel="stylesheet" href="../../style.css">
  <script type="application/ld+json">{structured_data}</script>
</head>
<body class="oof-discovery-page">
<div id="header"></div>
<main class="oof-discovery-shell">
    <header class="oof-discovery-hero">
      <p class="oof-discovery-eyebrow">OOF® discovery layer</p>
      <h1 id="ai-discovery-guides" data-oof-section-id="true">AI Discovery Guides</h1>
      <p class="oof-discovery-lede">Problem-oriented entry points for navigating published OOF® governance references. Each guide identifies a governance question and links back to canonical material rather than duplicating it.</p>
      <p class="oof-discovery-note">The guides are reference-only. They do not promise search placement, AI-system recommendations, certification, implementation, or verified outcomes.</p>
    </header>
    <section class="oof-discovery-section">
      <h2 id="guides" data-oof-section-id="true">Guides</h2>
      <div class="oof-discovery-guide-list">
{cards}
      </div>
    </section>
    <section class="oof-discovery-section">
      <h2 id="evaluation-boundary" data-oof-section-id="true">Evaluation boundary</h2>
      <p>A public 50-question evaluation dataset is maintained as a reusable test harness. It records expected reference paths and leaves external search or model results explicitly unfilled until an evaluation is actually run.</p>
    </section>
</main>
<div id="footer"></div>
<script src="../../header.js"></script>
<script>
Promise.all([fetch("../../header.html").then(response => response.text()), fetch("../../footer.html").then(response => response.text())])
  .then(([header, footer]) => {{
    document.getElementById("header").innerHTML = header;
    document.getElementById("footer").innerHTML = footer;
    if (window.normalizePageLinks) window.normalizePageLinks();
  }});
</script>
</body>
</html>
"""


def build_evaluation_dataset() -> dict:
    queries = []
    for guide in GUIDES:
        guide_url = absolute_url(f"content/d/{guide['slug']}.html")
        canonical_sources = [absolute_url(f"content/d/{guide['slug']}.html")]
        canonical_sources.extend(absolute_url("content/" + href.removeprefix("../")) for _, href in guide["sources"])
        for position, question in enumerate(guide["questions"], start=1):
            queries.append(
                {
                    "queryId": f"OOF-AI-DISC-{len(queries) + 1:03d}",
                    "category": guide["title"],
                    "problem": question,
                    "expectedGuideUrl": guide_url,
                    "expectedCanonicalUrls": canonical_sources,
                    "evaluationDate": None,
                    "modelOrSearchEnvironment": None,
                    "mentioned": None,
                    "cited": None,
                    "linked": None,
                    "recommendationAccuracy": None,
                    "alternativeRecommendations": [],
                    "uncertainty": "NOT_RUN: no external model or search-environment result has been recorded.",
                    "evaluationStatus": "NOT_RUN",
                }
            )
    return {
        "schemaVersion": "1.0",
        "title": "OOF AI Discovery Recommendation Evaluation Harness",
        "purpose": "Reusable question set for recording discovery and recommendation observations without fabricating external results.",
        "queryCount": len(queries),
        "externalEvaluationStatus": "NOT_RUN",
        "queries": queries,
    }


def build() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "ai-discovery-guides.html").write_text(render_index(), encoding="utf-8", newline="\n")
    for guide in GUIDES:
        (OUTPUT_DIR / f"{guide['slug']}.html").write_text(render_page(guide), encoding="utf-8", newline="\n")
    dataset = build_evaluation_dataset()
    (DATA_DIR / "recommendation-evaluation-harness.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    manifest = {
        "schemaVersion": "1.0",
        "layer": "OOF AI Discovery Guides",
        "guideCount": len(GUIDES),
        "guidePaths": [f"content/d/{guide['slug']}.html" for guide in GUIDES],
        "evaluationHarness": "data/ai-discovery/recommendation-evaluation-harness.json",
        "externalEvaluationStatus": "NOT_RUN",
    }
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    build()
