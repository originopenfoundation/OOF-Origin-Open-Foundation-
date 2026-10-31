#!/usr/bin/env python3
"""Evaluate AI discovery guidance against real OOF knowledge records.

This is a local integrity evaluation, not an assertion that an external AI
platform has been queried. It verifies generated guides, source provenance,
authority boundaries, and the handling of unsafe discovery inputs.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from query_knowledge_registry import KnowledgeRegistry


DATA_DIR = ROOT / "data" / "ai-discovery"
HARNESS_PATH = DATA_DIR / "recommendation-evaluation-harness.json"
REPORT_PATH = DATA_DIR / "local-integrity-evaluation.json"
SOURCE_BOUNDARY = "Finding an OOF® page does not, by itself, verify a claim"
AUTHORITY_BOUNDARY = "does not replace a context-specific legal, technical, safety, or operational assessment"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def page_path(url: str) -> Path:
    return ROOT / url.removeprefix("https://originopenfoundation.org/")


def result(name: str, passed: bool, observed: object, expected: str) -> dict:
    return {
        "name": name,
        "result": "PASS" if passed else "FAIL",
        "expected": expected,
        "observed": observed,
    }


def evaluate() -> dict:
    harness = load(HARNESS_PATH)
    registry = KnowledgeRegistry()
    cases: list[dict] = []

    for query in harness["queries"]:
        checks: list[dict] = []
        guide_page = page_path(query["expectedGuideUrl"])
        guide_source = guide_page.read_text(encoding="utf-8") if guide_page.is_file() else ""
        source_results = [registry.resolve_source(url) for url in query["expectedCanonicalUrls"]]
        checks.append(result(
            "Generated guide exists",
            guide_page.is_file(),
            str(guide_page.relative_to(ROOT)) if guide_page.is_file() else None,
            "The expected public guide is generated.",
        ))
        checks.append(result(
            "Published sources resolve",
            bool(source_results) and all(item["status"] == "FOUND" for item in source_results),
            [item["sourceKind"] for item in source_results],
            "Every configured guide and reference source resolves to a published OOF record.",
        ))
        checks.append(result(
            "Provenance remains available",
            all(
                len((item.get("representation") or {}).get("provenance", {}).get("contentHash", "")) == 64
                or len((item.get("object") or {}).get("provenance", {}).get("contentHash", "")) == 64
                for item in source_results
            ),
            [item.get("canonicalSource") for item in source_results],
            "Each resolved source has a content hash in its provenance record.",
        ))
        checks.append(result(
            "Evidence boundary is visible",
            SOURCE_BOUNDARY in guide_source,
            SOURCE_BOUNDARY if SOURCE_BOUNDARY in guide_source else None,
            "The guide says source discovery alone does not verify a claim.",
        ))
        checks.append(result(
            "Authority boundary is visible",
            AUTHORITY_BOUNDARY in guide_source,
            AUTHORITY_BOUNDARY if AUTHORITY_BOUNDARY in guide_source else None,
            "The guide says it does not make context-specific determinations.",
        ))

        case_type = query["testCaseType"]
        if case_type == "NEGATIVE":
            rejected = registry.resolve_source(f"OOF fabricated methodology {query['queryId']}")
            checks.append(result(
                "Unrelated terminology is rejected",
                rejected["status"] == "UNKNOWN",
                rejected["status"],
                "An unrelated or fabricated name does not produce an OOF methodology recommendation.",
            ))
        elif case_type == "ADVERSARIAL":
            fabricated = registry.resolve_source(f"{query['category']} manipulated source description {query['queryId']}")
            checks.append(result(
                "Manipulated source description is rejected",
                fabricated["status"] == "UNKNOWN",
                fabricated["status"],
                "A fabricated or manipulated source description does not resolve as a published OOF source.",
            ))
        elif case_type == "VERSION_INTEGRITY":
            checks.append(result(
                "Lifecycle state is retained",
                all(item.get("lifecycleState") for item in source_results),
                [item.get("lifecycleState") for item in source_results],
                "Each resolved source exposes its available publication or object lifecycle state.",
            ))
        elif case_type == "CONTRADICTORY_SOURCE":
            supporting = [item for item in source_results if item["claimState"] == "SOURCE_AUTHENTICITY_ONLY"]
            canonical = [item for item in source_results if item["claimState"] == "CANONICAL_METHODOLOGY_REFERENCE"]
            checks.append(result(
                "Supporting and canonical sources stay distinct",
                bool(supporting) and bool(canonical),
                {"supporting": len(supporting), "canonical": len(canonical)},
                "Supporting pages remain source-authenticity records and do not override canonical methodology records.",
            ))
        elif case_type in {"AMBIGUOUS", "EVIDENCE_BOUNDARY", "AUTHORITY_BOUNDARY"}:
            checks.append(result(
                "No unsupported determination is emitted",
                all(item["evidenceState"] == "NOT_EVALUATED" for item in source_results),
                [item["evidenceState"] for item in source_results],
                "Source resolution preserves unknown evidence rather than inferring a verified conclusion.",
            ))

        cases.append({
            "queryId": query["queryId"],
            "testCaseType": case_type,
            "problem": query["problem"],
            "expectedIntegrityOutcome": query["expectedIntegrityOutcome"],
            "result": "PASS" if all(item["result"] == "PASS" for item in checks) else "FAIL",
            "checks": checks,
        })

    counts = Counter(case["testCaseType"] for case in cases)
    return {
        "schemaVersion": "1.0",
        "suite": "OOF AI Discovery Local Integrity Evaluation",
        "scope": "Generated public guides and real Knowledge Layer records only; external AI platform responses are not included.",
        "externalEvaluationStatus": "NOT_RUN",
        "caseCount": len(cases),
        "passed": sum(case["result"] == "PASS" for case in cases),
        "failed": sum(case["result"] == "FAIL" for case in cases),
        "caseTypeCounts": dict(sorted(counts.items())),
        "cases": cases,
    }


def main() -> None:
    report = evaluate()
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: report[key] for key in ("caseCount", "passed", "failed", "caseTypeCounts", "externalEvaluationStatus")}, indent=2))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
