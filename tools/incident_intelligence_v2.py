#!/usr/bin/env python3
"""Build versioned, evidence-linked OOF incident intelligence assessments.

Source incident records are read-only. Generated analysis is stored separately,
remains explicitly unapproved, and consumes the existing OOF Knowledge Layer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "ai-incidents"
STORE_PATH = DATA_ROOT / "incident-store.json"
ANALYSIS_PATH = DATA_ROOT / "analysis-store.json"
KNOWLEDGE_SNAPSHOT_PATH = DATA_ROOT / "knowledge-reassessment-state.json"
KNOWLEDGE_ROOT = ROOT / "data" / "knowledge"
ENGINE_VERSION = "2.0.1"

STOPWORDS = {
    "about", "across", "after", "against", "architecture", "based", "before", "between",
    "complete", "core", "from", "governance", "governed", "incident", "index", "intelligence",
    "activity", "architecture", "control", "data", "human", "layer", "management", "method", "model",
    "module", "modules", "oof", "operational", "risk", "standard", "standards", "system", "systems", "that",
    "their", "these", "this", "through", "under", "using", "where", "which", "with",
}

# These are mechanism-to-language expansions, not architecture assignments.
# Architecture ownership is resolved dynamically from the Knowledge Layer.
MECHANISM_EXPANSIONS = {
    "deepfake": ("identity", "impersonation", "origin", "evidence"),
    "impersonation": ("identity", "origin", "attribution"),
    "biometric": ("identity", "classification", "recognition"),
    "hallucination": ("validation", "evidence", "reliability", "accuracy"),
    "misidentified": ("validation", "classification", "recognition", "accuracy"),
    "misread": ("validation", "classification", "observation", "accuracy"),
    "incorrect": ("validation", "evidence", "accuracy"),
    "fabricated": ("validation", "evidence", "integrity"),
    "autonomous": ("agency", "execution", "autonomous", "control"),
    "robot": ("agency", "execution", "autonomous", "control"),
    "drone": ("agency", "execution", "autonomous", "control"),
    "cyber": ("integrity", "security", "risk"),
    "malware": ("integrity", "security", "risk"),
    "phishing": ("identity", "integrity", "security"),
    "prediction": ("prediction", "uncertainty", "probability"),
    "predictive": ("prediction", "uncertainty", "probability"),
    "liability": ("liability", "responsibility", "accountability"),
    "credit": ("value", "eligibility", "decision"),
    "loan": ("value", "eligibility", "decision"),
    "pricing": ("value", "valuation", "flow"),
    "tax": ("tax", "event", "value"),
    "memory": ("memory", "retention", "record"),
    "training": ("memory", "provenance", "data"),
    "simulation": ("simulation", "model", "reality"),
    "chatbot": ("cognition", "reasoning", "decision"),
    "reasoning": ("cognition", "decision", "interpretation"),
    "sensor": ("observation", "operational", "reality"),
    "perception": ("observation", "operational", "reality"),
}

SEVERITY_SIGNALS = {
    "actualHarm": {
        3: ("death", "dead", "killed", "fatal", "hospitalized", "gunpoint"),
        2: ("injury", "injured", "arrested", "detained", "lost", "defrauded", "harassment"),
        1: ("denied", "blocked", "discrimination", "misidentified", "incorrect"),
    },
    "scale": {
        3: ("millions of", "nationwide", "global", "mass"),
        2: ("thousands of", "hundreds of", "widespread", "campaign"),
        1: ("multiple", "several", "community"),
    },
    "reversibility": {
        3: ("death", "fatal", "permanent"),
        2: ("financial loss", "lost £", "lost $", "lost €", "irreversible"),
        1: ("suspended", "removed", "reputational"),
    },
    "autonomy": {2: ("autonomous", "self-driving", "robot", "drone", "agentic"), 1: ("automated", "algorithm")},
    "propagation": {2: ("viral", "mass-produced", "campaign", "widespread"), 1: ("shared", "social media")},
    "infrastructureImportance": {2: ("hospital", "election", "power grid", "police", "military", "government"), 1: ("school", "bank", "airport")},
    "financialImpact": {2: ("fraud", "defrauded", "financial loss", "lost £", "lost $", "lost €"), 1: ("credit", "loan", "insurance")},
    "physicalImpact": {3: ("death", "killed", "fatal"), 2: ("injury", "injured", "gunpoint"), 1: ("collision", "unsafe")},
    "informationImpact": {2: ("deepfake", "misinformation", "disinformation", "fabricated", "cloned voice"), 1: ("hallucination", "incorrect claim")},
    "controlFailure": {2: ("without consent", "unauthorized", "no oversight"), 1: ("failed to", "malfunction", "vulnerability")},
    "persistence": {2: ("ongoing", "persistent", "retained indefinitely"), 1: ("repeated", "continued")},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def canonical_json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_hash(value) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def normalized_text(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def tokens(value) -> list[str]:
    return [word for word in normalized_text(value).split() if len(word) >= 4 and word not in STOPWORDS]


def immutable_source_view(record: dict) -> dict:
    """Exclude legacy generated classification fields from source evidence."""
    return {key: value for key, value in record.items() if key not in {"architectureRelevance", "assessment"}}


class KnowledgeLayer:
    def __init__(self, root: Path = KNOWLEDGE_ROOT):
        self.root = root
        objects_payload = read_json(root / "objects-core.json", {"objects": []})
        relationships_payload = read_json(root / "relationships.json", {"relationships": []})
        self.manifest = read_json(root / "manifest.json", {})
        self.objects = {
            item["id"]: item for item in objects_payload.get("objects", [])
            if item.get("authorityState") == "CANONICAL_AUTHORITATIVE"
        }
        self.relationships = [
            item for item in relationships_payload.get("relationships", [])
            if item.get("authorityState") == "AUTHORITATIVE"
        ]
        self.architectures = {
            item["id"]: item for item in self.objects.values() if item.get("artifactType") == "Architecture"
        }
        self.children = defaultdict(list)
        for item in self.objects.values():
            architecture_id = item.get("architectureId")
            if architecture_id in self.architectures:
                self.children[architecture_id].append(item)
        self.corpora = {architecture_id: self._corpus(architecture_id) for architecture_id in self.architectures}
        self.document_frequency = Counter(
            term for corpus in self.corpora.values() for term in set(corpus)
        )
        self.signatures = {architecture_id: self._signature(architecture_id) for architecture_id in self.architectures}
        self.impact_fingerprint = content_hash(self.signatures)

    def _material_fields(self, item: dict) -> dict:
        return {
            key: item.get(key) for key in (
                "id", "canonicalName", "acronym", "artifactType", "canonicalDefinition", "governedSpace",
                "coreQuestion", "category", "subcategory", "status", "version", "architectureId", "parentObjectId",
            )
        }

    def _signature(self, architecture_id: str) -> str:
        related = sorted((self._material_fields(item) for item in self.children[architecture_id]), key=lambda item: item["id"])
        relations = sorted(
            [{
                "sourceId": rel.get("sourceId"), "targetId": rel.get("targetId"), "relationshipType": rel.get("relationshipType")
            }
            for rel in self.relationships
            if rel.get("sourceId") == architecture_id or rel.get("targetId") == architecture_id],
            key=lambda item: (item["sourceId"] or "", item["targetId"] or "", item["relationshipType"] or ""),
        )
        return content_hash({"architecture": self._material_fields(self.architectures[architecture_id]), "children": related, "relationships": relations})

    def _corpus(self, architecture_id: str) -> Counter[str]:
        architecture = self.architectures[architecture_id]
        corpus = Counter()
        for field in ("canonicalName", "acronym", "canonicalDefinition", "governedSpace", "coreQuestion"):
            corpus.update(tokens(architecture.get(field)))
        for child in self.children[architecture_id]:
            for field in ("canonicalName", "acronym", "canonicalDefinition", "governedSpace", "coreQuestion", "category", "subcategory"):
                corpus.update(tokens(child.get(field)))
        return corpus

    def _incident_terms(self, record: dict) -> Counter[str]:
        weighted = Counter()
        for field, weight in (("title", 4), ("system", 3), ("technology", 3), ("industry", 2), ("summary", 1), ("organization", 1), ("aiSystemType", 2)):
            for term in tokens(record.get(field)):
                weighted[term] += weight
        original = list(weighted)
        for term in original:
            for expansion in MECHANISM_EXPANSIONS.get(term, ()):
                if expansion not in STOPWORDS:
                    weighted[expansion] += 2
        return weighted

    def rank(self, record: dict) -> list[dict]:
        incident_terms = self._incident_terms(record)
        ranked = []
        for architecture_id, corpus in self.corpora.items():
            matches = sorted(set(incident_terms) & set(corpus), key=lambda term: (-incident_terms[term] * min(corpus[term], 3), term))
            score = sum(
                incident_terms[term]
                * min(corpus[term], 3)
                * (1 + math.log((len(self.corpora) + 1) / (self.document_frequency[term] + 1)))
                for term in matches
            )
            if score:
                architecture = self.architectures[architecture_id]
                ranked.append({
                    "objectId": architecture_id,
                    "architectureId": str(architecture.get("acronym") or "").casefold(),
                    "label": architecture.get("canonicalName"),
                    "canonicalUrl": architecture.get("canonicalUrl"),
                    "score": round(score, 2),
                    "matchedTerms": matches[:12],
                })
        return sorted(ranked, key=lambda item: (-item["score"], item["architectureId"]))

    def references(self, architecture_object_id: str, record: dict, limit: int = 3) -> list[dict]:
        incident_terms = self._incident_terms(record)
        ranked = []
        for item in self.children.get(architecture_object_id, []):
            corpus = Counter()
            for field in ("canonicalName", "canonicalDefinition", "governedSpace", "coreQuestion", "category", "subcategory"):
                corpus.update(tokens(item.get(field)))
            matched = sorted(set(incident_terms) & set(corpus))
            score = sum(incident_terms[term] * min(corpus[term], 3) for term in matched)
            if score:
                ranked.append({
                    "objectId": item["id"], "name": item.get("canonicalName"), "artifactType": item.get("artifactType"),
                    "canonicalUrl": item.get("canonicalUrl"), "matchedTerms": matched[:8], "score": score,
                })
        return sorted(ranked, key=lambda item: (-item["score"], item["name"] or ""))[:limit]


def source_authority(source: dict) -> str:
    value = normalized_text(" ".join(str(source.get(key) or "") for key in ("sourceType", "publisher", "verificationStatus")))
    if any(term in value for term in ("regulator", "government", "court", "official statement")):
        return "Official"
    if any(term in value for term in ("research", "university", "academic")):
        return "Research"
    if "database" in value or "weekly data export" in value:
        return "Specialist database"
    if "journal" in value or "news" in value:
        return "Journalism"
    return "Unclassified"


def evidence_snapshot(record: dict) -> dict:
    sources = []
    independence_keys = set()
    for source in record.get("sources") or []:
        host = urlparse(source.get("url") or "").hostname or ""
        independence_key = normalized_text(source.get("publisher") or host or source.get("sourceId"))
        independence_keys.add(independence_key)
        sources.append({
            "sourceId": source.get("sourceId"),
            "url": source.get("url"),
            "publisher": source.get("publisher"),
            "authority": source_authority(source),
            "independenceKey": independence_key,
            "directness": "Secondary catalogue" if "database" in normalized_text(source.get("publisher")) else "Not determined",
            "publicationTime": source.get("publicationDate"),
            "retrievalTime": source.get("retrievedAt"),
            "eventTime": record.get("occurredAt"),
            "verificationState": source.get("verificationStatus"),
        })
    incident_source_hash = content_hash(immutable_source_view(record))
    return {
        "snapshotId": f"{record['id']}-EVID-{incident_source_hash[:12]}",
        "incidentSourceHash": incident_source_hash,
        "sources": sources,
        "corroboration": {
            "sourceCount": len(sources),
            "independentSourceCount": len(independence_keys),
            "status": "Single-source" if len(independence_keys) < 2 else "Corroborated",
            "contradictionState": "Not evaluated" if len(independence_keys) < 2 else "No contradiction identified",
        },
    }


def severity_assessment(record: dict, evidence: dict) -> dict:
    text = normalized_text(" ".join(str(record.get(key) or "") for key in ("title", "summary", "system", "organization", "impactTypes", "affectedParties")))
    dimensions = {}
    matched_evidence = {}
    for dimension, levels in SEVERITY_SIGNALS.items():
        score = 0
        signals = []
        for level, phrases in levels.items():
            matches = [phrase for phrase in phrases if normalized_text(phrase) in text]
            if matches and level > score:
                score = level
                signals = matches
        dimensions[dimension] = score
        if signals:
            matched_evidence[dimension] = signals
    if len(record.get("affectedParties") or []) >= 5:
        dimensions["affectedPopulation"] = 2
    elif record.get("affectedParties"):
        dimensions["affectedPopulation"] = 1
    else:
        dimensions["affectedPopulation"] = 0
    score = sum(dimensions.values())
    evidence_depth = sum(bool(record.get(field)) for field in ("summary", "countryCode", "organization", "system", "impactTypes", "affectedParties"))
    confidence = min(0.88, 0.35 + evidence_depth * 0.06 + min(evidence["corroboration"]["independentSourceCount"], 2) * 0.08)
    if evidence_depth < 2:
        level = "Insufficient Evidence"
    elif score >= 15 and (dimensions.get("actualHarm", 0) >= 2 or dimensions.get("physicalImpact", 0) >= 2):
        level = "Critical"
    elif score >= 9:
        level = "High"
    elif score >= 4:
        level = "Moderate"
    else:
        level = "Low"
    active = [name for name, value in dimensions.items() if value]
    rationale = (
        f"Automated evidence-based severity is {level} from {len(active)} supported dimensions: "
        f"{', '.join(active) if active else 'no material severity dimension identified'}. "
        "This is an automated analysis, not an OOF® approved determination."
    )
    return {
        "level": level, "score": score, "confidence": round(confidence, 2), "dimensions": dimensions,
        "matchedEvidence": matched_evidence, "rationale": rationale, "rubricVersion": "OOF-AII-SEV-1.0",
    }


def architecture_analysis(record: dict, knowledge: KnowledgeLayer) -> dict:
    ranked = knowledge.rank(record)
    if not ranked:
        return {"status": "INSUFFICIENT_EVIDENCE", "primaryArchitecture": None, "contributingArchitectures": []}
    maximum = ranked[0]["score"]
    if maximum < 3:
        return {"status": "INSUFFICIENT_EVIDENCE", "primaryArchitecture": None, "contributingArchitectures": []}
    selected = [item for item in ranked if item["score"] >= max(3, maximum * 0.65)]
    results = []
    for index, candidate in enumerate(selected):
        confidence = min(0.9, 0.48 + candidate["score"] / max(40, maximum * 2) * 0.35)
        references = knowledge.references(candidate["objectId"], record)
        results.append({
            **candidate,
            "role": "Primary" if index == 0 else "Contributing",
            "governedMechanism": ", ".join(candidate["matchedTerms"][:5]),
            "reasonForRelevance": (
                f"Knowledge retrieval matched incident evidence to {candidate['label']} through governed terms: "
                f"{', '.join(candidate['matchedTerms'][:8])}."
            ),
            "supportingEvidence": [source.get("sourceId") for source in record.get("sources") or []],
            "confidence": round(confidence, 2),
            "uncertainty": "Automated retrieval; no authorized human review performed.",
            "relevantStandardsModules": references,
        })
    return {"status": "AUTOMATED_ANALYSIS", "primaryArchitecture": results[0], "contributingArchitectures": results[1:]}


def uncertainty_notes(record: dict, evidence: dict, architecture: dict) -> list[str]:
    notes = []
    if evidence["corroboration"]["independentSourceCount"] < 2:
        notes.append("Only one independent source group is represented; corroboration is not established.")
    if not record.get("countryCode"):
        notes.append("Country could not be resolved from the available evidence.")
    for field, label in (("technology", "AI technology"), ("industry", "industry"), ("aiSystemType", "AI system type")):
        if not record.get(field):
            notes.append(f"{label} is not specified in the source record.")
    if architecture["status"] == "INSUFFICIENT_EVIDENCE":
        notes.append("Available evidence is insufficient for architecture relevance analysis.")
    notes.append("Automated analysis has not been reviewed or approved by OOF®.")
    return notes


def build_assessment(record: dict, knowledge: KnowledgeLayer, version: int, supersedes: str | None, reason: str | None, created_at: str) -> dict:
    evidence = evidence_snapshot(record)
    architecture = architecture_analysis(record, knowledge)
    severity = severity_assessment(record, evidence)
    primary = architecture.get("primaryArchitecture")
    findings = []
    if primary:
        findings.append({
            "type": "Governance Signal",
            "statement": f"Available evidence indicates relevance to {primary['label']}.",
            "basis": primary["matchedTerms"],
            "status": "Automated / Not OOF Approved",
            "limitation": "Architecture relevance does not establish architecture failure, legal fault, or regulatory non-compliance.",
        })
    assessment_id = f"OOF-AII-ASMT-{record['id'].split('-')[-1]}-V{version}"
    return {
        "assessmentIdentity": assessment_id,
        "incidentId": record["id"],
        "analysisVersion": version,
        "engineVersion": ENGINE_VERSION,
        "architectureRegistryVersion": knowledge.manifest.get("buildId") or knowledge.manifest.get("buildFingerprint"),
        "knowledgeImpactFingerprint": knowledge.impact_fingerprint,
        "evidenceSnapshot": evidence,
        "severityAssessment": severity,
        "architectureAnalysis": architecture,
        "layerAnalysis": {
            "status": "AUTOMATED_ANALYSIS" if primary else "INSUFFICIENT_EVIDENCE",
            "governedMechanisms": primary.get("matchedTerms", []) if primary else [],
            "observedFactBoundary": "Source facts remain in the immutable incident record; this object contains generated interpretation only.",
        },
        "coverageAssessment": {
            "status": "UNDER_REVIEW" if primary else "INSUFFICIENT_EVIDENCE",
            "rationale": "Architecture relevance alone is insufficient to determine coverage or a governance gap.",
        },
        "governanceFindings": findings,
        "uncertainties": uncertainty_notes(record, evidence, architecture),
        "analysisType": "Automated",
        "humanReview": {"status": "Not performed", "reviewer": None, "reviewedAt": None},
        "oofApproved": False,
        "createdAt": created_at,
        "supersedes": supersedes,
        "reassessmentReason": reason,
    }


def changed_architectures(previous: dict, knowledge: KnowledgeLayer) -> set[str]:
    old = previous.get("architectureSignatures") or {}
    current = knowledge.signatures
    return {key for key in set(old) | set(current) if old.get(key) != current.get(key)}


def should_reassess(record: dict, latest: dict | None, knowledge: KnowledgeLayer, changed: set[str]) -> tuple[bool, str | None]:
    if latest is None:
        return True, "Initial V2 automated analysis"
    current_source_hash = content_hash(immutable_source_view(record))
    if latest.get("evidenceSnapshot", {}).get("incidentSourceHash") != current_source_hash:
        return True, "Incident evidence changed"
    if latest.get("engineVersion") != ENGINE_VERSION:
        return True, "Material analysis engine change"
    if not changed:
        return False, None
    prior_ids = {
        item.get("objectId") for item in [latest.get("architectureAnalysis", {}).get("primaryArchitecture")]
        + latest.get("architectureAnalysis", {}).get("contributingArchitectures", []) if item
    }
    if prior_ids & changed:
        return True, "Relevant OOF Knowledge Layer object changed"
    ranked_ids = {item["objectId"] for item in knowledge.rank(record)}
    if ranked_ids & changed:
        return True, "New or changed OOF knowledge may affect this incident"
    return False, None


def build(
    store_path: Path = STORE_PATH,
    analysis_path: Path = ANALYSIS_PATH,
    snapshot_path: Path = KNOWLEDGE_SNAPSHOT_PATH,
    knowledge_root: Path = KNOWLEDGE_ROOT,
    created_at: str | None = None,
) -> dict:
    records = read_json(store_path, {"incidents": []}).get("incidents", [])
    knowledge = KnowledgeLayer(knowledge_root)
    existing = read_json(analysis_path, {"assessments": []})
    assessments = existing.get("assessments", [])
    by_incident = defaultdict(list)
    for assessment in assessments:
        by_incident[assessment["incidentId"]].append(assessment)
    previous_snapshot = read_json(snapshot_path, {})
    changed = changed_architectures(previous_snapshot, knowledge)
    generated_at = created_at or now_iso()
    created = skipped = 0
    for record in records:
        history = sorted(by_incident[record["id"]], key=lambda item: item["analysisVersion"])
        latest = history[-1] if history else None
        required, reason = should_reassess(record, latest, knowledge, changed)
        if not required:
            skipped += 1
            continue
        version = (latest["analysisVersion"] + 1) if latest else 1
        assessment = build_assessment(
            record, knowledge, version,
            latest.get("assessmentIdentity") if latest else None,
            reason,
            generated_at,
        )
        assessments.append(assessment)
        by_incident[record["id"]].append(assessment)
        created += 1
    assessments.sort(key=lambda item: (item["incidentId"], item["analysisVersion"]))
    if created == 0:
        generated_at = existing.get("generatedAt", generated_at)
        snapshot_assessed_at = previous_snapshot.get("assessedAt", generated_at)
    else:
        snapshot_assessed_at = generated_at
    payload = {
        "schemaVersion": "2.0",
        "engineVersion": ENGINE_VERSION,
        "generatedAt": generated_at,
        "knowledgeLayer": {
            "source": "data/knowledge",
            "buildId": knowledge.manifest.get("buildId"),
            "buildFingerprint": knowledge.manifest.get("buildFingerprint"),
            "impactFingerprint": knowledge.impact_fingerprint,
            "architectureCount": len(knowledge.architectures),
            "retrievalMode": "structured lexical relational hybrid",
        },
        "assessments": assessments,
    }
    write_json(analysis_path, payload)
    write_json(snapshot_path, {
        "schemaVersion": "1.0",
        "engineVersion": ENGINE_VERSION,
        "knowledgeBuildId": knowledge.manifest.get("buildId"),
        "knowledgeImpactFingerprint": knowledge.impact_fingerprint,
        "architectureSignatures": knowledge.signatures,
        "assessedAt": snapshot_assessed_at,
    })
    return {"incidentCount": len(records), "assessmentsCreated": created, "assessmentsSkipped": skipped, "changedArchitectures": len(changed)}


def latest_assessments(path: Path = ANALYSIS_PATH) -> dict[str, dict]:
    payload = read_json(path, {"assessments": []})
    latest = {}
    for assessment in payload.get("assessments", []):
        current = latest.get(assessment["incidentId"])
        if current is None or assessment["analysisVersion"] > current["analysisVersion"]:
            latest[assessment["incidentId"]] = assessment
    return latest


def validate(path: Path = ANALYSIS_PATH, store_path: Path = STORE_PATH) -> list[str]:
    payload = read_json(path, {})
    errors = []
    records = read_json(store_path, {"incidents": []}).get("incidents", [])
    incident_ids = {record["id"] for record in records}
    seen = set()
    versions = defaultdict(list)
    for assessment in payload.get("assessments", []):
        identity = assessment.get("assessmentIdentity")
        if identity in seen:
            errors.append(f"Duplicate assessment identity: {identity}")
        seen.add(identity)
        incident_id = assessment.get("incidentId")
        if incident_id not in incident_ids:
            errors.append(f"Assessment references unknown incident: {incident_id}")
        versions[incident_id].append(assessment.get("analysisVersion"))
        if assessment.get("analysisType") != "Automated":
            errors.append(f"Unexpected analysis type: {identity}")
        if assessment.get("oofApproved") is not False:
            errors.append(f"Automated assessment must not be OOF approved: {identity}")
        if assessment.get("humanReview", {}).get("status") == "Completed":
            errors.append(f"Automated store cannot contain completed human review: {identity}")
        architecture = assessment.get("architectureAnalysis", {})
        items = [architecture.get("primaryArchitecture")] + architecture.get("contributingArchitectures", [])
        for item in (item for item in items if item):
            if not item.get("reasonForRelevance") or not item.get("supportingEvidence"):
                errors.append(f"Architecture assignment lacks explanation or evidence: {identity}")
    for incident_id, values in versions.items():
        if sorted(values) != list(range(1, max(values) + 1)):
            errors.append(f"Assessment versions are not continuous: {incident_id}")
    latest = latest_assessments(path)
    missing = incident_ids - set(latest)
    if missing:
        errors.append(f"Incidents without automated analysis: {len(missing)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "validate"))
    args = parser.parse_args()
    if args.command == "build":
        print(json.dumps(build(), indent=2))
    else:
        errors = validate()
        if errors:
            print("\n".join(errors))
            return 1
        print(f"Validated {len(latest_assessments())} latest automated incident assessments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
