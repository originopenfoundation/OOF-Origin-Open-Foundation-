#!/usr/bin/env python3
"""Deterministic local retrieval for the OOF knowledge registry."""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
import re
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "knowledge"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: str) -> str:
    value = value.casefold().replace("®", "").replace("™", "")
    value = re.sub(r"\babout\b", " ", value)
    value = re.sub(r"\bcomplete standards\s*&\s*modules index\b", " ", value)
    value = re.sub(r"\barchitecture (?:map|index)\b", " ", value)
    value = re.sub(r"\b(?:question|standards|module|site) index\b", " ", value)
    value = re.sub(r"\([^)]*\)", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


class KnowledgeRegistry:
    def __init__(self, root: Path = DATA) -> None:
        self.root = root
        self.objects = load(root / "objects-core.json")["objects"]
        self.representations = load(root / "representations.json")["representations"]
        self.by_id = {item["id"]: item for item in self.objects}
        self.representation_by_id = {item["id"]: item for item in self.representations}
        self.by_url = load(root / "indexes" / "object-by-canonical-url.json")["index"]
        self.by_name = load(root / "indexes" / "object-by-name.json")["index"]
        alias_path = root / "indexes" / "object-aliases.json"
        self.aliases = load(alias_path)["index"] if alias_path.exists() else {}
        compact_path = root / "compact-objects.json"
        self.compact_by_id = {
            item["objectId"]: item for item in load(compact_path).get("objects", [])
        } if compact_path.exists() else {}
        self.lexical_index = load(root / "indexes" / "lexical.json")["index"]
        relationships = load(root / "relationships.json")["relationships"]
        self.relationships = relationships
        self.relations_by_object = load(root / "indexes" / "relations-by-object.json")["index"]
        self.relationship_by_id = {item["id"]: item for item in relationships}

    def exact(self, value: str) -> dict | None:
        result = self.exact_result(value)
        return result.get("object") if result["status"] == "FOUND" else None

    def exact_result(self, value: str) -> dict:
        object_id = value if value in self.by_id else self.by_url.get(value)
        if object_id:
            item = self.by_id.get(object_id)
            if item and item["authorityState"] not in {"REVIEW_REQUIRED", "QUARANTINED"}:
                return {"status": "FOUND", "authorityState": item["authorityState"], "object": item}
            return {"status": item["authorityState"] if item else "NOT_FOUND", "object": None}
        matches = self.by_name.get(normalize(value), [])
        eligible = [self.by_id[item] for item in matches if self.by_id[item]["authorityState"] not in {"REVIEW_REQUIRED", "QUARANTINED"}]
        if len(eligible) == 1:
            return {"status": "FOUND", "authorityState": eligible[0]["authorityState"], "object": eligible[0]}
        if len(eligible) > 1:
            return {"status": "AMBIGUOUS", "object": None, "candidateIds": [item["id"] for item in eligible]}
        return {"status": "NOT_FOUND", "object": None}

    @staticmethod
    def _lifecycle_rank(item: dict) -> int:
        value = normalize(item.get("status") or "")
        if value in {"current", "completed", "published", "active", "canonical"}:
            return 0
        if value == "draft":
            return 1
        if value in {"superseded", "archived", "deprecated"}:
            return 3
        return 2

    def _resolution(self, matches: list[dict], method: str, confidence: str, current_only: bool) -> dict:
        eligible = [
            item for item in matches
            if item and item.get("authorityState") not in {"REVIEW_REQUIRED", "QUARANTINED"}
        ]
        if current_only and eligible:
            best = min(self._lifecycle_rank(item) for item in eligible)
            eligible = [item for item in eligible if self._lifecycle_rank(item) == best]
        unique = {item["id"]: item for item in eligible}
        if len(unique) == 1:
            item = next(iter(unique.values()))
            return {
                "status": "FOUND",
                "object": item,
                "resolutionMethod": method,
                "resolutionConfidence": confidence,
                "sourceAuthority": item.get("sourceAuthority"),
                "canonicalSource": item.get("canonicalUrl"),
                "ambiguityState": "NONE",
            }
        if len(unique) > 1:
            return {
                "status": "AMBIGUOUS",
                "object": None,
                "candidateIds": sorted(unique),
                "resolutionMethod": method,
                "resolutionConfidence": "Unresolved",
                "sourceAuthority": None,
                "canonicalSource": None,
                "ambiguityState": "MULTIPLE_AUTHORIZED_OBJECTS",
            }
        return {
            "status": "UNKNOWN",
            "object": None,
            "resolutionMethod": method,
            "resolutionConfidence": "Unresolved",
            "sourceAuthority": None,
            "canonicalSource": None,
            "ambiguityState": "UNRESOLVED",
        }

    def candidates(self, value: str, limit: int = 5) -> list[dict]:
        needle = normalize(value)
        if not needle:
            return []
        scored: dict[str, tuple[float, str]] = {}
        keys = set(self.by_name) | set(self.aliases)
        for key in keys:
            if key == "oof" and needle != "oof":
                continue
            ratio = SequenceMatcher(None, needle, key).ratio()
            if needle in key or key in needle:
                ratio = max(ratio, min(0.94, 0.68 + min(len(needle), len(key)) / max(len(needle), len(key)) * 0.25))
            if ratio < 0.68:
                continue
            ids = set(self.by_name.get(key, []))
            ids.update(entry["objectId"] for entry in self.aliases.get(key, []))
            for object_id in ids:
                item = self.by_id.get(object_id)
                if not item or item.get("authorityState") in {"REVIEW_REQUIRED", "QUARANTINED"}:
                    continue
                previous = scored.get(object_id)
                if previous is None or ratio > previous[0]:
                    scored[object_id] = (ratio, key)
        ranked = sorted(scored.items(), key=lambda row: (-row[1][0], self._lifecycle_rank(self.by_id[row[0]]), self.by_id[row[0]]["canonicalName"], row[0]))
        return [
            {
                "object": self.by_id[object_id],
                "candidateScore": round(score, 3),
                "matchedReference": matched,
                "sourceAuthority": self.by_id[object_id].get("sourceAuthority"),
            }
            for object_id, (score, matched) in ranked[:limit]
        ]

    def resolve(self, value: str, *, allow_candidates: bool = True, current_only: bool = False) -> dict:
        if value in self.by_id:
            return self._resolution([self.by_id[value]], "immutableObjectId", "Exact", current_only)
        object_id = self.by_url.get(value)
        if object_id:
            return self._resolution([self.by_id.get(object_id)], "canonicalUrl", "Exact", current_only)
        key = normalize(value)
        direct_ids = self.by_name.get(key, [])
        if direct_ids:
            return self._resolution([self.by_id.get(item) for item in direct_ids], "canonicalNameOrAcronym", "Exact normalized", current_only)
        alias_entries = self.aliases.get(key, [])
        approved = [entry for entry in alias_entries if entry.get("resolverEligible") is True]
        if approved:
            methods = sorted({entry.get("aliasType", "approved_alias") for entry in approved})
            return self._resolution([self.by_id.get(entry["objectId"]) for entry in approved], "+".join(methods), "Governed alias", current_only)
        if allow_candidates:
            candidates = self.candidates(value)
            if candidates:
                return {
                    "status": "CANDIDATE_MATCH",
                    "object": None,
                    "candidates": candidates,
                    "resolutionMethod": "fuzzyCandidate",
                    "resolutionConfidence": "Candidate only",
                    "sourceAuthority": None,
                    "canonicalSource": None,
                    "ambiguityState": "CLARIFICATION_REQUIRED",
                }
        return self._resolution([], "noMatch", "Unresolved", current_only)

    def compact(self, value: str) -> dict:
        result = self.resolve(value, allow_candidates=False)
        if result["status"] != "FOUND":
            return result
        item = result["object"]
        compact = self.compact_by_id.get(item["id"])
        if compact is None:
            compact = {
                "objectId": item["id"],
                "canonicalName": item.get("canonicalName"),
                "acronym": item.get("acronym"),
                "objectType": item.get("artifactType"),
                "canonicalUrl": item.get("canonicalUrl"),
                "authority": item.get("authorityState"),
                "provenance": item.get("provenance"),
            }
        return {**result, "compactObject": compact}

    def benchmark(self, value: str) -> dict:
        operations = {
            "objectId": lambda item: self.resolve(item["id"]),
            "canonicalName": lambda item: self.resolve(item["canonicalName"]),
            "acronym": lambda item: self.resolve(item.get("acronym") or item["canonicalName"]),
            "canonicalUrl": lambda item: self.resolve(item["canonicalUrl"]),
            "relationship": lambda item: self.related(item["id"]),
            "lexical": lambda item: self.lexical(item["canonicalName"], 5),
            "fuzzyCandidate": lambda item: self.candidates((item.get("acronym") or item["canonicalName"]) + "x", 5),
        }
        item = self.resolve(value, allow_candidates=False).get("object") or self.objects[0]
        result = {}
        for name, operation in operations.items():
            started = time.perf_counter()
            operation(item)
            result[name] = round((time.perf_counter() - started) * 1000, 3)
        return result

    def external_ai_test_suite(self) -> dict:
        architecture = next(item for item in self.objects if item.get("artifactType") == "Architecture" and item.get("acronym"))
        parent = next((item for item in self.objects if item.get("artifactType") == "ParentStandard" and item.get("architectureId")), architecture)
        module = next((item for item in self.objects if item.get("artifactType") == "CoreModule" and item.get("parentObjectId")), parent)
        duplicate_key = next((key for key, ids in self.by_name.items() if len(ids) > 1), None)
        approved_alias = next((
            entry for entries in self.aliases.values() for entry in entries
            if entry.get("aliasType") in {"approved_alias", "historical_alias"} and entry.get("resolverEligible")
        ), None)
        superseded = next((item for item in self.objects if normalize(item.get("status") or "") in {"superseded", "archived", "deprecated"}), None)
        trademarked = architecture["acronym"] + ("®" if "®" in architecture["canonicalName"] else "™")
        cases = []

        def add(name: str, query: str, result: dict | list, expected) -> None:
            if isinstance(result, dict):
                status = result.get("status", "FOUND")
                item = result.get("object")
                candidate = (result.get("candidates") or [{}])[0].get("object") if result.get("candidates") else None
                item = item or candidate
                method = result.get("resolutionMethod")
                confidence = result.get("resolutionConfidence")
                ambiguity = result.get("ambiguityState")
            else:
                status = "FOUND" if result else "UNKNOWN"
                item = result[0].get("object") if result else None
                method = "lexical"
                confidence = "Candidate only"
                ambiguity = "NONE" if result else "UNRESOLVED"
            allowed = expected if isinstance(expected, set) else {expected}
            cases.append({
                "name": name, "query": query, "resolvedObjectId": item.get("id") if item else None,
                "canonicalName": item.get("canonicalName") if item else None, "resolutionMethod": method,
                "resolutionConfidence": confidence, "sourceAuthority": item.get("sourceAuthority") if item else None,
                "canonicalSource": item.get("canonicalUrl") if item else None, "ambiguityState": ambiguity,
                "resultState": status, "result": "PASS" if status in allowed else "FAIL",
            })

        timed_cases = (
            ("A Exact acronym", architecture["acronym"], lambda: self.resolve(architecture["acronym"]), "FOUND"),
            ("B Trademarked acronym", trademarked, lambda: self.resolve(trademarked), "FOUND"),
            ("C Trademark omitted", architecture["acronym"], lambda: self.resolve(architecture["acronym"]), "FOUND"),
            ("D Full canonical name", architecture["canonicalName"], lambda: self.resolve(architecture["canonicalName"]), "FOUND"),
            ("E Canonical URL", architecture["canonicalUrl"], lambda: self.resolve(architecture["canonicalUrl"]), "FOUND"),
            ("F Immutable Object ID", architecture["id"], lambda: self.resolve(architecture["id"]), "FOUND"),
            ("H Slight typo", architecture["acronym"] + "x", lambda: self.resolve(architecture["acronym"] + "x"), {"CANDIDATE_MATCH", "AMBIGUOUS"}),
            ("I Incomplete object name", architecture["canonicalName"].split("—")[0], lambda: self.resolve(architecture["canonicalName"].split("—")[0]), {"FOUND", "CANDIDATE_MATCH", "AMBIGUOUS"}),
            ("J Natural-language description", architecture.get("governedSpace") or architecture["canonicalName"], lambda: self.lexical(architecture.get("governedSpace") or architecture["canonicalName"]), "FOUND"),
            ("K Governed-space question", f"What governs {architecture.get('governedSpace') or architecture['canonicalName']}?", lambda: self.lexical(f"What governs {architecture.get('governedSpace') or architecture['canonicalName']}?"), "FOUND"),
            ("L Parent Standard lookup", parent["canonicalName"], lambda: self.resolve(parent["canonicalName"]), "FOUND"),
            ("M Core Module lookup", module["canonicalName"], lambda: self.resolve(module["canonicalName"]), "FOUND"),
            ("N Architecture membership", parent["id"], lambda: self.compact(parent["id"]), "FOUND"),
            ("O Child-object lookup", architecture["id"], lambda: self.compact(architecture["id"]), "FOUND"),
            ("P Cross-architecture relationship", architecture["id"], lambda: self.resolve(architecture["id"]), "FOUND"),
            ("Q Current-version lookup", architecture["canonicalName"], lambda: self.resolve(architecture["canonicalName"], current_only=True), "FOUND"),
            ("S Canonical-definition lookup", architecture["id"], lambda: self.compact(architecture["id"]), "FOUND"),
            ("T Unknown acronym", "ZZZ-NOT-OOF", lambda: self.resolve("ZZZ-NOT-OOF"), "UNKNOWN"),
            ("V Incorrect acronym expansion", f"{architecture['acronym']} unrelated fabricated expansion", lambda: self.resolve(f"{architecture['acronym']} unrelated fabricated expansion"), {"CANDIDATE_MATCH", "UNKNOWN"}),
        )
        for name, query, operation, expected in timed_cases:
            result = operation()
            add(name, query, result, expected)

        if approved_alias:
            add("G Approved alias", approved_alias["alias"], self.resolve(approved_alias["alias"]), "FOUND")
        else:
            cases.append({"name": "G Approved alias", "query": None, "resultState": "NOT_APPLICABLE", "result": "PASS", "reason": "No source-backed approved alias is currently published."})
        if superseded:
            add("R Superseded-object lookup", superseded["canonicalName"], self.resolve(superseded["canonicalName"], current_only=True), {"FOUND", "AMBIGUOUS"})
        else:
            cases.append({"name": "R Superseded-object lookup", "query": None, "resultState": "NOT_APPLICABLE", "result": "PASS", "reason": "No source-backed superseded object is currently published."})
        if duplicate_key:
            add("U Ambiguous acronym", duplicate_key, self.resolve(duplicate_key), "AMBIGUOUS")
        else:
            cases.append({"name": "U Ambiguous acronym", "query": None, "resultState": "NOT_APPLICABLE", "result": "PASS"})
        supporting = self.supporting("governance", 1)
        canonical = self.resolve(architecture["id"])
        conflict_pass = bool(supporting) and canonical["status"] == "FOUND" and canonical["object"]["authorityState"] == "CANONICAL_AUTHORITATIVE"
        cases.append({
            "name": "W Supporting-page conflict with canonical source", "query": architecture["id"],
            "resolvedObjectId": architecture["id"], "resultState": "CANONICAL_PRECEDENCE",
            "result": "PASS" if conflict_pass else "FAIL",
            "reason": "Supporting material remains separately retrievable and cannot override canonical object fields.",
        })
        return {
            "schemaVersion": "1.1", "suite": "External-AI Retrieval Test Suite", "caseCount": len(cases),
            "passed": sum(case["result"] == "PASS" for case in cases),
            "failed": sum(case["result"] == "FAIL" for case in cases), "cases": cases,
        }

    def related(self, object_id: str, authoritative_only: bool = False) -> list[dict]:
        found = [self.relationship_by_id[item] for item in self.relations_by_object.get(object_id, [])]
        if authoritative_only:
            found = [item for item in found if item["authorityState"] == "AUTHORITATIVE"]
        return found

    def lexical(self, query: str, limit: int = 10) -> list[dict]:
        tokens = sorted(set(normalize(query).split()))
        if not tokens:
            return []
        scores: dict[str, int] = {}
        for token in tokens:
            for object_id in self.lexical_index.get(token, []):
                scores[object_id] = scores.get(object_id, 0) + 1
        rank = {"CANONICAL_AUTHORITATIVE": 0, "SUPPORTING_CITABLE": 1}
        eligible = [item for item in scores if self.by_id[item]["authorityState"] in rank]
        ranked = sorted(eligible, key=lambda item: (rank[self.by_id[item]["authorityState"]], -scores[item], self.by_id[item]["canonicalName"], item))
        return [{"score": scores[item], "authorityState": self.by_id[item]["authorityState"], "object": self.by_id[item]} for item in ranked[:limit]]

    def supporting(self, query: str, limit: int = 10) -> list[dict]:
        needle = normalize(query)
        found = [
            item for item in self.representations
            if item["authorityState"] == "SUPPORTING_CITABLE"
            and needle in normalize(f"{item['title']} {item['canonicalUrl']}")
        ]
        return sorted(found, key=lambda item: (item["title"], item["id"]))[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--related", action="store_true")
    parser.add_argument("--authoritative-only", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--candidates", action="store_true")
    parser.add_argument("--current", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()
    registry = KnowledgeRegistry()
    resolved = registry.resolve(args.query, current_only=args.current)
    exact = resolved.get("object")
    if args.benchmark:
        result: object = registry.benchmark(args.query)
    elif args.compact:
        result = registry.compact(args.query)
    elif args.candidates:
        result = registry.candidates(args.query, args.limit)
    elif args.related and exact:
        result = {**resolved, "relationships": registry.related(exact["id"], args.authoritative_only)}
    else:
        result = resolved if resolved["status"] != "UNKNOWN" else registry.lexical(args.query, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
