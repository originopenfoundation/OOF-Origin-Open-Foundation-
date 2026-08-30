#!/usr/bin/env python3
"""Validate OOF AI discovery metadata without changing website content."""

from __future__ import annotations

import json
import html
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- OOF AI DISCOVERY START -->"
END = "<!-- OOF AI DISCOVERY END -->"
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\s*", re.S)
BASE_URL = "https://originopenfoundation.org/"


def public_pages() -> list[Path]:
    pages = []
    candidates = sorted(ROOT.rglob("*.html"), key=lambda item: item.relative_to(ROOT).as_posix().casefold())
    for path in candidates:
        if ".git" in path.parts:
            continue
        if "</head>" in path.read_text(encoding="utf-8").lower():
            pages.append(path)
    return pages


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    errors: list[str] = []
    pages = public_pages()
    canonicals: set[str] = set()

    for path in pages:
        source = path.read_text(encoding="utf-8")
        blocks = re.findall(re.escape(START) + r"(.*?)" + re.escape(END), source, re.S)
        if len(blocks) != 1:
            errors.append(f"{relative(path)}: expected one AI metadata block, found {len(blocks)}")
            continue
        block = blocks[0]
        canonical_match = re.search(r'<link rel="canonical" href="([^"]+)"', block)
        if not canonical_match:
            errors.append(f"{relative(path)}: missing canonical URL")
        else:
            canonical = canonical_match.group(1)
            page_relative = relative(path)
            expected_canonical = BASE_URL if page_relative == "index.html" else BASE_URL + quote(unquote(page_relative), safe="/-._~()")
            if canonical != expected_canonical:
                errors.append(f"{relative(path)}: canonical URL does not match its file path")
            if canonical in canonicals:
                errors.append(f"{relative(path)}: duplicate canonical URL {canonical}")
            canonicals.add(canonical)
        json_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', block, re.S)
        if not json_match:
            errors.append(f"{relative(path)}: missing JSON-LD")
        else:
            try:
                data = json.loads(json_match.group(1))
                if data.get("url") != canonical_match.group(1) if canonical_match else False:
                    errors.append(f"{relative(path)}: JSON-LD URL differs from canonical")
                title_match = re.search(r"<title>(.*?)</title>", source, re.I | re.S)
                if title_match:
                    expected_name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", title_match.group(1)))).strip()
                    if data.get("name") != expected_name:
                        errors.append(f"{relative(path)}: JSON-LD name differs from the page title")
                if not data.get("name") or not data.get("inLanguage"):
                    errors.append(f"{relative(path)}: incomplete JSON-LD identity")
            except json.JSONDecodeError as exc:
                errors.append(f"{relative(path)}: invalid JSON-LD: {exc}")

        try:
            baseline = subprocess.check_output(
                ["git", "show", f"HEAD:{relative(path)}"], cwd=ROOT, stderr=subprocess.DEVNULL
            ).decode("utf-8")
        except subprocess.CalledProcessError:
            baseline = None
        if baseline is not None and BLOCK_RE.sub("", source) != BLOCK_RE.sub("", baseline):
            errors.append(f"{relative(path)}: content outside the AI metadata block changed")

    graph = json.loads((ROOT / "data" / "oof-site-knowledge-graph.json").read_text(encoding="utf-8"))
    graph_pages = [item for item in graph.get("@graph", []) if str(item.get("@id", "")).endswith("#webpage")]
    if len(graph_pages) != len(pages):
        errors.append(f"Knowledge graph has {len(graph_pages)} pages; expected {len(pages)}")
    graph_urls = {item.get("url") for item in graph_pages}
    if graph_urls != canonicals:
        errors.append("Knowledge graph and canonical page sets differ")

    for item in graph_pages:
        for link in item.get("relatedLink", []):
            target = unquote(urlparse(link).path.lstrip("/"))
            if not target:
                target = "index.html"
            if not (ROOT / target).is_file():
                errors.append(f'Knowledge graph link target is missing: {item.get("url")} -> {link}')

    sitemap_root = ET.parse(ROOT / "sitemap.xml").getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = {element.text for element in sitemap_root.findall("sm:url/sm:loc", namespace)}
    if sitemap_urls != canonicals:
        errors.append("Sitemap and canonical page sets differ")

    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    if f"Sitemap: {BASE_URL}sitemap.xml" not in robots or "Allow: /" not in robots:
        errors.append("robots.txt does not expose the sitemap and full crawl access")

    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    for required in ("sitemap.xml", "oof-site-knowledge-graph.json", "search-index.json", "llms-full.txt"):
        if required not in llms:
            errors.append(f"llms.txt is missing {required}")

    search_entries = json.loads((ROOT / "search-index.json").read_text(encoding="utf-8"))
    search_urls = {entry.get("url") for entry in search_entries}
    missing_search = {relative(path) for path in pages} - search_urls
    if missing_search:
        errors.append(f"Search index is missing {len(missing_search)} public pages")

    if errors:
        print("AI compatibility validation failed:")
        for error in errors[:100]:
            print(f"- {error}")
        if len(errors) > 100:
            print(f"- ... and {len(errors) - 100} more")
        return 1

    print(
        f"AI compatibility validation passed: {len(pages)} pages, unique canonicals, valid JSON-LD, "
        "complete sitemap, knowledge graph, LLM indexes, search coverage, and unchanged page content."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
