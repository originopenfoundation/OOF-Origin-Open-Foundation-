#!/usr/bin/env python3
"""Build the report-only OOF machine-readable knowledge infrastructure."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote, unquote


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_ai_compatibility as discovery  # noqa: E402
import build_architecture_registry as architecture_source  # noqa: E402


SCHEMA_VERSION = "1.1"
EXTRACTOR_VERSION = "oof-knowledge-infrastructure/1.1"
BASE_URL = "https://originopenfoundation.org/"
OUTPUT_RELATIVE = Path("data/knowledge")
ARCHITECTURE_INDEX_PATH = "data/oof-architecture-registry.json"
COMPLETE_ARCHITECTURE_INDEX_PATH = "oof-structured-architecture-index.html"
AUTHORITY_STATES = (
    "CANONICAL_AUTHORITATIVE",
    "SUPPORTING_CITABLE",
    "REVIEW_REQUIRED",
    "QUARANTINED",
)
PUBLIC_CONSUMERS = [
    "public",
    "LaRA",
    "GIE",
    "OOF-agents",
    "OOF-tools",
    "OOF-search",
    "authorized-machine-consumer",
]
TOKEN_STOPWORDS = {
    "a", "about", "an", "and", "architecture", "as", "at", "by", "for", "from", "governance",
    "in", "index", "is", "map", "module", "of", "oof", "on", "or", "standard", "the", "to", "with",
}
ORIGIN_ID_RE = re.compile(r"\bOOF-OID-(?:[A-Z0-9]+-)+\d{4}-\d{2}-\d{2}-\d{4}\b")
LANGUAGE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-(?:[A-Z]{2}|\d{3}))?$")


def git_value(format_string: str, source_path: str) -> str:
    try:
        return subprocess.run(
            ["git", "log", "-1", f"--format={format_string}", "--", source_path],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


SOURCE_COMMIT = git_value("%H", COMPLETE_ARCHITECTURE_INDEX_PATH)
GENERATED_TIMESTAMP = git_value("%cI", COMPLETE_ARCHITECTURE_INDEX_PATH)
BUILD_ID = f"OOF-KI-1.1-{SOURCE_COMMIT[:12]}"


def dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def clean(value: str | None) -> str:
    return discovery.clean_text(value or "")


def normalize(value: str | None) -> str:
    text = clean(value).casefold().replace("®", "").replace("™", "")
    text = re.sub(r"\babout\b", " ", text)
    text = re.sub(r"\bcomplete standards\s*&\s*modules index\b", " ", text)
    text = re.sub(r"\barchitecture (?:map|index)\b", " ", text)
    text = re.sub(r"\b(?:question|standards|module|site) index\b", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def valid_origin_id(value: str | None) -> str:
    match = ORIGIN_ID_RE.search(clean(value))
    return match.group(0) if match else ""


def acronym_from(value: str) -> str | None:
    matches = re.findall(r"\(([A-Z][A-Z0-9-]{1,15})(?:®|™)?\)", value)
    if matches:
        return matches[-1]
    leading = re.match(r"^([A-Z][A-Z0-9-]{1,15})(?:®|™)?(?:\s|\s*[—-])", value)
    return leading.group(1) if leading else None


def artifact_type(record: dict) -> str:
    explicit = clean(record["fields"].get("Type"))
    value = f"{explicit} {record['title']} {record['relative']}".casefold()
    if "core module" in value or re.search(r"\bmodule\b", value):
        return "CoreModule"
    if "parent standard" in value or re.search(r"\bstandard\b", value):
        return "ParentStandard"
    if "architecture" in value:
        return "Architecture"
    if "methodology" in value:
        return "Methodology"
    if "assessment" in value:
        return "Assessment"
    if "service" in value:
        return "Service"
    if "tool" in value or "engine" in value or "platform" in value:
        return "Tool"
    if "definition" in value:
        return "Definition"
    return "Reference"


def representation_type(record: dict) -> str:
    value = f"{record['title']} {record['relative']}".casefold()
    if "architecture map" in value:
        return "ArchitectureMap"
    if "complete standards" in value and "modules index" in value:
        return "StandardsModulesIndex"
    if "question index" in value or "questions" in value:
        return "QuestionIndex"
    if "translation" in value or record.get("language", "en") != "en":
        return "Translation"
    if record["title"].casefold().startswith("about ") or " about " in f" {record['title'].casefold()} ":
        return "AboutStandard" if artifact_type(record) == "ParentStandard" else "AboutArchitecture" if artifact_type(record) == "Architecture" else "About"
    if "index" in value:
        return "Index"
    if artifact_type(record) == "ParentStandard":
        return "CanonicalStandard"
    if artifact_type(record) == "Architecture":
        return "CanonicalArchitecture"
    return "CanonicalArtifact" if valid_origin_id(record["fields"].get("OriginID")) else "SupportingPage"


def section_value(source: str, heading: str) -> str | None:
    match = re.search(
        rf"<h[1-6]\b[^>]*>\s*{re.escape(heading)}\s*</h[1-6]>\s*<p\b[^>]*>(.*?)</p>",
        source,
        re.I | re.S,
    )
    if not match:
        return None
    value = clean(re.sub(r"<[^>]+>", " ", match.group(1)))
    return value or None


def source_hash(record: dict) -> str:
    source = discovery.BLOCK_RE.sub("", record["source"])
    return sha256_bytes(source.encode("utf-8"))


def normalized_language(record: dict) -> str:
    match = re.search(r"<html\b[^>]*\blang=[\"']([^\"']+)", record["source"], re.I)
    candidate = (match.group(1) if match else record.get("language") or "en").strip()
    aliases = {"english": "en", "eng": "en", "sk": "sk", "slovak": "sk"}
    candidate = aliases.get(candidate.casefold(), candidate)
    return candidate if LANGUAGE_RE.fullmatch(candidate) else "en"


def provenance(source_path: str, source_url: str, content_hash: str) -> dict:
    return {
        "sourcePath": source_path,
        "sourceUrl": source_url,
        "repositoryCommit": SOURCE_COMMIT,
        "buildId": BUILD_ID,
        "contentHash": content_hash,
        "extractorVersion": EXTRACTOR_VERSION,
        "generatedTimestamp": GENERATED_TIMESTAMP,
    }


def architecture_snapshot(item: dict) -> dict:
    primary = item.get("primaryPage") or {}
    return {
        "acronym": clean(item.get("acronym")),
        "displayName": clean(item.get("displayName")),
        "name": clean(item.get("name")),
        "status": clean(item.get("status")),
        "primaryUrl": clean(primary.get("url")),
        "standardCount": int(item.get("standardCount", len(item.get("standards", [])))),
        "standards": sorted((clean(value.get("name")), clean(value.get("url"))) for value in item.get("standards", [])),
    }


def cross_validate_architecture(index_item: dict | None, complete_item: dict | None) -> dict:
    fields = ("acronym", "displayName", "name", "status", "standardCount", "standards")
    index_value = architecture_snapshot(index_item) if index_item else None
    complete_value = architecture_snapshot(complete_item) if complete_item else None
    conflicts = []
    if not index_value or not complete_value:
        conflicts.append({"field": "membership", "architectureIndex": bool(index_value), "completeArchitectureIndex": bool(complete_value)})
    else:
        for field in fields:
            if index_value[field] != complete_value[field]:
                conflicts.append({"field": field, "architectureIndex": index_value[field], "completeArchitectureIndex": complete_value[field]})
    if not conflicts:
        result = "PASS"
        authority_state = "CANONICAL_AUTHORITATIVE"
    elif index_value and complete_value and all(item["field"] not in {"acronym", "membership"} for item in conflicts):
        result = "PARTIAL"
        authority_state = "SUPPORTING_CITABLE"
    else:
        result = "CONFLICT"
        authority_state = "QUARANTINED" if any(item["field"] in {"acronym", "membership"} for item in conflicts) else "REVIEW_REQUIRED"
    return {"result": result, "authorityState": authority_state, "conflicts": conflicts}


def authority_for(rep_type: str, mapped: bool, relative: str) -> tuple[str, list[str], str]:
    if relative == "oof-structured-architecture-index.html":
        return "canonical", ["architectureIdentity", "registryMembership"], "designatedArchitectureIndex"
    if rep_type == "ArchitectureMap" and mapped:
        return "canonical", ["architectureStructure", "architectureComposition"], "approvedArchitectureRegistry"
    if rep_type in {"CanonicalStandard", "CanonicalArchitecture", "CanonicalArtifact"} and mapped:
        return "canonical", ["canonicalDefinition", "governedSpace", "canonicalArtifactContent"], "explicitObjectIdentity"
    if rep_type in {"StandardsModulesIndex", "QuestionIndex", "Index"}:
        return "index", ["indexFunction"], "explicitIndexRepresentation"
    if rep_type.startswith("About"):
        return "explanatory", ["explanation"], "explanatoryRepresentation"
    if rep_type == "Translation":
        return "translation", ["languageRepresentation"], "derivedLanguageRepresentation"
    return "supporting", ["discovery"], "pageRepresentation"


def object_record(object_id: str, name: str, kind: str, canonical_url: str | None, identity_basis: str, record: dict | None = None, authority_state: str = "CANONICAL_AUTHORITATIVE") -> dict:
    fields = record["fields"] if record else {}
    item = {
        "id": object_id,
        "canonicalName": clean(name),
        "acronym": acronym_from(name),
        "artifactType": kind,
        "subtype": clean(fields.get("Type")) or None,
        "canonicalUrl": canonical_url,
        "representations": [],
        "architectureId": None,
        "parentObjectId": None,
        "category": clean(fields.get("Category")) or None,
        "subcategory": clean(fields.get("Subcategory")) or None,
        "canonicalDefinition": section_value(record["source"], "Canonical Definition") if record else None,
        "governedSpace": clean(fields.get("Governed Space")) or None,
        "coreQuestion": section_value(record["source"], "Core Question") if record else None,
        "status": clean(fields.get("Status")) or "published",
        "version": clean(fields.get("Version")) or None,
        "dates": {"publicationDate": clean(fields.get("Publication Date")) or None},
        "language": normalized_language(record) if record else "en",
        "visibility": "public",
        "allowedConsumers": PUBLIC_CONSUMERS,
        "identityBasis": identity_basis,
        "authorityState": authority_state,
        "sourceAuthority": {
            "state": authority_state,
            "domains": ["architectureTruth"] if kind == "Architecture" else ["objectIdentity", "canonicalArtifactContent"],
            "basis": identity_basis,
        },
        "provenance": provenance(
            record["relative"] if record else COMPLETE_ARCHITECTURE_INDEX_PATH,
            record["canonical"] if record else (canonical_url or discovery.canonical_url(COMPLETE_ARCHITECTURE_INDEX_PATH)),
            source_hash(record) if record else sha256_file(ROOT / COMPLETE_ARCHITECTURE_INDEX_PATH),
        ),
    }
    return item


def relation_id(source: str, kind: str, target: str, state: str) -> str:
    digest = sha256_bytes(f"{source}|{kind}|{target}|{state}".encode("utf-8"))[:20]
    return f"OOF-REL-{digest.upper()}"


def build(output_root: Path) -> dict:
    output = output_root / OUTPUT_RELATIVE
    paths = discovery.public_pages()
    records = [record for record in discovery.inspect_pages(paths) if discovery.alias_target(record["relative"]) is None]
    records_by_relative = {record["relative"]: record for record in records}
    records_by_url = {record["canonical"]: record for record in records}
    architecture_registry = json.loads((ROOT / "data/oof-architecture-registry.json").read_text(encoding="utf-8"))
    complete_architectures = architecture_source.parse_index()
    architecture_source.parse_navigation(complete_architectures)
    complete_by_acronym = {item["acronym"]: item for item in complete_architectures}
    index_by_acronym = {item["acronym"]: item for item in architecture_registry.get("architectures", [])}
    architecture_validation = []
    for acronym in sorted(set(index_by_acronym) | set(complete_by_acronym)):
        result = cross_validate_architecture(index_by_acronym.get(acronym), complete_by_acronym.get(acronym))
        result.update({
            "acronym": acronym,
            "architectureIndexSource": ARCHITECTURE_INDEX_PATH,
            "completeArchitectureIndexSource": COMPLETE_ARCHITECTURE_INDEX_PATH,
            "candidateCanonicalUrl": discovery.canonical_url((((index_by_acronym.get(acronym) or complete_by_acronym.get(acronym) or {}).get("primaryPage") or {}).get("url", ""))),
            "reviewReason": None if result["result"] == "PASS" else "Canonical source fields do not fully agree; no automatic promotion was applied.",
            "provenance": provenance(
                ARCHITECTURE_INDEX_PATH,
                discovery.canonical_url(ARCHITECTURE_INDEX_PATH),
                sha256_file(ROOT / ARCHITECTURE_INDEX_PATH),
            ),
        })
        architecture_validation.append(result)
    validation_by_acronym = {item["acronym"]: item for item in architecture_validation}
    search_index_hash = sha256_file(ROOT / "search-index.json")

    origin_groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        origin_id = valid_origin_id(record["fields"].get("OriginID"))
        if origin_id:
            origin_groups[origin_id].append(record)
    duplicates = {key: value for key, value in origin_groups.items() if len(value) > 1}
    unique_origin_ids = {key for key, value in origin_groups.items() if len(value) == 1}

    objects: dict[str, dict] = {}
    rep_to_object: dict[str, str] = {}
    authoritative: list[dict] = []

    def add_authoritative(source: str, kind: str, target: str, basis: str, source_url: str) -> None:
        key = (source, kind, target, "AUTHORITATIVE")
        if key in {(item["sourceId"], item["relationshipType"], item["targetId"], item["authorityState"]) for item in authoritative}:
            return
        authoritative.append({
            "id": relation_id(*key),
            "sourceId": source,
            "targetId": target,
            "relationshipType": kind,
            "authorityState": "AUTHORITATIVE",
            "authorityBasis": basis,
            "sourceUrl": source_url,
            "status": "active",
            "sourceAuthority": {"state": "CANONICAL_AUTHORITATIVE", "basis": basis},
            "provenance": provenance(COMPLETE_ARCHITECTURE_INDEX_PATH, discovery.canonical_url(COMPLETE_ARCHITECTURE_INDEX_PATH), sha256_file(ROOT / COMPLETE_ARCHITECTURE_INDEX_PATH)),
        })

    architecture_objects: dict[str, str] = {}
    standard_name_map: dict[str, list[str]] = defaultdict(list)
    for architecture in architecture_registry.get("architectures", []):
        object_id = f"OOF-KO-ARCH-{architecture['id'].upper()}"
        architecture_objects[architecture["id"]] = object_id
        primary_url = discovery.canonical_url(architecture["primaryPage"]["url"])
        primary_record = records_by_url.get(primary_url)
        objects[object_id] = object_record(
            object_id,
            architecture["displayName"],
            "Architecture",
            primary_url,
            "approvedArchitectureRegistryId",
            primary_record,
            validation_by_acronym[architecture["acronym"]]["authorityState"],
        )
        objects[object_id]["acronym"] = architecture["acronym"]
        objects[object_id]["status"] = architecture["status"]
        objects[object_id]["sourceAuthority"] = {
            "state": validation_by_acronym[architecture["acronym"]]["authorityState"],
            "domains": ["architectureIdentity", "registryMembership", "architectureStatus", "architectureHierarchy"],
            "basis": "architectureCanonicalCrossValidation",
            "sources": [ARCHITECTURE_INDEX_PATH, COMPLETE_ARCHITECTURE_INDEX_PATH],
            "validationResult": validation_by_acronym[architecture["acronym"]]["result"],
        }
        for page in architecture.get("pages", []):
            url = discovery.canonical_url(page["url"])
            if url in records_by_url:
                rep_to_object[url + "#webpage"] = object_id
        for position, standard in enumerate(architecture.get("standards", []), 1):
            standard_url = discovery.canonical_url(standard["url"])
            standard_record = records_by_url.get(standard_url)
            origin_id = valid_origin_id(standard_record["fields"].get("OriginID")) if standard_record else ""
            standard_id = origin_id if origin_id in unique_origin_ids else f"OOF-KO-STD-{architecture['id'].upper()}-{position:02d}"
            if standard_id not in objects:
                objects[standard_id] = object_record(
                    standard_id,
                    standard["name"],
                    "ParentStandard",
                    standard_url,
                    "existingOriginID" if origin_id in unique_origin_ids else "approvedArchitectureHierarchyCoordinate",
                    standard_record,
                )
            objects[standard_id]["architectureId"] = object_id
            standard_name_map[normalize(standard["name"])].append(standard_id)
            if standard_record:
                rep_to_object[standard_url + "#webpage"] = standard_id
            add_authoritative(object_id, "containsStandard", standard_id, "approvedArchitectureRegistry", primary_url)
            add_authoritative(standard_id, "belongsToArchitecture", object_id, "approvedArchitectureRegistry", standard_url)

    for origin_id in sorted(unique_origin_ids):
        record = origin_groups[origin_id][0]
        rep_id = record["canonical"] + "#webpage"
        if rep_id in rep_to_object:
            continue
        kind = artifact_type(record)
        objects[origin_id] = object_record(origin_id, record["title"], kind, record["canonical"], "existingOriginID", record)
        rep_to_object[rep_id] = origin_id
        if kind == "ParentStandard":
            standard_name_map[normalize(record["title"])].append(origin_id)

    architecture_aliases: dict[str, str] = {}
    for architecture in architecture_registry.get("architectures", []):
        oid = architecture_objects[architecture["id"]]
        for value in (architecture["id"], architecture["acronym"], architecture["displayName"], architecture["name"]):
            architecture_aliases[normalize(value)] = oid

    for object_id, item in list(objects.items()):
        if item["artifactType"] != "CoreModule":
            continue
        record = records_by_url.get(item["canonicalUrl"] or "")
        if not record:
            continue
        parent_name = clean(record["fields"].get("Parent Standard"))
        candidates = standard_name_map.get(normalize(parent_name), []) if parent_name else []
        if len(set(candidates)) == 1:
            parent_id = candidates[0]
            item["parentObjectId"] = parent_id
            item["architectureId"] = objects[parent_id].get("architectureId")
            add_authoritative(parent_id, "containsModule", object_id, "explicitParentStandardMetadata", record["canonical"])
            add_authoritative(object_id, "parentStandard", parent_id, "explicitParentStandardMetadata", record["canonical"])
        architecture_name = clean(record["fields"].get("Architecture") or record["fields"].get("Architecture Family"))
        architecture_id = architecture_aliases.get(normalize(architecture_name)) if architecture_name else None
        if architecture_id and not item.get("architectureId"):
            item["architectureId"] = architecture_id
            add_authoritative(object_id, "belongsToArchitecture", architecture_id, "explicitArchitectureMetadata", record["canonical"])

    representations = []
    for record in records:
        rep_id = record["canonical"] + "#webpage"
        mapped_id = rep_to_object.get(rep_id)
        rep_type = representation_type(record)
        role, domains, basis = authority_for(rep_type, bool(mapped_id), record["relative"])
        identity_status = "resolved" if mapped_id else "unresolved"
        authority_state = "CANONICAL_AUTHORITATIVE" if mapped_id and role == "canonical" else "SUPPORTING_CITABLE"
        origin_id = valid_origin_id(record["fields"].get("OriginID"))
        if origin_id in duplicates:
            identity_status = "quarantined-duplicate-origin-id"
            mapped_id = None
            authority_state = "QUARANTINED"
        representation = {
            "id": rep_id,
            "title": record["title"],
            "canonicalUrl": record["canonical"],
            "representationType": rep_type,
            "artifactTypeHint": artifact_type(record),
            "representsObject": mapped_id,
            "identityStatus": identity_status,
            "authorityRole": role,
            "authorityDomain": domains,
            "authorityBasis": basis,
            "authorityState": authority_state,
            "sourceAuthority": {"state": authority_state, "domains": domains, "basis": basis},
            "authoritativeSource": record["canonical"] if role == "canonical" else None,
            "derivedFrom": [],
            "language": normalized_language(record),
            "visibility": "public",
            "allowedConsumers": PUBLIC_CONSUMERS,
            "provenance": provenance(record["relative"], record["canonical"], source_hash(record)),
        }
        representations.append(representation)
        if mapped_id:
            objects[mapped_id]["representations"].append(rep_id)
            add_authoritative(rep_id, "representsObject", mapped_id, basis, record["canonical"])

    relationships = list(authoritative)
    known_rep_ids = {item["id"] for item in representations}
    seen_discovery: set[tuple[str, str, str]] = set()
    for record in records:
        source_id = record["canonical"] + "#webpage"
        for relation in record.get("relations", []):
            target_id = relation["target"] + "#webpage"
            key = (source_id, relation["type"], target_id)
            if target_id not in known_rep_ids or key in seen_discovery:
                continue
            seen_discovery.add(key)
            relationships.append({
                "id": relation_id(source_id, relation["type"], target_id, "DISCOVERY"),
                "sourceId": source_id,
                "targetId": target_id,
                "relationshipType": relation["type"],
                "authorityState": "DISCOVERY",
                "authorityBasis": "explicitHTMLLink",
                "sourceUrl": record["canonical"],
                "status": "observed",
                "sourceAuthority": {"state": "SUPPORTING_CITABLE", "basis": "explicitHTMLLink"},
                "provenance": provenance(record["relative"], record["canonical"], source_hash(record)),
            })

    object_list = sorted(objects.values(), key=lambda item: item["id"])
    representation_list = sorted(representations, key=lambda item: item["canonicalUrl"])
    relationships.sort(key=lambda item: (item["authorityState"], item["sourceId"], item["relationshipType"], item["targetId"]))

    duplicate_report = []
    for origin_id, group in sorted(duplicates.items()):
        pages = []
        similarities = []
        for record in group:
            pages.append({
                "url": record["canonical"],
                "title": record["title"],
                "artifactClassification": artifact_type(record),
                "parentArchitecture": clean(record["fields"].get("Architecture") or record["fields"].get("Architecture Family")) or None,
                "parentStandard": clean(record["fields"].get("Parent Standard")) or None,
            })
        for index, left in enumerate(group):
            for right in group[index + 1:]:
                similarities.append({
                    "left": left["canonical"],
                    "right": right["canonical"],
                    "contentSimilarity": round(SequenceMatcher(None, left["visibleText"][:20000], right["visibleText"][:20000]).ratio(), 4),
                })
        normalized_titles = {normalize(record["title"]) for record in group}
        has_about = any(representation_type(record).startswith("About") for record in group)
        interpretation = "representation" if has_about and len(normalized_titles) == 1 else "duplicate" if len(normalized_titles) == 1 else "separate-object" if len(normalized_titles) > 1 else "unresolved"
        duplicate_report.append({
            "originId": origin_id,
            "pages": pages,
            "pairwiseSimilarity": similarities,
            "possibleInterpretation": interpretation,
            "resolutionStatus": "requires-human-review",
            "automaticResolutionApplied": False,
        })

    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[normalize(record["title"])].append(record)
    candidate_pool = []
    for key, group in groups.items():
        if not key or len(group) < 2:
            continue
        rep_types = sorted({representation_type(record) for record in group})
        candidate_pool.append({
            "normalizedName": key,
            "candidatePages": [{"url": record["canonical"], "title": record["title"], "representationType": representation_type(record)} for record in group],
            "representationTypes": rep_types,
            "possibleInterpretation": "multiple-representations" if len(rep_types) > 1 else "possible-duplicate",
            "resolutionStatus": "requires-authority-review",
            "automaticMergeApplied": False,
        })
    candidate_pool.sort(key=lambda item: (-len(item["candidatePages"]), item["normalizedName"]))
    candidate_review = candidate_pool[:39]

    reviewed_urls = {
        page["url"]
        for group in candidate_review
        for page in group["candidatePages"]
    }
    for item in representation_list:
        if item["canonicalUrl"] in reviewed_urls and item["authorityState"] == "SUPPORTING_CITABLE" and not item["representsObject"]:
            item["authorityState"] = "REVIEW_REQUIRED"
            item["identityStatus"] = "review-required-candidate-entity"
            item["sourceAuthority"] = {
                "state": "REVIEW_REQUIRED",
                "domains": item["authorityDomain"],
                "basis": "candidateEntityCollision",
            }

    object_by_id = {item["id"]: index for index, item in enumerate(object_list)}
    object_by_url = {item["canonicalUrl"]: item["id"] for item in object_list if item.get("canonicalUrl")}
    object_by_name: dict[str, list[str]] = defaultdict(list)
    for item in object_list:
        for name in filter(None, (item["canonicalName"], item.get("acronym"))):
            key = normalize(name)
            if item["id"] not in object_by_name[key]:
                object_by_name[key].append(item["id"])
    children: dict[str, list[str]] = defaultdict(list)
    for item in object_list:
        if item.get("parentObjectId"):
            children[item["parentObjectId"]].append(item["id"])
        if item.get("architectureId") and item["artifactType"] == "ParentStandard":
            children[item["architectureId"]].append(item["id"])
    relations_by_object: dict[str, list[str]] = defaultdict(list)
    for relation in relationships:
        relations_by_object[relation["sourceId"]].append(relation["id"])
        relations_by_object[relation["targetId"]].append(relation["id"])
    lexical: dict[str, set[str]] = defaultdict(set)
    for item in object_list:
        corpus = " ".join(filter(None, (item["canonicalName"], item.get("acronym"), item.get("canonicalDefinition"), item.get("governedSpace"))))
        for token in re.findall(r"[a-z0-9]{2,}", normalize(corpus)):
            if token not in TOKEN_STOPWORDS:
                lexical[token].add(item["id"])

    type_counts = Counter(item["artifactType"] for item in object_list)
    representation_counts = Counter(item["representationType"] for item in representation_list)
    authority_counts = Counter(item["authorityState"] for item in representation_list)
    authoritative_count = sum(item["authorityState"] == "AUTHORITATIVE" for item in relationships)
    discovery_count = len(relationships) - authoritative_count
    unmapped_representations = sum(item["representsObject"] is None for item in representation_list)
    unresolved_representations = sum(
        item["representsObject"] is None and item["authorityState"] != "QUARANTINED"
        for item in representation_list
    )
    quarantined_representations = sum(item["authorityState"] == "QUARANTINED" for item in representation_list)
    reference_acronyms = sorted({
        architecture["acronym"]
        for architecture in architecture_registry.get("architectures", [])
        if any(
            "architecture index" in page.get("label", "").casefold()
            and "complete standards" not in page.get("label", "").casefold()
            for page in architecture.get("pages", [])
        )
    })
    reference_validation = [
        {
            "acronym": acronym,
            "result": validation_by_acronym[acronym]["result"],
            "authorityState": validation_by_acronym[acronym]["authorityState"],
            "evidence": [ARCHITECTURE_INDEX_PATH, COMPLETE_ARCHITECTURE_INDEX_PATH],
            "dedicatedIndexPages": [
                page["url"]
                for page in index_by_acronym[acronym].get("pages", [])
                if "architecture index" in page.get("label", "").casefold()
                and "complete standards" not in page.get("label", "").casefold()
            ],
        }
        for acronym in reference_acronyms
    ]
    malformed_languages = [item["id"] for item in representation_list if not LANGUAGE_RE.fullmatch(item["language"])]
    architecture_blockers = [item["acronym"] for item in architecture_validation if item["result"] != "PASS"]
    readiness_blockers = []
    if architecture_blockers:
        readiness_blockers.append(f"Architecture Core cross-validation requires review: {', '.join(architecture_blockers)}")
    if len(reference_validation) != 4 or any(item["result"] != "PASS" for item in reference_validation):
        readiness_blockers.append("The four Reference Architectures are not all fully cross-validated.")
    if duplicate_report:
        readiness_blockers.append(f"{len(duplicate_report)} duplicate OriginID groups remain under explicit governance review.")
    if candidate_review:
        readiness_blockers.append(f"{len(candidate_review)} candidate entity groups remain under authority review.")
    if malformed_languages:
        readiness_blockers.append(f"{len(malformed_languages)} representations contain an unapproved language code.")
    lara_ready = not readiness_blockers
    review_queue = {
        "architectureConflicts": [item for item in architecture_validation if item["result"] != "PASS"],
        "duplicateOriginIdGroups": [item["originId"] for item in duplicate_report],
        "candidateEntityGroups": [item["normalizedName"] for item in candidate_review],
        "automaticPromotionApplied": False,
    }
    consumer_contract = {
        "contractVersion": "1.1",
        "mode": "read-only",
        "database": "shared OOF Knowledge Infrastructure outputs; no separate LaRA database",
        "precedence": ["CANONICAL_AUTHORITATIVE", "validated authoritative relationships", "SUPPORTING_CITABLE", "discovery"],
        "exclusions": ["REVIEW_REQUIRED", "QUARANTINED"],
        "exactLookup": {"success": "FOUND", "ambiguous": "AMBIGUOUS", "missing": "NOT_FOUND"},
        "mutationAllowed": False,
        "publicApiCreated": False,
    }

    dump(output / "objects-core.json", {"schemaVersion": SCHEMA_VERSION, "generationMode": "report-only", "visibility": "public", "objects": object_list})
    dump(output / "representations.json", {"schemaVersion": SCHEMA_VERSION, "generationMode": "report-only", "visibility": "public", "representations": representation_list})
    dump(output / "relationships.json", {"schemaVersion": SCHEMA_VERSION, "generationMode": "report-only", "visibility": "public", "relationships": relationships})
    dump(output / "indexes/object-by-id.json", {"schemaVersion": SCHEMA_VERSION, "objectsFile": "../objects-core.json", "index": object_by_id})
    dump(output / "indexes/object-by-canonical-url.json", {"schemaVersion": SCHEMA_VERSION, "index": object_by_url})
    dump(output / "indexes/object-by-name.json", {"schemaVersion": SCHEMA_VERSION, "index": dict(sorted(object_by_name.items()))})
    dump(output / "indexes/children-by-parent.json", {"schemaVersion": SCHEMA_VERSION, "index": {key: sorted(set(value)) for key, value in sorted(children.items())}})
    dump(output / "indexes/relations-by-object.json", {"schemaVersion": SCHEMA_VERSION, "index": {key: sorted(set(value)) for key, value in sorted(relations_by_object.items())}})
    dump(output / "indexes/lexical.json", {"schemaVersion": SCHEMA_VERSION, "index": {key: sorted(value) for key, value in sorted(lexical.items())}})
    dump(output / "indexes/representations-by-authority.json", {
        "schemaVersion": SCHEMA_VERSION,
        "index": {
            state: sorted(item["id"] for item in representation_list if item["authorityState"] == state)
            for state in AUTHORITY_STATES
        },
    })
    dump(output / "reports/duplicate-origin-id-review.json", {
        "schemaVersion": SCHEMA_VERSION,
        "reviewStatus": "human-review-required",
        "summary": {"duplicateGroups": len(duplicate_report), "affectedRepresentations": sum(len(item["pages"]) for item in duplicate_report)},
        "conflicts": duplicate_report,
    })
    dump(output / "reports/candidate-entity-review.json", {
        "schemaVersion": SCHEMA_VERSION,
        "reviewStatus": "authority-review-required",
        "selectionMethod": "Top 39 deterministic normalized-name groups with multiple public representations; no merge is applied.",
        "candidatePoolCount": len(candidate_pool),
        "candidateGroupCount": len(candidate_review),
        "groups": candidate_review,
    })
    dump(output / "reports/architecture-canonical-validation.json", {
        "schemaVersion": SCHEMA_VERSION,
        "policy": "PASS promotes to canonical; PARTIAL remains supporting and enters review; CONFLICT enters review or quarantine for identity conflicts.",
        "canonicalSources": {
            "architectureIndex": ARCHITECTURE_INDEX_PATH,
            "completeArchitectureIndex": COMPLETE_ARCHITECTURE_INDEX_PATH,
        },
        "authorityDomains": {
            ARCHITECTURE_INDEX_PATH: ["publicationApproval", "publicRegistryMembership", "publicationStatus"],
            COMPLETE_ARCHITECTURE_INDEX_PATH: ["architectureIdentity", "canonicalName", "standardsHierarchy", "canonicalUrls"],
        },
        "summary": dict(Counter(item["result"] for item in architecture_validation)),
        "architectures": architecture_validation,
    })
    dump(output / "reports/reference-architecture-validation.json", {
        "schemaVersion": SCHEMA_VERSION,
        "expectedCount": 4,
        "detectedCount": len(reference_validation),
        "architectures": reference_validation,
    })
    dump(output / "reports/authority-review-queue.json", {"schemaVersion": SCHEMA_VERSION, **review_queue})
    dump(output / "reports/lara-read-only-consumer-contract.json", {"schemaVersion": SCHEMA_VERSION, **consumer_contract})
    dump(output / "reports/lara-integration-readiness.json", {
        "schemaVersion": SCHEMA_VERSION,
        "LARA_INTEGRATION_READY": lara_ready,
        "architectureCoreReady": not architecture_blockers,
        "reportOnly": True,
        "blockers": readiness_blockers,
        "prohibitedCutoverApplied": False,
    })
    parity = {
        "schemaVersion": SCHEMA_VERSION,
        "mode": "report-only-parallel",
        "existingSearchPreserved": sha256_file(ROOT / "search-index.json") == search_index_hash,
        "publicPageCount": len(records),
        "representationCount": len(representation_list),
        "resolvedRepresentationCount": len(representation_list) - unmapped_representations,
        "unresolvedRepresentationCount": unresolved_representations,
        "quarantinedRepresentationCount": quarantined_representations,
        "objectCount": len(object_list),
        "objectTypeCounts": dict(sorted(type_counts.items())),
        "representationTypeCounts": dict(sorted(representation_counts.items())),
        "authorityStateCounts": {state: authority_counts.get(state, 0) for state in AUTHORITY_STATES},
        "relationshipCounts": {"authoritative": authoritative_count, "discovery": discovery_count},
        "duplicateOriginIdGroups": len(duplicate_report),
        "candidateEntityGroupsForReview": len(candidate_review),
        "canonicalUrlChangesApplied": 0,
        "visibleContentChangesApplied": 0,
        "productionConsumerCutoverApplied": False,
        "architectureCoreReady": not architecture_blockers,
        "phase6LaRAReadOnlyIntegrationSafe": lara_ready,
        "phase6Recommendation": "Remain in report-only mode until the published readiness blockers are resolved and accepted by OOF authority.",
    }
    dump(output / "reports/migration-parity-report.json", parity)
    dump(output / "reports/implementation-summary.json", {
        "schemaVersion": SCHEMA_VERSION,
        "implementation": "OOF Knowledge Infrastructure 1.1",
        "mode": "report-only-parallel",
        "objectRegistry": "objects-core.json",
        "representationRegistry": "representations.json",
        "relationshipRegistry": "relationships.json",
        "authorityModel": "Authority is assigned as CANONICAL_AUTHORITATIVE, SUPPORTING_CITABLE, REVIEW_REQUIRED, or QUARANTINED. Architecture truth requires agreement between both designated canonical sources.",
        "representationModel": "Pages remain page identities and may represent a shared governed object; unresolved pages remain unmerged.",
        "visibilityModel": "Public output is generated separately and contains public knowledge only; visibility and allowedConsumers are separate fields.",
        "retrievalModel": ["canonicalExactLookup", "validatedRelationshipLookup", "supportingRetrieval", "discovery", "AIReasoningLater"],
        "currentSearchStatus": "preserved-as-fallback",
        "unresolvedGovernanceDecisions": ["duplicateOriginIds", "candidateEntityGroups", "unresolvedRepresentationMappings"],
        "phase6Recommendation": parity["phase6Recommendation"],
    })
    implementation_report = {
        "schemaVersion": SCHEMA_VERSION,
        "title": "OOF Knowledge Infrastructure 1.1 Implementation Report",
        "A_scope": "Existing 1.0 infrastructure updated in place; no rebuild of site content and no production consumer cutover.",
        "B_mode": "report-only",
        "C_counts": {"objects": len(object_list), "representations": len(representation_list), "relationships": len(relationships)},
        "D_canonicalSources": [ARCHITECTURE_INDEX_PATH, COMPLETE_ARCHITECTURE_INDEX_PATH],
        "E_authorityMapping": {state: authority_counts.get(state, 0) for state in AUTHORITY_STATES},
        "F_architectureCore": {"ready": not architecture_blockers, "validationReport": "architecture-canonical-validation.json"},
        "G_referenceArchitectures": {"detected": reference_acronyms, "validationReport": "reference-architecture-validation.json"},
        "H_crossValidation": "Deterministic field comparison is integrated into every build.",
        "I_futureOnboarding": "All newly indexed architectures enter the same cross-validation loop automatically.",
        "J_promotionRule": "Only PASS from governed source evidence promotes architecture identity to canonical.",
        "K_failureRecords": "Conflict fields, both source values, candidate URL, reason, provenance, commit and generated timestamp are retained.",
        "L_anomalyDetection": {"reviewQueue": "authority-review-queue.json", "architectureBlockers": architecture_blockers},
        "M_historicalPages": {"classified": len(representation_list), "authorityStateCounts": {state: authority_counts.get(state, 0) for state in AUTHORITY_STATES}},
        "N_unresolvedRepresentations": unresolved_representations,
        "O_retrievalPrecedence": consumer_contract["precedence"],
        "P_sourceAuthority": "Present on every object, representation and relationship.",
        "Q_architectureTruth": "Only the two designated architecture sources may establish or override architecture truth.",
        "R_duplicateOriginIds": {"groups": len(duplicate_report), "affectedRepresentations": sum(len(item["pages"]) for item in duplicate_report), "automaticMergeApplied": False},
        "S_candidateEntities": {"groups": len(candidate_review), "automaticMergeApplied": False},
        "T_languages": {"approvedPattern": LANGUAGE_RE.pattern, "malformedAfterNormalization": len(malformed_languages)},
        "U_schemaAndSemantics": {"schemas": 4, "semanticFieldsRequireSourceEvidence": True},
        "V_provenance": {"repositoryCommit": SOURCE_COMMIT, "buildId": BUILD_ID, "generatedTimestamp": GENERATED_TIMESTAMP, "extractorVersion": EXTRACTOR_VERSION},
        "W_testsAndGoldenFixtures": "Validator and unit tests cover schemas, collisions, ambiguity, precedence, exclusions, source consistency, onboarding, correction promotion, integrity and performance.",
        "X_laraReadiness": {"LARA_INTEGRATION_READY": lara_ready, "blockers": readiness_blockers, "contract": "lara-read-only-consumer-contract.json"},
    }
    dump(output / "reports/knowledge-infrastructure-1.1-report.json", implementation_report)

    files = []
    for path in sorted(output.rglob("*.json")):
        if path.name == "manifest.json":
            continue
        files.append({"path": path.relative_to(output_root).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    fingerprint = sha256_bytes("\n".join(f"{item['path']}:{item['sha256']}" for item in files).encode("utf-8"))
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "generationMode": "report-only",
        "extractorVersion": EXTRACTOR_VERSION,
        "buildFingerprint": fingerprint,
        "visibility": "public",
        "allowedConsumers": PUBLIC_CONSUMERS,
        "sourceCommit": SOURCE_COMMIT,
        "buildId": BUILD_ID,
        "generatedAt": GENERATED_TIMESTAMP,
        "authorityStates": list(AUTHORITY_STATES),
        "LARA_INTEGRATION_READY": lara_ready,
        "counts": {"objects": len(object_list), "representations": len(representation_list), "relationships": len(relationships)},
        "schemas": [
            "schemas/oof-knowledge-object.v1.schema.json",
            "schemas/oof-knowledge-representation.v1.schema.json",
            "schemas/oof-knowledge-relationship.v1.schema.json",
            "schemas/oof-knowledge-manifest.v1.schema.json",
        ],
        "files": files,
    }
    dump(output / "manifest.json", manifest)
    return {"objects": len(object_list), "representations": len(representation_list), "relationships": len(relationships), "duplicates": len(duplicate_report), "candidates": len(candidate_review)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    summary = build(args.output_root.resolve())
    print(
        "Knowledge infrastructure built in report-only mode: "
        f"{summary['objects']} objects, {summary['representations']} representations, "
        f"{summary['relationships']} relationships, {summary['duplicates']} duplicate-ID groups, "
        f"{summary['candidates']} candidate entity groups."
    )


if __name__ == "__main__":
    main()
