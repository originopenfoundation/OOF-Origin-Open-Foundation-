#!/usr/bin/env python3
"""Validate the report-only OOF knowledge infrastructure."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "knowledge"
sys.path.insert(0, str(ROOT / "tools"))
from query_knowledge_registry import KnowledgeRegistry  # noqa: E402
from validate_json_schema import validate_file  # noqa: E402


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest = load(DATA / "manifest.json")
    objects = load(DATA / "objects-core.json")["objects"]
    representations = load(DATA / "representations.json")["representations"]
    relationships = load(DATA / "relationships.json")["relationships"]
    duplicates = load(DATA / "reports" / "duplicate-origin-id-review.json")
    candidates = load(DATA / "reports" / "candidate-entity-review.json")
    architecture_validation = load(DATA / "reports" / "architecture-canonical-validation.json")
    reference_validation = load(DATA / "reports" / "reference-architecture-validation.json")
    readiness = load(DATA / "reports" / "lara-integration-readiness.json")

    schema_jobs = (
        (DATA / "objects-core.json", ROOT / "schemas" / "oof-knowledge-object.v1.schema.json", "objects"),
        (DATA / "representations.json", ROOT / "schemas" / "oof-knowledge-representation.v1.schema.json", "representations"),
        (DATA / "relationships.json", ROOT / "schemas" / "oof-knowledge-relationship.v1.schema.json", "relationships"),
        (DATA / "manifest.json", ROOT / "schemas" / "oof-knowledge-manifest.v1.schema.json", None),
    )
    for payload_path, schema_path, item_key in schema_jobs:
        schema_errors = validate_file(load(payload_path), schema_path, item_key)
        errors.extend(f"Schema validation ({payload_path.name}): {message}" for message in schema_errors[:20])

    object_ids = [item["id"] for item in objects]
    representation_ids = [item["id"] for item in representations]
    relationship_ids = [item["id"] for item in relationships]
    require(len(object_ids) == len(set(object_ids)), "Object IDs are not unique", errors)
    require(len(representation_ids) == len(set(representation_ids)), "Representation IDs are not unique", errors)
    require(len(relationship_ids) == len(set(relationship_ids)), "Relationship IDs are not unique", errors)
    require(manifest["counts"] == {"objects": len(objects), "representations": len(representations), "relationships": len(relationships)}, "Manifest counts do not match registries", errors)

    known = set(object_ids) | set(representation_ids)
    object_id_set = set(object_ids)
    representation_set = set(representation_ids)
    source_hashes = {item["provenance"]["sourcePath"]: item["provenance"]["contentHash"] for item in representations}
    for item in objects:
        require(item["visibility"] == "public", f"Non-public object leaked: {item['id']}", errors)
        require(item["authorityState"] in {"CANONICAL_AUTHORITATIVE", "SUPPORTING_CITABLE", "REVIEW_REQUIRED", "QUARANTINED"}, f"Invalid object authority state: {item['id']}", errors)
        require(item["canonicalUrl"].startswith("https://originopenfoundation.org/"), f"Invalid canonical URL: {item['id']}", errors)
        require(set(item["representations"]).issubset(representation_set), f"Unknown representation on object: {item['id']}", errors)
        source = ROOT / item["provenance"]["sourcePath"]
        require(source.is_file(), f"Missing source file: {source}", errors)
        require(source_hashes.get(item["provenance"]["sourcePath"]) == item["provenance"]["contentHash"], f"Object provenance differs from its representation: {item['id']}", errors)
    for item in representations:
        require(item["visibility"] == "public", f"Non-public representation leaked: {item['id']}", errors)
        require(item["authorityState"] in {"CANONICAL_AUTHORITATIVE", "SUPPORTING_CITABLE", "REVIEW_REQUIRED", "QUARANTINED"}, f"Invalid representation authority state: {item['id']}", errors)
        if item["representsObject"]:
            require(item["representsObject"] in object_id_set, f"Unknown represented object: {item['id']}", errors)
        if item["identityStatus"] == "quarantined-duplicate-origin-id":
            require(item["representsObject"] is None, f"Duplicate OriginID representation was merged: {item['id']}", errors)
            require(item["authorityState"] == "QUARANTINED", f"Duplicate OriginID is not quarantined: {item['id']}", errors)
        source = ROOT / item["provenance"]["sourcePath"]
        require(source.is_file(), f"Missing representation source: {source}", errors)
        require(len(item["provenance"]["contentHash"]) == 64, f"Invalid representation content hash: {item['id']}", errors)
    for item in relationships:
        require(item["sourceId"] in known and item["targetId"] in known, f"Dangling relationship: {item['id']}", errors)
        require(item["authorityState"] in {"AUTHORITATIVE", "VALIDATED_AUTHORITATIVE", "SUPPORTING", "DISCOVERY", "REVIEW_REQUIRED", "QUARANTINED"}, f"Invalid authority state: {item['id']}", errors)
        if item["authorityState"] == "DISCOVERY":
            require(item["authorityBasis"] not in {"approvedArchitectureRegistry", "explicitPageMetadata"}, f"Discovery relationship uses an authoritative basis: {item['id']}", errors)

    parents = {item["id"]: item["parentObjectId"] for item in objects if item["parentObjectId"]}
    for start in parents:
        seen: set[str] = set()
        current = start
        while current in parents:
            require(current not in seen, f"Hierarchy cycle starts at {start}", errors)
            if current in seen:
                break
            seen.add(current)
            current = parents[current]

    require(duplicates["summary"] == {"duplicateGroups": 7, "affectedRepresentations": 15}, "Duplicate OriginID audit no longer matches the reviewed baseline", errors)
    require(all(not item["automaticResolutionApplied"] for item in duplicates["conflicts"]), "A duplicate OriginID was automatically resolved", errors)
    require(
        candidates["candidateGroupCount"] == candidates["candidatePoolCount"] == len(candidates["groups"]),
        "Candidate entity review must contain every detected collision group",
        errors,
    )
    require(architecture_validation["canonicalSources"] == {"architectureIndex": "data/oof-architecture-registry.json", "completeArchitectureIndex": "oof-structured-architecture-index.html"}, "Canonical architecture sources changed unexpectedly", errors)
    require(all(item["result"] == "PASS" for item in architecture_validation["architectures"]), "Architecture Core contains unresolved source conflicts", errors)
    require(reference_validation["detectedCount"] == reference_validation["expectedCount"] == 4, "Exactly four Reference Architectures must be cross-validated", errors)
    require(all(item["result"] == "PASS" for item in reference_validation["architectures"]), "Reference Architecture validation failed", errors)
    require(readiness["reportOnly"] is True and readiness["prohibitedCutoverApplied"] is False, "LaRA readiness escaped report-only mode", errors)
    require(readiness["LARA_INTEGRATION_READY"] == manifest["LARA_INTEGRATION_READY"], "LaRA readiness disagrees with manifest", errors)
    require(manifest["generationMode"] == "report-only", "Knowledge infrastructure is not report-only", errors)
    require(manifest["visibility"] == "public", "Public manifest has invalid visibility", errors)

    for item in manifest["files"]:
        path = ROOT / item["path"]
        require(path.is_file(), f"Manifest file missing: {item['path']}", errors)
        if path.is_file():
            require(sha256(path) == item["sha256"] and path.stat().st_size == item["bytes"], f"Manifest hash mismatch: {item['path']}", errors)

    registry = KnowledgeRegistry()
    sample = objects[0]
    started = time.perf_counter()
    require(registry.exact(sample["id"])["id"] == sample["id"], "Exact ID lookup failed", errors)
    require(registry.exact(sample["canonicalUrl"])["id"] == sample["id"], "Exact URL lookup failed", errors)
    require(bool(registry.lexical(sample["canonicalName"])), "Lexical lookup failed", errors)
    elapsed_ms = (time.perf_counter() - started) * 1000
    require(elapsed_ms < 100, f"Warm retrieval budget exceeded: {elapsed_ms:.1f} ms", errors)

    with tempfile.TemporaryDirectory() as directory:
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_knowledge_infrastructure.py"), "--output-root", directory], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        rebuilt = Path(directory) / "data" / "knowledge" / "manifest.json"
        require(load(rebuilt)["buildFingerprint"] == manifest["buildFingerprint"], "Build is not deterministic", errors)

    unresolved = sum(item["representsObject"] is None and item["authorityState"] != "QUARANTINED" for item in representations)
    if unresolved:
        warnings.append(f"{unresolved} non-quarantined representations remain intentionally unmapped")
    if not readiness["LARA_INTEGRATION_READY"]:
        warnings.append("LaRA integration remains blocked as documented in lara-integration-readiness.json")
    return errors, warnings


def main() -> None:
    errors, warnings = validate()
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Knowledge infrastructure validation passed.")


if __name__ == "__main__":
    main()
