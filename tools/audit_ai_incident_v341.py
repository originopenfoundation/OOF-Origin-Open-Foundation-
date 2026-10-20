#!/usr/bin/env python3
"""Independently audit the public AI incident V3.4.1 production projection."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ai-incidents"
PUBLIC = DATA / "public"
REPORT = DATA / "v3-4-1-production-audit.json"
MARKDOWN = ROOT / "docs" / "AI_INCIDENT_V3_4_1_PRODUCTION_REMEDIATION_AUDIT.md"
NOISE = re.compile(r"\b(?:how|involving)\s+(?:yes|no|been|including|while|without|otherwise|previously|whether)\b", re.I)


def read(path: Path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def run() -> dict:
    index = read(PUBLIC / "incident-index.json", {"items": []})
    summary = read(PUBLIC / "summary.json", {})
    store = read(DATA / "analysis-store.json", {"assessments": []})
    latest = {}
    historical_noise = 0
    for assessment in store.get("assessments", []):
        text = " ".join([assessment.get("incidentGovernanceInsight") or "", *(assessment.get("governanceQuestions") or [])])
        if NOISE.search(text):
            historical_noise += 1
        incident_id = assessment.get("incidentId")
        if incident_id and assessment.get("analysisVersion", 0) > latest.get(incident_id, {}).get("analysisVersion", 0):
            latest[incident_id] = assessment
    errors = []
    statuses = Counter()
    for item in index.get("items", []):
        detail = read(PUBLIC / "incident-details" / f"{item.get('slug')}.json", {})
        assessment = item.get("assessment") or {}
        statuses[assessment.get("analysisStatus") or "MISSING"] += 1
        if not item.get("source", {}).get("url", "").startswith(("https://", "http://")):
            errors.append(f"{item.get('id')}: source attribution missing")
        if not detail or detail.get("id") != item.get("id"):
            errors.append(f"{item.get('id')}: detail projection mismatch")
        for value in (item.get("governanceInsight") or "", *(detail.get("automatedAnalysis", {}).get("governanceQuestions") or [])):
            if NOISE.search(value):
                errors.append(f"{item.get('id')}: placeholder-derived generated subject")
        if assessment.get("analysisStatus") == "AUTOMATED_ANALYSIS_AVAILABLE":
            outcome = (detail.get("automatedAnalysis") or {}).get("qualityOutcomes") or {}
            if outcome.get("publicationEligibility") != "PUBLISHABLE":
                errors.append(f"{item.get('id')}: published analysis lacks publication eligibility")
    expected = summary.get("totalIncidents")
    if expected != len(index.get("items", [])):
        errors.append("summary total does not match public incident index")
    result = {
        "auditVersion": "OOF-AII-INDEPENDENT-AUDIT-3.4.1.1",
        "auditedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Public projection, generated analysis status, source attribution, and detail-page consistency.",
        "recordsAudited": len(index.get("items", [])),
        "latestAssessmentsAudited": len(latest),
        "historicalPlaceholderDerivedOutputs": historical_noise,
        "currentPlaceholderDerivedOutputs": sum(1 for error in errors if "placeholder-derived" in error),
        "analysisStatuses": dict(statuses),
        "humanReviewPending": summary.get("humanReviewPending"),
        "architectureCoverageReviewRequired": summary.get("architectureCoverageReviewRequired"),
        "errors": errors,
        "result": "PASS" if not errors else "FAIL",
        "independenceStatement": "This audit reads the generated public artifacts and does not invoke the incident intelligence validator.",
    }
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MARKDOWN.parent.mkdir(parents=True, exist_ok=True)
    MARKDOWN.write_text(
        "# AI Incident V3.4.1 Production Remediation Audit\n\n"
        f"Result: **{result['result']}**\n\n"
        f"- Public records audited: {result['recordsAudited']}\n"
        f"- Latest assessments audited: {result['latestAssessmentsAudited']}\n"
        f"- Historical placeholder-derived outputs: {result['historicalPlaceholderDerivedOutputs']}\n"
        f"- Current placeholder-derived public outputs: {result['currentPlaceholderDerivedOutputs']}\n"
        f"- Human review pending: {result['humanReviewPending']}\n"
        f"- Architecture coverage review required: {result['architectureCoverageReviewRequired']}\n\n"
        "The audit independently checks public index/detail consistency, source attribution, publication eligibility and generated-placeholder patterns. "
        "It does not alter source incident facts or assessment history.\n",
        encoding="utf-8",
    )
    if errors:
        raise SystemExit("Independent audit failed:\n- " + "\n- ".join(errors[:50]))
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run()
