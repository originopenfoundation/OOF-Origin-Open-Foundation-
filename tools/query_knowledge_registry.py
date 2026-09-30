#!/usr/bin/env python3
"""Deterministic local retrieval for the OOF knowledge registry."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "knowledge"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: str) -> str:
    value = value.casefold().replace("®", "").replace("™", "")
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
    args = parser.parse_args()
    registry = KnowledgeRegistry()
    exact = registry.exact(args.query)
    if args.related and exact:
        result: object = {"object": exact, "relationships": registry.related(exact["id"], args.authoritative_only)}
    else:
        result = exact or registry.lexical(args.query, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
