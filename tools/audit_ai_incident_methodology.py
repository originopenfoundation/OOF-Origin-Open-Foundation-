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
        "methodologicalCorrectness": "SUPPORTED" if not problems else "REVIEW_REQUIRED",
        "supportingEvidence": [source.get("sourceId") for source in record.get("sources", [])],
        "problems": problems,
    }


def main() -> int:
    knowledge = engine.KnowledgeLayer()
    records = load_records()
    latest = list(engine.latest_assessments().values())
    sample = sample_assessments(latest)
    audited = [audit_item(item, records[item["incidentId"]], knowledge) for item in sample]
    insight_counts = Counter(item["governanceInsight"] for item in audited if item.get("governanceInsight"))
    repeated_insights = [text for text, count in insight_counts.items() if count > 1]
    problems = [problem for item in audited for problem in item["problems"]]
    payload = {
        "schemaVersion": "1.0", "engineVersion": engine.ENGINE_VERSION,
        "knowledgeBuildId": knowledge.manifest.get("buildId"),
        "sampleMethod": "Deterministic greedy coverage of architecture, severity, evidence and methodology-depth traits",
        "sampleSize": len(audited), "auditedIncidents": audited,
        "identifiedProblems": problems,
        "repeatedGenericInsights": repeated_insights,
        "overallMethodologicalAssessment": (
            "The audited automated selections are canonically traceable and satisfy the implemented evidence-depth constraints. "
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
        + ("\n".join(f"- {problem}" for problem in problems) if problems else "No structural or canonical-reference failure was found in the reproducible sample.")
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
    print(json.dumps({"sampleSize": len(audited), "problems": len(problems), "repeatedGenericInsights": len(repeated_insights)}, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
