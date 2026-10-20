#!/usr/bin/env python3
"""Build versioned, evidence-linked OOF incident intelligence assessments.

Source incident records are read-only. Generated analysis is stored separately,
remains explicitly unapproved, and consumes the existing OOF Knowledge Layer.
"""

from __future__ import annotations

import argparse
import ast
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
REVIEW_QUEUE_PATH = DATA_ROOT / "human-review-queue.json"
KNOWLEDGE_ROOT = ROOT / "data" / "knowledge"
ENGINE_VERSION = "3.4.1"
QUALITY_GATE_VERSION = "OOF-AII-QG-3.4.1.2"

PLACEHOLDER_VALUES = {"", "no", "none", "null", "unknown", "n a", "not specified", "unspecified"}
# These values are not prohibited in ordinary source prose.  They are rejected only
# when they appear as a standalone extracted analytical value or generated subject.
SEMANTIC_NOISE_VALUES = {"yes", "no", "been", "including", "while", "without", "otherwise", "previously", "whether"}
INVALID_ANALYTICAL_VALUES = PLACEHOLDER_VALUES | SEMANTIC_NOISE_VALUES
NORMALIZED_FIELDS = (
    "organization", "system", "technology", "industry", "aiSystemType",
    "impactTypes", "affectedParties",
)

STOPWORDS = {
    "about", "across", "after", "against", "architecture", "based", "before", "between",
    "complete", "core", "from", "governance", "governed", "incident", "index", "intelligence",
    "activity", "architecture", "control", "data", "human", "layer", "management", "method", "model",
    "module", "modules", "oof", "operational", "risk", "standard", "standards", "system", "systems", "that",
    "their", "these", "this", "through", "under", "using", "where", "which", "with",
    "including", "while", "without", "otherwise", "previously", "whether", "history",
    "historical", "collaboration", "collaborative", "yes", "no", "been",
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


def is_invalid_analytical_value(value) -> bool:
    """True when a value cannot be used as an extracted governance subject."""
    return normalized_text(value) in INVALID_ANALYTICAL_VALUES


def _parse_serialized_collection(value):
    """Parse source-export collections without executing or inventing data."""
    if not isinstance(value, str):
        return value
    candidate = value.strip()
    if not (candidate.startswith("[") and candidate.endswith("]")):
        return value
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(candidate)
        except (ValueError, SyntaxError, TypeError, json.JSONDecodeError):
            continue
        if isinstance(parsed, (list, tuple)):
            return list(parsed)
    return value


def _clean_source_value(value):
    value = _parse_serialized_collection(value)
    if isinstance(value, (list, tuple, set)):
        cleaned = []
        for item in value:
            normalized = normalized_text(item)
            if normalized in INVALID_ANALYTICAL_VALUES:
                continue
            text = str(item).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned
    if normalized_text(value) in INVALID_ANALYTICAL_VALUES:
        return None
    return str(value).strip() if value is not None else None


def normalized_incident_view(record: dict) -> tuple[dict, dict]:
    """Return an analytical view while retaining the immutable raw source record."""
    normalized = dict(record)
    transformations = []
    for field in NORMALIZED_FIELDS:
        raw = record.get(field)
        cleaned = _clean_source_value(raw)
        if field in {"impactTypes", "affectedParties"}:
            analytical = cleaned if isinstance(cleaned, list) else [cleaned] if cleaned else []
        else:
            analytical = "; ".join(cleaned) if isinstance(cleaned, list) else cleaned
        normalized[field] = analytical
        if raw != analytical:
            transformations.append({
                "field": field,
                "rawValue": raw,
                "normalizedValue": analytical,
                "reason": "placeholder removed" if analytical is None else "serialized collection normalized",
            })
    return normalized, {
        "policyVersion": "OOF-AII-NORM-3.2",
        "sourceRecordModified": False,
        "rawRecordHash": content_hash(immutable_source_view(record)),
        "normalizedFields": {field: normalized.get(field) for field in NORMALIZED_FIELDS},
        "transformations": transformations,
    }


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
        self.children_by_parent = defaultdict(list)
        for item in self.objects.values():
            parent_id = item.get("parentObjectId")
            if parent_id in self.objects:
                self.children_by_parent[parent_id].append(item)
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

    def _reference_candidate(self, item: dict, incident_terms: Counter[str]) -> dict | None:
        corpus = Counter()
        for field in ("canonicalName", "canonicalDefinition", "governedSpace", "coreQuestion", "category", "subcategory"):
            corpus.update(tokens(item.get(field)))
        matched = sorted(
            set(incident_terms) & set(corpus),
            key=lambda term: (-incident_terms[term] * min(corpus[term], 3), term),
        )
        score = sum(incident_terms[term] * min(corpus[term], 3) for term in matched)
        if not score:
            return None
        return {
            "objectId": item["id"], "name": item.get("canonicalName"), "artifactType": item.get("artifactType"),
            "canonicalUrl": item.get("canonicalUrl"), "matchedTerms": matched[:8], "score": score,
            "governedSpace": item.get("governedSpace"), "coreQuestion": item.get("coreQuestion"),
            "parentObjectId": item.get("parentObjectId"),
            "canonicalProvenance": {
                "knowledgeBuildId": self.manifest.get("buildId"),
                "contentHash": item.get("provenance", {}).get("contentHash"),
                "authorityState": item.get("authorityState"),
            },
        }

    def references(self, architecture_object_id: str, record: dict) -> list[dict]:
        """Return only the deepest methodology justified by incident evidence.

        Parent Standards and Core Modules are ranked inside the selected
        architecture. A module can only be emitted beneath a selected parent,
        and sparse records remain at architecture depth.
        """
        incident_terms = self._incident_terms(record)
        evidence_depth = sum(bool(record.get(field)) for field in (
            "summary", "system", "technology", "industry", "organization", "impactTypes", "affectedParties",
        ))
        if evidence_depth < 2 or len(incident_terms) < 3:
            return []
        parents = []
        for item in self.children.get(architecture_object_id, []):
            if item.get("artifactType") != "ParentStandard":
                continue
            candidate = self._reference_candidate(item, incident_terms)
            if candidate and candidate["score"] >= 4 and len(candidate["matchedTerms"]) >= 2:
                parents.append(candidate)
        if not parents:
            return []
        parent = sorted(parents, key=lambda item: (-item["score"], item["name"] or ""))[0]
        references = [parent]
        if evidence_depth < 4:
            return references
        modules = []
        for item in self.children_by_parent.get(parent["objectId"], []):
            if item.get("artifactType") != "CoreModule":
                continue
            candidate = self._reference_candidate(item, incident_terms)
            if candidate and candidate["score"] >= 6 and len(candidate["matchedTerms"]) >= 2:
                modules.append(candidate)
        if modules:
            references.append(sorted(modules, key=lambda item: (-item["score"], item["name"] or ""))[0])
        return references


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
    authorities = {item["authority"] for item in sources}
    verification_values = normalized_text(" ".join(str(item.get("verificationState") or "") for item in sources))
    if "disputed" in verification_values or "contradicted" in verification_values:
        public_status = "Contradicted / Disputed"
    elif not sources or not record.get("summary"):
        public_status = "Evidence Insufficient"
    elif "Official" in authorities:
        public_status = "Officially Documented"
    elif len(independence_keys) >= 2:
        public_status = "Independently Corroborated"
    else:
        public_status = "Source-Reported"
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
        "publicEvidenceStatus": public_status,
    }


def original_oof_report(record: dict, evidence: dict) -> dict:
    source = (evidence.get("sources") or [{}])[0]
    publisher = source.get("publisher") or "the identified public source"
    event_date = str(record.get("occurredAt") or record.get("reportedAt") or "")[:10]
    location = record.get("country") if record.get("country") not in (None, "Location not specified") else None
    context = ", ".join(value for value in (event_date, location) if value)
    opening = f"{publisher} reports that {record.get('summary') or record.get('title')}"
    if context:
        opening += f" ({context})."
    elif not opening.endswith("."):
        opening += "."
    limitation = (
        "OOF® has not independently verified this account. The description preserves source attribution and separates reported facts from the automated governance analysis below."
        if evidence.get("publicEvidenceStatus") == "Source-Reported"
        else "This OOF® incident report is evidence-bounded and does not constitute a finding of fault or liability."
    )
    return {
        "headline": record.get("title"),
        "report": opening,
        "sourceAttribution": publisher,
        "sourceUrl": source.get("url"),
        "eventDate": event_date or None,
        "evidenceStatus": evidence.get("publicEvidenceStatus"),
        "uncertaintyStatement": limitation,
    }


def prevention_guidance(record: dict, architecture: dict, gaps: list[str]) -> dict:
    primary = architecture.get("primaryArchitecture")
    if not primary:
        return {
            "governanceGapToExamine": "Establish the governed mechanism before selecting a preventive control.",
            "recommendedPreventiveControl": "Collect sufficient system, operator, decision, and outcome evidence before control selection.",
            "howToVerify": "Confirm the system identity, operating authority, event sequence, and effect through attributable records.",
            "relevantMethodology": [],
            "evidenceLimitation": (gaps or ["Available evidence does not justify architecture-level prevention guidance."])[0],
        }
    references = primary.get("relevantStandardsModules") or []
    mechanism = primary.get("governedMechanism") or "the reported governed mechanism"
    methodology = [{
        "name": item.get("name"), "artifactType": item.get("artifactType"),
        "canonicalUrl": item.get("canonicalUrl"), "objectId": item.get("objectId"),
    } for item in references[:2]]
    return {
        "governanceGapToExamine": f"Examine whether controls governing {mechanism} were defined, active, and accountable at the time of the reported event.",
        "recommendedPreventiveControl": f"Require an evidence-producing control for {mechanism}, with a named authority, intervention condition, and review owner.",
        "howToVerify": "Test the control against a representative failure scenario and retain the decision, intervention, and outcome evidence for independent review.",
        "relevantMethodology": methodology,
        "evidenceLimitation": (gaps or ["The recommendation is preliminary and should be adapted after incident-specific evidence review."])[0],
    }


def practical_checklist(record: dict, architecture: dict) -> list[dict]:
    primary = architecture.get("primaryArchitecture")
    mechanism = (primary or {}).get("governedMechanism") or "the reported AI activity"
    return [
        {"item": "Identify accountable authority", "verification": "Record who authorized, operated, and could stop the activity."},
        {"item": "Reconstruct the evidence chain", "verification": "Link source, system action, observation, consequence, and time."},
        {"item": "Test the preventive control", "verification": f"Demonstrate that the control detects or constrains {mechanism} under comparable conditions."},
        {"item": "Record residual uncertainty", "verification": "List unresolved facts and the evidence required to resolve them."},
    ]


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
        mechanism = ", ".join(candidate["matchedTerms"][:3]) or "the reported governance problem"
        deepest = references[0] if references else None
        methodology_focus = deepest.get("name") if deepest else candidate["label"]
        governance_focus = (
            deepest.get("coreQuestion") if deepest and deepest.get("coreQuestion")
            else f"How should {mechanism} be governed in the conditions described by the available incident evidence?"
        )
        results.append({
            **candidate,
            "role": "Primary" if index == 0 else "Contributing",
            "governedMechanism": ", ".join(candidate["matchedTerms"][:5]),
            "reasonForRelevance": (
                f"Available reporting describes {mechanism}. This makes {candidate['label']} relevant to examining "
                f"{methodology_focus} in this specific incident; relevance does not establish governance failure."
            ),
            "whyItMattersHere": (
                f"The reported {mechanism} concern falls within the governed questions represented by {candidate['label']}."
            ),
            "governanceFocus": governance_focus,
            "methodologyDepth": deepest.get("artifactType") if deepest else "Architecture",
            "supportingEvidence": [source.get("sourceId") for source in record.get("sources") or []],
            "confidence": round(confidence, 2),
            "uncertainty": "Automated retrieval; no authorized human review performed.",
            "relevantStandardsModules": references,
        })
    return {"status": "AUTOMATED_ANALYSIS", "primaryArchitecture": results[0], "contributingArchitectures": results[1:]}


def assessment_confidence(record: dict, evidence: dict, architecture: dict) -> str:
    if architecture["status"] == "INSUFFICIENT_EVIDENCE" or not record.get("summary"):
        return "Evidence Insufficient"
    source_count = evidence["corroboration"]["independentSourceCount"]
    populated = sum(bool(record.get(field)) for field in ("summary", "countryCode", "organization", "system", "technology", "impactTypes", "affectedParties"))
    if source_count >= 2 and populated >= 5:
        return "High"
    if source_count >= 2 or populated >= 5:
        return "Moderate"
    return "Limited"


def confidence_dimensions(record: dict, evidence: dict, architecture: dict) -> dict:
    source_count = evidence["corroboration"]["independentSourceCount"]
    source_score = min(1.0, source_count / 2)
    source_level = "Corroborated" if source_count >= 2 else "Single-source" if source_count == 1 else "No source"

    fields = ("summary", "countryCode", "organization", "system", "technology", "industry", "impactTypes", "affectedParties")
    populated = sum(bool(record.get(field)) for field in fields)
    extraction_score = populated / len(fields)
    extraction_level = "High" if extraction_score >= 0.75 else "Moderate" if extraction_score >= 0.5 else "Limited"

    primary = architecture.get("primaryArchitecture")
    if not primary:
        methodology_score = 0.0
        methodology_level = "Evidence Insufficient"
    else:
        term_count = len(primary.get("matchedTerms") or [])
        reference_depth = len(primary.get("relevantStandardsModules") or [])
        methodology_score = min(0.95, 0.35 + term_count * 0.08 + reference_depth * 0.08)
        methodology_level = "High" if methodology_score >= 0.75 else "Moderate" if methodology_score >= 0.55 else "Limited"
    return {
        "sourceCorroboration": {
            "level": source_level, "score": round(source_score, 2),
            "independentSourceCount": source_count,
            "disclosure": "Measures source-group corroboration only; it does not establish factual truth.",
        },
        "extractionCompleteness": {
            "level": extraction_level, "score": round(extraction_score, 2),
            "populatedFields": populated, "evaluatedFields": len(fields),
            "disclosure": "Measures populated source fields after deterministic normalization; it does not measure correctness.",
        },
        "methodologicalAssignment": {
            "level": methodology_level, "score": round(methodology_score, 2),
            "matchedTerms": (primary or {}).get("matchedTerms", []),
            "disclosure": "Measures automated assignment support; substantive correctness requires authorized human review.",
        },
    }


def incident_evidence(record: dict, evidence: dict) -> dict:
    sources = evidence.get("sources", [])
    reported = []
    if record.get("summary"):
        reported.append(record["summary"])
    elif record.get("title"):
        reported.append(record["title"])
    known = []
    if record.get("occurredAt"):
        known.append(f"The incident record identifies the event date as {str(record['occurredAt'])[:10]}.")
    if record.get("country") and record.get("country") != "Location not specified":
        known.append(f"The incident record identifies the location as {record['country']}.")
    unknowns = []
    if evidence["corroboration"]["independentSourceCount"] < 2:
        unknowns.append("Independent corroboration is not established in the available incident record.")
    if not record.get("system"):
        unknowns.append("The specific AI system is not established by the available record.")
    if not record.get("organization"):
        unknowns.append("The responsible operating organization is not established by the available record.")
    return {
        "sourcesUsed": [{
            "sourceId": item.get("sourceId"), "url": item.get("url"), "publisher": item.get("publisher"),
            "sourceType": item.get("authority"), "verificationState": item.get("verificationState"),
        } for item in sources],
        "knownFacts": known,
        "reportedClaims": reported,
        "materialUnknowns": unknowns,
        "evidenceState": evidence.get("corroboration", {}).get("status"),
    }


def primary_governance_problem(architecture: dict) -> str:
    primary = architecture.get("primaryArchitecture")
    if not primary:
        return "Available evidence does not establish a sufficiently specific governed problem for architecture assignment."
    mechanism = primary.get("governedMechanism") or "the reported activity"
    return (
        f"The incident appears to expose a governance problem involving {mechanism}. "
        "Available reporting supports preliminary methodological interpretation, not a finding of fault or non-compliance."
    )


def governance_relationship(architecture: dict) -> str:
    primary = architecture.get("primaryArchitecture")
    contributing = architecture.get("contributingArchitectures", [])
    if not primary:
        return "No architecture relationship is asserted because the governed space remains unresolved."
    if not contributing:
        return f"The available evidence currently supports one primary governed domain: {primary['label']}."
    labels = ", ".join(item["label"] for item in contributing)
    return (
        f"{primary['label']} frames the primary governed problem. {labels} contribute distinct questions. "
        "These relationships do not make the governed domains equivalent."
    )


def governance_questions(record: dict, architecture: dict, gaps: list[str]) -> list[str]:
    questions = []
    for item in [architecture.get("primaryArchitecture"), *architecture.get("contributingArchitectures", [])]:
        if item and item.get("governanceFocus") and item["governanceFocus"] not in questions:
            questions.append(item["governanceFocus"])
    if record.get("organization"):
        questions.append(f"What operational authority and controls applied to {record['organization']} at the relevant time?")
    else:
        questions.append("Who held operational authority for the reported system or activity at the relevant time?")
    if record.get("system") and not is_invalid_analytical_value(record["system"]):
        questions.append(f"What evidence would establish how {record['system']} produced or enabled the reported outcome?")
    else:
        questions.append("What evidence would establish how the relevant AI system produced or enabled the reported outcome?")
    if gaps:
        questions.append("What additional independent evidence is required to resolve the material evidence gaps?")
    unique = []
    for question in questions:
        if question not in unique:
            unique.append(question)
    return unique[:5]


def governance_insight(record: dict, architecture: dict, confidence_state: str) -> str | None:
    primary = architecture.get("primaryArchitecture")
    if not primary or confidence_state == "Evidence Insufficient":
        return None
    subject = record.get("system") or record.get("organization") or record.get("title") or "the reported AI activity"
    if is_invalid_analytical_value(subject):
        subject = record.get("title") or "the reported AI activity"
    focus = primary.get("governanceFocus") or "Which governance controls applied, and were they effective?"
    case_label = record.get("title") or "the source-reported incident"
    if confidence_state == "Limited":
        return (
        f"Available reporting on {case_label} indicates that {subject} raises a preliminary question for {primary['label']}: {focus} "
            "The current evidence does not yet establish whether the relevant control existed or was effective."
        )
    return (
        f"The source-reported case {case_label}, involving {subject}, raises a preliminary question for {primary['label']}: {focus} "
        "This automated interpretation does not establish fault, control failure, or legal responsibility."
    )


def semantic_output_problems(assessment: dict) -> list[str]:
    """Inspect generated analytical fields without treating ordinary prose as invalid."""
    problems = []
    architecture = assessment.get("architectureAnalysis") or {}
    for item in filter(None, [architecture.get("primaryArchitecture"), *(architecture.get("contributingArchitectures") or [])]):
        for term in item.get("matchedTerms") or []:
            if is_invalid_analytical_value(term):
                problems.append(f"invalid matched term: {term}")
        if is_invalid_analytical_value(item.get("governedMechanism")):
            problems.append(f"invalid governed mechanism: {item.get('governedMechanism')}")
    subject_pattern = r"\b(?:how|involving)\s+(yes|no|been|including|while|without|otherwise|previously|whether)\b"
    for field in ("incidentGovernanceInsight",):
        if re.search(subject_pattern, normalized_text(assessment.get(field)), flags=re.I):
            problems.append(f"invalid generated subject in {field}")
    for question in assessment.get("governanceQuestions") or []:
        if re.search(subject_pattern, normalized_text(question), flags=re.I):
            problems.append("invalid generated subject in governance question")
    return problems


def quality_outcomes(assessment: dict) -> dict:
    """Return separate outcomes; only a clean generated assessment can be public."""
    architecture = assessment.get("architectureAnalysis") or {}
    primary = architecture.get("primaryArchitecture")
    evidence = assessment.get("evidenceSnapshot") or {}
    structural = "PASS" if assessment.get("assessmentIdentity") and assessment.get("incidentId") and assessment.get("assessmentDisclosure") else "FAIL"
    semantic = "FAIL" if semantic_output_problems(assessment) else "PASS"
    methodological = "PASS" if primary and primary.get("canonicalUrl") else "REVIEW REQUIRED" if primary else "REVIEW REQUIRED"
    evidence_transparency = "PASS" if evidence.get("sources") and evidence.get("publicEvidenceStatus") else "FAIL"
    assessment_eligibility = "PUBLISHABLE" if structural == semantic == evidence_transparency == "PASS" else "PENDING"
    return {
        "structuralIntegrity": structural,
        "semanticIntegrity": semantic,
        "methodologicalSupport": methodological,
        "evidenceTransparency": evidence_transparency,
        "publicationEligibility": assessment_eligibility,
        "sourceRecordEligibility": "PUBLISHABLE",
        "preventionGuidanceEligibility": "WITHHELD_PENDING_INDEPENDENT_SUPPORT",
    }


def methodological_reasoning_chain(record: dict, architecture: dict, questions: list[str], insight: str | None) -> dict:
    primary = architecture.get("primaryArchitecture")
    references = primary.get("relevantStandardsModules", []) if primary else []
    parent = next((item for item in references if item.get("artifactType") == "ParentStandard"), None)
    module = next((item for item in references if item.get("artifactType") == "CoreModule"), None)
    return {
        "incidentEvidence": [source.get("sourceId") for source in record.get("sources") or []],
        "governedProblem": primary_governance_problem(architecture) if primary else None,
        "governedSpace": primary.get("label") if primary else None,
        "primaryArchitecture": primary.get("objectId") if primary else None,
        "contributingArchitectures": [item["objectId"] for item in architecture.get("contributingArchitectures", [])],
        "parentStandard": parent.get("objectId") if parent else None,
        "coreModule": module.get("objectId") if module else None,
        "governedMechanism": primary.get("governedMechanism") if primary else None,
        "governanceQuestions": questions,
        "incidentGovernanceInsight": insight,
        "deepestJustifiedLevel": module.get("artifactType") if module else parent.get("artifactType") if parent else "Architecture" if primary else "Unresolved",
    }


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
    return notes


def build_assessment(record: dict, knowledge: KnowledgeLayer, version: int, supersedes: str | None, reason: str | None, created_at: str) -> dict:
    raw_record = record
    record, normalization = normalized_incident_view(raw_record)
    evidence = evidence_snapshot(raw_record)
    architecture = architecture_analysis(record, knowledge)
    severity = severity_assessment(record, evidence)
    primary = architecture.get("primaryArchitecture")
    confidence_state = assessment_confidence(record, evidence, architecture)
    dimensions = confidence_dimensions(record, evidence, architecture)
    evidence_view = incident_evidence(record, evidence)
    gaps = uncertainty_notes(record, evidence, architecture)
    questions = governance_questions(record, architecture, gaps)
    insight = governance_insight(record, architecture, confidence_state)
    report = original_oof_report(record, evidence)
    prevention = prevention_guidance(record, architecture, gaps)
    findings = []
    for item in [primary, *architecture.get("contributingArchitectures", [])]:
        if not item:
            continue
        finding_status = "Supported" if evidence["corroboration"]["independentSourceCount"] >= 2 else "Indicated"
        finding = f"Available evidence {finding_status.casefold()} relevance to {item['label']} for the reported {item.get('governedMechanism') or 'governance problem'}."
        findings.append({
            "type": "Governance Signal",
            "finding": finding,
            "statement": finding,
            "evidenceBasis": item["supportingEvidence"],
            "basis": item["matchedTerms"],
            "architectureReference": item["objectId"],
            "confidenceState": confidence_state,
            "status": finding_status,
            "limitation": "Architecture relevance does not establish architecture failure, legal fault, liability, or regulatory non-compliance.",
        })
    assessment_id = f"OOF-AII-ASMT-{record['id'].split('-')[-1]}-V{version}"
    assessment = {
        "assessmentIdentity": assessment_id,
        "incidentId": record["id"],
        "analysisVersion": version,
        "engineVersion": ENGINE_VERSION,
        "architectureRegistryVersion": knowledge.manifest.get("buildId") or knowledge.manifest.get("buildFingerprint"),
        "knowledgeImpactFingerprint": knowledge.impact_fingerprint,
        "assessmentLabel": "Automated Preliminary Governance Assessment",
        "assessmentDisclosure": "Generated from available public incident evidence using OOF® governance methodology. It is not an official investigation, legal determination, regulatory finding, certification, or OOF® Approved Assessment.",
        "assessmentConfidence": confidence_state,
        "confidenceDimensions": dimensions,
        "sourceNormalization": normalization,
        "evidenceSnapshot": evidence,
        "incidentEvidence": evidence_view,
        "oofIncidentReport": report,
        "severityAssessment": severity,
        "architectureAnalysis": architecture,
        "primaryGovernanceProblem": primary_governance_problem(architecture),
        "governanceRelationship": governance_relationship(architecture),
        "governanceQuestions": questions,
        "incidentGovernanceInsight": insight,
        "preventionGuidance": prevention,
        "practicalChecklist": practical_checklist(record, architecture),
        "governanceFailurePattern": {
            "primaryArchitectureId": primary.get("architectureId") if primary else None,
            "mechanisms": primary.get("matchedTerms", [])[:5] if primary else [],
            "patternKey": content_hash({
                "architecture": primary.get("architectureId") if primary else None,
                "mechanisms": sorted((primary.get("matchedTerms") or [])[:3]) if primary else [],
            })[:16],
        },
        "methodologicalReasoningChain": methodological_reasoning_chain(record, architecture, questions, insight),
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
        "evidenceGaps": gaps,
        "uncertainties": gaps,
        "analysisType": "Automated",
        "humanReview": {"status": "Not performed", "reviewer": None, "reviewedAt": None},
        "oofApproved": False,
        "createdAt": created_at,
        "supersedes": supersedes,
        "reassessmentReason": reason,
    }
    assessment["qualityGateVersion"] = QUALITY_GATE_VERSION
    assessment["qualityOutcomes"] = quality_outcomes(assessment)
    return assessment


def changed_architectures(previous: dict, knowledge: KnowledgeLayer) -> set[str]:
    old = previous.get("architectureSignatures") or {}
    current = knowledge.signatures
    return {key for key in set(old) | set(current) if old.get(key) != current.get(key)}


def should_reassess(record: dict, latest: dict | None, knowledge: KnowledgeLayer, changed: set[str]) -> tuple[bool, str | None]:
    if latest is None:
        return True, "Initial automated analysis"
    current_source_hash = content_hash(immutable_source_view(record))
    if latest.get("evidenceSnapshot", {}).get("incidentSourceHash") != current_source_hash:
        return True, "Incident evidence changed"
    if latest.get("engineVersion") != ENGINE_VERSION:
        return True, "Material analysis engine change"
    if latest.get("qualityGateVersion") != QUALITY_GATE_VERSION:
        return True, "Production semantic quality gate remediation"
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
    backfill_report_path: Path | None = None,
    review_queue_path: Path | None = None,
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
    failures = []
    for record in records:
        history = sorted(by_incident[record["id"]], key=lambda item: item["analysisVersion"])
        latest = history[-1] if history else None
        required, reason = should_reassess(record, latest, knowledge, changed)
        if not required:
            skipped += 1
            continue
        version = (latest["analysisVersion"] + 1) if latest else 1
        try:
            assessment = build_assessment(
                record, knowledge, version,
                latest.get("assessmentIdentity") if latest else None,
                reason,
                generated_at,
            )
        except Exception as exc:  # A failed backfill record must remain visible and retryable.
            failures.append({"incidentId": record.get("id"), "error": f"{type(exc).__name__}: {exc}"})
            continue
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
        "schemaVersion": "3.0",
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
    report_path = backfill_report_path or analysis_path.with_name("v3-backfill-report.json")
    if created or failures or not report_path.exists():
        write_json(report_path, {
            "schemaVersion": "3.0",
            "engineVersion": ENGINE_VERSION,
            "generatedAt": generated_at,
            "sourceRecordsModified": False,
            "incidentCount": len(records),
            "assessmentsCreated": created,
            "assessmentsSkipped": skipped,
            "generationFailures": failures,
        })
    queue_path = review_queue_path or (REVIEW_QUEUE_PATH if analysis_path == ANALYSIS_PATH else analysis_path.with_name("human-review-queue.json"))
    write_json(queue_path, build_review_queue(assessments, records, generated_at))
    return {"incidentCount": len(records), "assessmentsCreated": created, "assessmentsSkipped": skipped, "changedArchitectures": len(changed), "generationFailures": len(failures)}


def latest_assessments(path: Path = ANALYSIS_PATH) -> dict[str, dict]:
    payload = read_json(path, {"assessments": []})
    latest = {}
    for assessment in payload.get("assessments", []):
        current = latest.get(assessment["incidentId"])
        if current is None or assessment["analysisVersion"] > current["analysisVersion"]:
            latest[assessment["incidentId"]] = assessment
    return latest


def build_review_queue(assessments: list[dict], records: list[dict], generated_at: str | None = None) -> dict:
    records_by_id = {item["id"]: item for item in records}
    latest = {}
    for assessment in assessments:
        incident_id = assessment["incidentId"]
        if assessment["analysisVersion"] > latest.get(incident_id, {}).get("analysisVersion", 0):
            latest[incident_id] = assessment
    queue = []
    for incident_id, assessment in sorted(latest.items()):
        reasons = []
        severity = assessment.get("severityAssessment", {}).get("level")
        methodology = assessment.get("confidenceDimensions", {}).get("methodologicalAssignment", {}).get("level")
        record = records_by_id.get(incident_id, {})
        source_count = assessment.get("evidenceSnapshot", {}).get("corroboration", {}).get("independentSourceCount", 0)
        if severity in {"High", "Critical"}:
            reasons.append(f"{severity} automated severity")
        if methodology in {"Limited", "Evidence Insufficient"}:
            reasons.append("weak or unresolved methodological assignment")
        if source_count < 2 and re.search(r"\b(caused|causing|resulted in|led to)\b", normalized_text(record.get("title"))):
            reasons.append("causal wording with single-source evidence")
        if reasons:
            queue.append({
                "incidentId": incident_id,
                "assessmentIdentity": assessment.get("assessmentIdentity"),
                "priority": "Urgent" if severity == "Critical" else "High" if severity == "High" else "Standard",
                "reasons": reasons,
                "status": "Awaiting authorized human review",
                "autoApprovalPermitted": False,
            })
    return {
        "schemaVersion": "1.0", "engineVersion": ENGINE_VERSION,
        "generatedAt": generated_at or now_iso(), "reviewRequired": len(queue), "items": queue,
    }


def validate(path: Path = ANALYSIS_PATH, store_path: Path = STORE_PATH) -> list[str]:
    payload = read_json(path, {})
    errors = []
    records = read_json(store_path, {"incidents": []}).get("incidents", [])
    incident_ids = {record["id"] for record in records}
    knowledge = KnowledgeLayer()
    knowledge_ids = set(knowledge.objects)
    allowed_confidence = {"High", "Moderate", "Limited", "Evidence Insufficient"}
    seen = set()
    versions = defaultdict(list)
    latest_versions = {
        assessment.get("incidentId"): max(
            candidate.get("analysisVersion", 0)
            for candidate in payload.get("assessments", [])
            if candidate.get("incidentId") == assessment.get("incidentId")
        )
        for assessment in payload.get("assessments", [])
    }
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
        is_latest_current = (
            assessment.get("engineVersion") == ENGINE_VERSION
            and assessment.get("analysisVersion") == latest_versions.get(incident_id)
        )
        if is_latest_current:
            if assessment.get("assessmentConfidence") not in allowed_confidence:
                errors.append(f"Invalid categorical assessment confidence: {identity}")
            questions = assessment.get("governanceQuestions") or []
            if not 1 <= len(questions) <= 5:
                errors.append(f"Assessment must contain 1-5 governance questions: {identity}")
            if any(re.search(r"\b(no|unknown|n a|not specified)\b", normalized_text(question)) for question in questions):
                errors.append(f"Governance question contains a source placeholder: {identity}")
            if not assessment.get("assessmentDisclosure"):
                errors.append(f"Assessment disclosure is missing: {identity}")
            dimensions = assessment.get("confidenceDimensions") or {}
            if set(dimensions) != {"sourceCorroboration", "extractionCompleteness", "methodologicalAssignment"}:
                errors.append(f"Three confidence dimensions are missing: {identity}")
            normalization = assessment.get("sourceNormalization") or {}
            if normalization.get("sourceRecordModified") is not False or not normalization.get("rawRecordHash"):
                errors.append(f"Source normalization provenance is missing: {identity}")
            bad_terms = PLACEHOLDER_VALUES | {"including", "while", "without", "otherwise", "previously", "whether"}
            architecture_for_terms = assessment.get("architectureAnalysis", {})
            evidence_terms = {
                normalized_text(term)
                for item in [architecture_for_terms.get("primaryArchitecture"), *architecture_for_terms.get("contributingArchitectures", [])]
                if item for term in item.get("matchedTerms", [])
            }
            if evidence_terms & bad_terms:
                errors.append(f"Weak or placeholder evidence term found: {identity}")
            if assessment.get("qualityGateVersion") != QUALITY_GATE_VERSION:
                errors.append(f"Production quality gate version is missing: {identity}")
            outcomes = assessment.get("qualityOutcomes") or {}
            required_outcomes = {"structuralIntegrity", "semanticIntegrity", "methodologicalSupport", "evidenceTransparency", "publicationEligibility"}
            if not required_outcomes <= set(outcomes):
                errors.append(f"Quality outcomes are incomplete: {identity}")
            if semantic_output_problems(assessment):
                errors.append(f"Semantic integrity failure: {identity}")
            for finding in assessment.get("governanceFindings") or []:
                if not finding.get("evidenceBasis") or not finding.get("architectureReference") or not finding.get("status"):
                    errors.append(f"Governance finding lacks evidence, architecture, or status: {identity}")
        architecture = assessment.get("architectureAnalysis", {})
        items = [architecture.get("primaryArchitecture")] + architecture.get("contributingArchitectures", [])
        chain = assessment.get("methodologicalReasoningChain")
        if is_latest_current and not chain:
            errors.append(f"Methodological reasoning chain is missing: {identity}")
        for item in (item for item in items if item):
            if not item.get("reasonForRelevance") or not item.get("supportingEvidence"):
                errors.append(f"Architecture assignment lacks explanation or evidence: {identity}")
            if item.get("objectId") not in knowledge_ids:
                errors.append(f"Architecture assignment references unknown knowledge object: {identity}")
            references = item.get("relevantStandardsModules") or []
            parent_ids = {reference.get("objectId") for reference in references if reference.get("artifactType") == "ParentStandard"}
            for reference in references:
                object_id = reference.get("objectId")
                canonical = knowledge.objects.get(object_id)
                if canonical is None:
                    errors.append(f"Methodology reference is not canonical: {identity} -> {object_id}")
                    continue
                if canonical.get("architectureId") != item.get("objectId"):
                    errors.append(f"Methodology reference belongs to another architecture: {identity} -> {object_id}")
                if reference.get("name") != canonical.get("canonicalName") or reference.get("canonicalUrl") != canonical.get("canonicalUrl"):
                    errors.append(f"Methodology reference name or URL is stale: {identity} -> {object_id}")
                if (
                    is_latest_current
                    and reference.get("artifactType") == "CoreModule"
                    and canonical.get("parentObjectId") not in parent_ids
                ):
                    errors.append(f"Core Module lacks its selected Parent Standard: {identity} -> {object_id}")
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
