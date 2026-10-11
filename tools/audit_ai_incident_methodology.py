#!/usr/bin/env python3
"""Produce a reproducible Knowledge Layer methodological accuracy audit."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import incident_intelligence_v2 as engine


ROOT = Path(__file__).resolve().parents[1]
JSON_REPORT = ROOT / "data" / "ai-incidents" / "methodological-accuracy-audit.json"
MARKDOWN_REPORT = ROOT / "docs" / "AI_INCIDENT_KNOWLEDGE_LAYER_METHODOLOGICAL_ACCURACY.md"
STAGE_A_JSON_REPORT = ROOT / "data" / "ai-incidents" / "v3-2-stage-a-capability-audit.json"
STAGE_A_REPORT = ROOT / "docs" / "AI_INCIDENT_V3_2_STAGE_A_IMPLEMENTATION_CAPABILITY_AUDIT.md"


def load_records() -> dict[str, dict]:
    payload = engine.read_json(engine.STORE_PATH, {"incidents": []})
    return {item["id"]: item for item in payload.get("incidents", [])}


def sample_assessments(assessments: list[dict], size: int = 20) -> list[dict]:
    """Greedily cover architectures and required evidence/severity conditions."""
    selected = []
    covered_architectures = set()
    covered_traits = set()

    def traits(item: dict) -> set[str]:
        evidence = item.get("evidenceSnapshot", {}).get("corroboration", {})
        severity = item.get("severityAssessment", {}).get("level")
        architecture = item.get("architectureAnalysis", {})
        references = [
            reference.get("artifactType")
            for assignment in [architecture.get("primaryArchitecture"), *architecture.get("contributingArchitectures", [])]
            if assignment for reference in assignment.get("relevantStandardsModules", [])
        ]
        result = {f"severity:{severity}"}
        if evidence.get("independentSourceCount", 0) < 2:
            result.add("single-source")
        if item.get("assessmentConfidence") == "Evidence Insufficient":
            result.add("insufficient-evidence")
        if len(item.get("evidenceGaps", [])) >= 2:
            result.add("incomplete-context")
        if architecture.get("contributingArchitectures"):
            result.add("cross-architecture")
        result.update(f"depth:{value}" for value in references)
        return result

    remaining = sorted(assessments, key=lambda item: item["incidentId"])
    while remaining and len(selected) < size:
        def value(item: dict) -> tuple:
            primary = item.get("architectureAnalysis", {}).get("primaryArchitecture") or {}
            new_architecture = primary.get("objectId") not in covered_architectures
            new_traits = len(traits(item) - covered_traits)
            return (new_traits, int(new_architecture), len(item.get("evidenceGaps", [])), item["incidentId"])
        chosen = max(remaining, key=value)
        remaining.remove(chosen)
        selected.append(chosen)
        primary = chosen.get("architectureAnalysis", {}).get("primaryArchitecture") or {}
        if primary.get("objectId"):
            covered_architectures.add(primary["objectId"])
        covered_traits.update(traits(chosen))
    return selected


def audit_item(assessment: dict, record: dict, knowledge: engine.KnowledgeLayer) -> dict:
    architecture = assessment.get("architectureAnalysis", {})
    assignments = [architecture.get("primaryArchitecture"), *architecture.get("contributingArchitectures", [])]
    assignments = [item for item in assignments if item]
    problems = []
    references = []
    for assignment in assignments:
        canonical_architecture = knowledge.objects.get(assignment.get("objectId"))
        if not canonical_architecture or canonical_architecture.get("artifactType") != "Architecture":
            problems.append(f"Invalid architecture reference: {assignment.get('objectId')}")
        parent_ids = {
            item.get("objectId") for item in assignment.get("relevantStandardsModules", [])
            if item.get("artifactType") == "ParentStandard"
        }
        for reference in assignment.get("relevantStandardsModules", []):
            canonical = knowledge.objects.get(reference.get("objectId"))
            valid = bool(
                canonical
                and canonical.get("canonicalName") == reference.get("name")
                and canonical.get("canonicalUrl") == reference.get("canonicalUrl")
                and canonical.get("architectureId") == assignment.get("objectId")
            )
            if reference.get("artifactType") == "CoreModule":
                valid = valid and canonical.get("parentObjectId") in parent_ids
            if not valid:
                problems.append(f"Invalid methodology reference: {reference.get('objectId')}")
            references.append({
                "objectId": reference.get("objectId"), "name": reference.get("name"),
                "artifactType": reference.get("artifactType"), "canonicalUrl": reference.get("canonicalUrl"),
                "matchedTerms": reference.get("matchedTerms", []), "canonical": valid,
            })
        if not assignment.get("matchedTerms"):
            problems.append(f"Architecture lacks incident evidence terms: {assignment.get('objectId')}")
    chain = assessment.get("methodologicalReasoningChain") or {}
    if not chain:
        problems.append("Methodological reasoning chain is absent")
    questions = assessment.get("governanceQuestions") or []
    if not questions or any(not question.endswith("?") for question in questions):
        problems.append("Governance questions are absent or malformed")
    if any("how no produced" in engine.normalized_text(question) for question in questions):
        problems.append("Governance question contains a source placeholder")
    forbidden_terms = engine.PLACEHOLDER_VALUES | {"including", "while", "without", "otherwise", "previously", "whether"}
    evidence_terms = {engine.normalized_text(term) for item in assignments for term in item.get("matchedTerms", [])}
    if evidence_terms & forbidden_terms:
        problems.append("Weak or placeholder terms were used as assignment evidence")
    dimensions = assessment.get("confidenceDimensions") or {}
    if set(dimensions) != {"sourceCorroboration", "extractionCompleteness", "methodologicalAssignment"}:
        problems.append("Three distinct confidence dimensions are absent")
    normalization = assessment.get("sourceNormalization") or {}
    if normalization.get("sourceRecordModified") is not False or not normalization.get("rawRecordHash"):
        problems.append("Normalization provenance does not preserve the raw record boundary")
    insight = assessment.get("incidentGovernanceInsight")
    if assessment.get("assessmentConfidence") != "Evidence Insufficient" and not insight:
        problems.append("Governance insight is absent despite sufficient evidence")
    return {
        "incidentId": assessment["incidentId"],
        "title": record.get("title"),
        "severity": assessment.get("severityAssessment", {}).get("level"),
        "evidenceState": assessment.get("incidentEvidence", {}).get("evidenceState"),
        "assessmentConfidence": assessment.get("assessmentConfidence"),
        "primaryArchitecture": (architecture.get("primaryArchitecture") or {}).get("label"),
        "contributingArchitectures": [item.get("label") for item in architecture.get("contributingArchitectures", [])],
        "methodologyReferences": references,
        "evidenceTerms": sorted({term for item in assignments for term in item.get("matchedTerms", [])}),
        "governanceQuestions": questions,
        "governanceInsight": insight,
        "methodologicalCorrectness": "STRUCTURALLY VALID" if not problems else "REVIEW_REQUIRED",
        "supportingEvidence": [source.get("sourceId") for source in record.get("sources", [])],
        "problems": problems,
    }


def main() -> int:
    knowledge = engine.KnowledgeLayer()
    records = load_records()
    latest = list(engine.latest_assessments().values())
    audited = [audit_item(item, records[item["incidentId"]], knowledge) for item in sorted(latest, key=lambda value: value["incidentId"])]
    insight_counts = Counter(item["governanceInsight"] for item in audited if item.get("governanceInsight"))
    repeated_insights = [text for text, count in insight_counts.items() if count > 1]
    problems = [problem for item in audited for problem in item["problems"]]
    payload = {
        "schemaVersion": "1.0", "engineVersion": engine.ENGINE_VERSION,
        "knowledgeBuildId": knowledge.manifest.get("buildId"),
        "sampleMethod": "Full-dataset deterministic audit of every latest assessment",
        "sampleSize": len(audited), "auditedIncidents": audited,
        "identifiedProblems": problems,
        "repeatedGenericInsights": repeated_insights,
        "overallMethodologicalAssessment": (
            "The audited automated selections are structurally valid, canonically traceable, and satisfy the implemented evidence-depth constraints. "
            "They remain preliminary and require authorized human review for substantive correctness."
            if not problems and not repeated_insights else
            "One or more sampled selections require review; consult identifiedProblems and repeatedGenericInsights."
        ),
        "limitations": [
            "Lexical retrieval establishes relevance signals, not legal or methodological findings.",
            "Single-source and incomplete records cannot justify every Parent Standard or Core Module.",
            "This reproducible technical audit does not replace authorized expert review.",
        ],
    }
    engine.write_json(JSON_REPORT, payload)
    rows = []
    for item in audited:
        refs = "; ".join(reference["name"] for reference in item["methodologyReferences"]) or "Withheld"
        rows.append(f"| {item['incidentId']} | {item['primaryArchitecture'] or 'Unresolved'} | {refs} | {item['methodologicalCorrectness']} |")
    MARKDOWN_REPORT.write_text(
        "# OOF® AI Incident Knowledge Layer Methodological Accuracy Report\n\n"
        "## A. Integration Architecture\n\n"
        "The assessment engine reads canonical objects and authoritative relationships from `data/knowledge`. "
        "Architecture retrieval is followed by evidence-gated Parent Standard and Core Module retrieval.\n\n"
        "## B. Canonical Source Verification\n\n"
        f"Knowledge build: `{knowledge.manifest.get('buildId')}`. Every displayed reference is checked for canonical identity, name, URL, architecture ownership and module parentage.\n\n"
        "## C. Incident Sample Results\n\n"
        "| Incident | Primary architecture | Standards / modules | Result |\n|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n## D. Identified Problems\n\n"
        + ("\n".join(f"- {problem}" for problem in problems) if problems else "No structural or canonical-reference failure was found in the full-dataset audit.")
        + "\n\n## E. Corrections Implemented\n\n"
        "- Hierarchical retrieval prevents orphan Core Module assignments.\n"
        "- Sparse evidence remains at Architecture depth.\n"
        "- Canonical provenance and a complete methodological reasoning chain are retained.\n"
        "- Regression validation rejects stale names, URLs, cross-architecture references and orphan modules.\n\n"
        "## F. Remaining Limitations\n\n"
        + "\n".join(f"- {item}" for item in payload["limitations"])
        + "\n\n## G. Overall Methodological Assessment\n\n"
        + payload["overallMethodologicalAssessment"] + "\n",
        encoding="utf-8", newline="\n",
    )
    review_queue = engine.read_json(engine.REVIEW_QUEUE_PATH, {"items": []})
    placeholder_systems = sum(
        1 for record in records.values()
        if engine.normalized_text(record.get("system")) in engine.PLACEHOLDER_VALUES
    )
    serialized_industries = sum(
        1 for record in records.values()
        if isinstance(record.get("industry"), str) and record["industry"].strip().startswith("[")
    )
    architecture_ids = {
        assignment.get("objectId")
        for assessment in latest
        for assignment in [assessment.get("architectureAnalysis", {}).get("primaryArchitecture"),
                           *assessment.get("architectureAnalysis", {}).get("contributingArchitectures", [])]
        if assignment and assignment.get("objectId")
    }
    cross_architecture = sum(
        1 for assessment in latest
        if assessment.get("architectureAnalysis", {}).get("contributingArchitectures")
    )
    capability = {
        "schemaVersion": "3.2", "engineVersion": engine.ENGINE_VERSION,
        "title": "OOF® Global AI Incident Intelligence™ — V3.2 Stage A Implementation & Capability Audit",
        "dataset": {
            "incidentRecords": len(records), "latestAssessments": len(latest), "sourceRecordsModified": False,
            "placeholderSystemValuesNormalized": placeholder_systems,
            "serializedIndustryValuesNormalized": serialized_industries,
            "geographicallyAssigned": sum(bool(record.get("countryCode")) for record in records.values()),
            "locationNotSpecified": sum(not bool(record.get("countryCode")) for record in records.values()),
            "architecturesRepresented": len(architecture_ids),
            "crossArchitectureAssessments": cross_architecture,
            "singleSourceAssessments": sum(
                assessment.get("evidenceSnapshot", {}).get("corroboration", {}).get("independentSourceCount", 0) < 2
                for assessment in latest
            ),
            "oofApprovedAssessments": sum(assessment.get("oofApproved") is True for assessment in latest),
        },
        "llmIntegration": {
            "status": "NOT INTEGRATED",
            "finding": "The Stage A assessment path is deterministic Python and does not call an LLM API, submit prompts, consume model tokens, or require an LLM response cache.",
        },
        "sourceConnectors": [
            {"name": "ManualOOFIncidentAdapter", "status": "IMPLEMENTED", "mode": "local review inbox"},
            {"name": "AIIDWeeklyExcelAdapter", "status": "IMPLEMENTED", "mode": "bounded official weekly snapshot"},
        ],
        "validosIntegration": {
            "status": "KNOWLEDGE-LAYER RETRIEVAL",
            "finding": "VALIDOS may be retrieved as canonical methodology; no independent VALIDOS verification or approval is asserted.",
        },
        "performance": {
            "currentMode": "deterministic batch generation with static public projections",
            "futureDailyIntakeTarget": "maximum 10 newly admitted incidents per governed cycle",
            "newSchedulerOrConnectorImplemented": False,
        },
        "qualityGates": {
            "fullDatasetAudited": len(audited), "criticalDefects": len(problems),
            "repeatedGenericInsights": len(repeated_insights),
            "result": "FAIL" if problems else "PASS WITH REVIEW FLAGS" if repeated_insights else "PASS",
        },
        "humanReviewQueue": {"items": len(review_queue.get("items", [])), "automaticApproval": False},
        "stageBDeferred": [
            "new source connectors", "full multi-source VALIDOS verification", "public submission forms",
            "prevention guidance", "new public redesign or SEO routes", "new scheduler", "GIE",
            "new architecture", "multi-agent processing",
        ],
    }
    engine.write_json(STAGE_A_JSON_REPORT, capability)
    STAGE_A_REPORT.write_text(
        "# OOF® Global AI Incident Intelligence™ — V3.2 Stage A Implementation & Capability Audit\n\n"
        "## 1. Executive Result\n\n"
        f"Quality gate: **{capability['qualityGates']['result']}**. Audited all {len(audited)} latest assessments while preserving all {len(records)} raw incident records.\n\n"
        "## 2. Baseline and Scope\n\nStage A covers trust foundation, semantic quality, deterministic normalization, technical capability disclosure, and review controls.\n\n"
        "## 3. Map Integrity\n\nCountry geometry resolution uses ISO_A2 with ISO_A2_EH fallback for Natural Earth `-99` records, including France. Antarctica remains excluded from the public map.\n\n"
        "## 4. Source Normalization\n\nPlaceholders are removed from the analytical view, serialized source arrays are safely parsed, transformations are recorded, and raw source records remain unchanged.\n\n"
        "## 5. Semantic Matching\n\nWeak connective terms are excluded and deeper methodology remains evidence-gated and hierarchical.\n\n"
        "## 6. Governance Questions\n\nQuestions are generated only from normalized source fields and are checked for placeholder leakage and grammatical structure.\n\n"
        "## 7. Confidence Model\n\nSource corroboration, extraction completeness, and methodological assignment confidence are stored and disclosed independently.\n\n"
        "## 8. Human Review\n\nHigh-risk, weak-assignment, and causal-overstatement candidates enter a review queue. Automated approval is prohibited.\n\n"
        "## 9. Assessment History\n\nEngine 3.2 creates a new assessment version and retains superseded versions and raw evidence hashes.\n\n"
        "## 10. LLM Capability\n\nNo LLM is integrated into this assessment path; there are no model prompts, token calls, or response-cache dependencies.\n\n"
        "## 11. Source Connectors\n\nThe current adapters are the manual review inbox and the bounded AIID weekly snapshot adapter. No Stage B connector was added.\n\n"
        "## 12. VALIDOS Status\n\nVALIDOS is available through canonical Knowledge Layer retrieval; this does not constitute independent VALIDOS verification or approval.\n\n"
        "## 13. Performance and Daily Cycle\n\nThe static deterministic build supports governed incremental processing. A future cycle is capped by policy at 10 newly admitted incidents; no new scheduler was implemented.\n\n"
        "## 14. Quality Gates\n\n"
        f"Full-dataset assessments: {len(audited)}. Critical defects: {len(problems)}. Repeated generic insights: {len(repeated_insights)}.\n\n"
        "## 15. Deferred Stage B\n\nNew connectors, full multi-source verification, forms, prevention guidance, redesign, SEO expansion, scheduler work, GIE, new architectures, and multi-agent processing remain deferred.\n",
        encoding="utf-8", newline="\n",
    )
    print(json.dumps({"audited": len(audited), "problems": len(problems), "repeatedGenericInsights": len(repeated_insights), "result": capability["qualityGates"]["result"]}, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
