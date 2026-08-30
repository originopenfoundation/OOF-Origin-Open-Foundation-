#!/usr/bin/env python3
"""Generate non-visual AI discovery metadata for the complete OOF website."""

from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse
from xml.sax.saxutils import escape as xml_escape


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://originopenfoundation.org/"
SITE_NAME = "OOF® — OriginOpen® Foundation"
START = "<!-- OOF AI DISCOVERY START -->"
END = "<!-- OOF AI DISCOVERY END -->"
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\s*", re.S)
FIELD_NAMES = (
    "OriginID",
    "Architecture",
    "Architecture Family",
    "Parent Standard",
    "Category",
    "Subcategory",
    "Type",
    "Governed Space",
    "Status",
    "Canonical Language",
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.heading_parts: list[str] = []
        self.text_parts: list[str] = []
        self.hrefs: list[str] = []
        self.in_title = False
        self.in_heading = False
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self.ignored += 1
        if tag == "title":
            self.in_title = True
        if tag in {"h1", "h2"} and not self.heading_parts:
            self.in_heading = True
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href.strip())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self.ignored:
            self.ignored -= 1
        if tag == "title":
            self.in_title = False
        if tag in {"h1", "h2"}:
            self.in_heading = False

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return
        if self.in_title:
            self.title_parts.append(value)
        if self.in_heading and not self.heading_parts:
            self.heading_parts.append(value)
        if not self.ignored:
            self.text_parts.append(value)

    def title(self, fallback: str) -> str:
        value = " ".join(self.title_parts) or " ".join(self.heading_parts) or fallback
        return clean_text(value)

    def visible_text(self) -> str:
        return clean_text(" ".join(self.text_parts))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def public_pages() -> list[Path]:
    pages = []
    candidates = sorted(ROOT.rglob("*.html"), key=lambda item: item.relative_to(ROOT).as_posix().casefold())
    for path in candidates:
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "</head>" in text.lower():
            pages.append(path)
    return pages


def relative_url(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def encoded_path(value: str) -> str:
    return quote(unquote(value), safe="/-._~()")


def canonical_url(path_or_relative: Path | str) -> str:
    relative = relative_url(path_or_relative) if isinstance(path_or_relative, Path) else path_or_relative
    if relative == "index.html":
        return BASE_URL
    return urljoin(BASE_URL, encoded_path(relative))


def extract_fields(source: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for field in FIELD_NAMES:
        pattern = re.compile(
            rf"<(?:b|strong)>\s*{re.escape(field)}\s*:\s*</(?:b|strong)>\s*(.*?)(?=<br\s*/?>|</p>|</a>)",
            re.I | re.S,
        )
        match = pattern.search(source)
        if not match:
            continue
        value = clean_text(re.sub(r"<[^>]+>", " ", match.group(1)))
        if value:
            fields[field] = value
    return fields


def resolve_internal_links(page_path: Path, hrefs: list[str], known_urls: set[str]) -> list[str]:
    current = canonical_url(page_path)
    links: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue
        parsed = urlparse(urljoin(current, href))
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc.lower() not in {"", "originopenfoundation.org", "www.originopenfoundation.org"}:
            continue
        relative = unquote(parsed.path.lstrip("/"))
        if not relative or relative not in known_urls:
            continue
        target = canonical_url(relative)
        if target != current and target not in seen:
            seen.add(target)
            links.append(target)
    return links


def page_type(title: str, relative: str) -> str:
    lowered = f"{title} {relative}".casefold()
    if relative == "index.html":
        return "WebPage"
    if any(word in lowered for word in ("index", "architecture map", "site map")):
        return "CollectionPage"
    if "faq" in lowered:
        return "WebPage"
    return "TechArticle" if relative.startswith("content/") else "WebPage"


def inspect_pages(paths: list[Path]) -> list[dict]:
    known_urls = {relative_url(path) for path in paths}
    records = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(source)
        relative = relative_url(path)
        title = parser.title(path.stem.replace("-", " ").strip())
        fields = extract_fields(source)
        records.append(
            {
                "path": path,
                "relative": relative,
                "canonical": canonical_url(relative),
                "title": title,
                "language": "en",
                "schemaType": page_type(title, relative),
                "fields": fields,
                "links": resolve_internal_links(path, parser.hrefs, known_urls),
                "visibleText": parser.visible_text(),
            }
        )
    return records


def page_json_ld(record: dict) -> dict:
    data: dict = {
        "@context": "https://schema.org",
        "@type": record["schemaType"],
        "@id": record["canonical"] + "#webpage",
        "url": record["canonical"],
        "name": record["title"],
        "inLanguage": record["language"],
        "isPartOf": {"@id": BASE_URL + "#website"},
        "publisher": {"@id": BASE_URL + "#organization"},
    }
    if record["schemaType"] == "TechArticle":
        data["headline"] = record["title"]
        data["author"] = {"@id": BASE_URL + "#organization"}
        data["mainEntityOfPage"] = {"@id": record["canonical"] + "#webpage"}
    topics = [
        record["fields"].get(field)
        for field in ("Architecture", "Architecture Family", "Parent Standard", "Category", "Subcategory", "Governed Space")
        if record["fields"].get(field)
    ]
    if topics:
        data["keywords"] = topics
        data["about"] = [{"@type": "Thing", "name": topic} for topic in topics]
    if record["links"]:
        data["relatedLink"] = record["links"]
    if record["fields"].get("OriginID"):
        data["identifier"] = record["fields"]["OriginID"]
    if record["fields"]:
        data["additionalProperty"] = [
            {"@type": "PropertyValue", "name": key, "value": value}
            for key, value in record["fields"].items()
        ]
    return data


def metadata_block(record: dict) -> str:
    canonical = html.escape(record["canonical"], quote=True)
    title = html.escape(record["title"], quote=True)
    json_ld = json.dumps(page_json_ld(record), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return "\n".join(
        [
            START,
            f'<link rel="canonical" href="{canonical}" />',
            f'<link rel="alternate" hreflang="en" href="{canonical}" />',
            f'<link rel="alternate" hreflang="x-default" href="{canonical}" />',
            f'<link rel="alternate" type="application/ld+json" href="{BASE_URL}data/oof-site-knowledge-graph.json" title="OOF Site Knowledge Graph" />',
            f'<link rel="alternate" type="text/plain" href="{BASE_URL}llms.txt" title="OOF LLM Index" />',
            '<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1" />',
            '<meta name="googlebot" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1" />',
            '<meta name="content-language" content="en" />',
            f'<meta name="DC.title" content="{title}" />',
            '<meta name="DC.language" content="en" />',
            f'<meta name="DC.identifier" content="{canonical}" />',
            f'<script type="application/ld+json">{json_ld}</script>',
            END,
        ]
    )


def inject_metadata(record: dict) -> None:
    path = record["path"]
    source = path.read_text(encoding="utf-8")
    source = BLOCK_RE.sub("", source)
    source = re.sub(r"</head>", metadata_block(record) + "\n</head>", source, count=1, flags=re.I)
    path.write_text(source, encoding="utf-8", newline="\n")


def graph_record(record: dict) -> dict:
    item: dict = {
        "@type": record["schemaType"],
        "@id": record["canonical"] + "#webpage",
        "url": record["canonical"],
        "name": record["title"],
        "inLanguage": record["language"],
        "isPartOf": {"@id": BASE_URL + "#website"},
    }
    if record["schemaType"] == "TechArticle":
        item["headline"] = record["title"]
        item["author"] = {"@id": BASE_URL + "#organization"}
        item["mainEntityOfPage"] = {"@id": record["canonical"] + "#webpage"}
    topics = [
        record["fields"].get(field)
        for field in ("Architecture", "Architecture Family", "Parent Standard", "Category", "Subcategory", "Governed Space")
        if record["fields"].get(field)
    ]
    if topics:
        item["keywords"] = topics
        item["about"] = [{"@type": "Thing", "name": topic} for topic in topics]
    if record["links"]:
        item["relatedLink"] = record["links"]
    if record["fields"].get("OriginID"):
        item["identifier"] = record["fields"]["OriginID"]
    if record["fields"]:
        item["additionalProperty"] = [
            {"@type": "PropertyValue", "name": key, "value": value}
            for key, value in record["fields"].items()
        ]
    return item


def write_knowledge_graph(records: list[dict]) -> None:
    graph = [
        {
            "@type": "Organization",
            "@id": BASE_URL + "#organization",
            "name": SITE_NAME,
            "url": BASE_URL,
            "logo": canonical_url("favicon.png"),
        },
        {
            "@type": "WebSite",
            "@id": BASE_URL + "#website",
            "name": SITE_NAME,
            "url": BASE_URL,
            "inLanguage": "en",
            "publisher": {"@id": BASE_URL + "#organization"},
            "hasPart": [{"@id": record["canonical"] + "#webpage"} for record in records],
        },
    ]
    graph.extend(graph_record(record) for record in records)
    output = {"@context": "https://schema.org", "@graph": graph}
    path = ROOT / "data" / "oof-site-knowledge-graph.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_sitemap(records: list[dict]) -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for record in records:
        lines.extend(["  <url>", f'    <loc>{xml_escape(record["canonical"])}</loc>', "  </url>"])
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_robots() -> None:
    text = "\n".join(["User-agent: *", "Allow: /", "", f"Sitemap: {BASE_URL}sitemap.xml", ""])
    (ROOT / "robots.txt").write_text(text, encoding="utf-8", newline="\n")


def write_llm_indexes(records: list[dict]) -> None:
    preferred = [
        "index.html",
        "oof-site-index.html",
        "oof-structured-architecture-index.html",
        "standardinde.html",
        "reference-architectures.html",
        "content/v/validos-architecture.html",
        "content/v/validos-complete-index.html",
    ]
    by_relative = {record["relative"]: record for record in records}
    lines = [
        f"# {SITE_NAME}",
        "",
        "> Canonical methodological reference website for OOF architectures, standards, modules, services, and governance resources.",
        "",
        "All canonical documents are in English. Follow each document's explicit hierarchy and governed links; do not infer compatibility from proximity or link volume.",
        "",
        "## Primary Navigation",
        "",
    ]
    for relative in preferred:
        if relative in by_relative:
            record = by_relative[relative]
            lines.append(f'- [{record["title"]}]({record["canonical"]})')
    lines.extend(
        [
            "",
            "## Machine-Readable Resources",
            "",
            f"- [XML Sitemap]({BASE_URL}sitemap.xml)",
            f"- [OOF Site Knowledge Graph]({BASE_URL}data/oof-site-knowledge-graph.json)",
            f"- [OOF Governed Relationship Registry]({BASE_URL}data/oof-relationship-registry.json)",
            f"- [Site Search Index]({BASE_URL}search-index.json)",
            f"- [Complete Page Catalog]({BASE_URL}llms-full.txt)",
            "",
            "## Retrieval Guidance",
            "",
            "Use canonical URLs from the sitemap or knowledge graph. Treat Parent Resources, Standards Compatibility, Module Flow, and Cross-Architecture Interfaces as distinct governed relationship types.",
            "",
        ]
    )
    (ROOT / "llms.txt").write_text("\n".join(lines), encoding="utf-8", newline="\n")

    full = [
        f"# {SITE_NAME} — Complete Page Catalog",
        "",
        f"> {len(records)} canonical HTML documents. Fetch the linked canonical page for its authoritative content and formatting.",
        "",
    ]
    current_group = None
    for record in records:
        parts = record["relative"].split("/")
        group = "Root Documents" if len(parts) == 1 else "/".join(parts[:-1])
        if group != current_group:
            if current_group is not None:
                full.append("")
            full.extend([f"## {group}", ""])
            current_group = group
        full.append(f'- [{record["title"]}]({record["canonical"]})')
    full.append("")
    (ROOT / "llms-full.txt").write_text("\n".join(full), encoding="utf-8", newline="\n")


def update_search_index(records: list[dict]) -> int:
    path = ROOT / "search-index.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    existing = {entry.get("url") for entry in entries}
    added = 0
    for record in records:
        if record["relative"] in existing:
            continue
        entries.append({"title": record["title"], "url": record["relative"], "text": record["visibleText"]})
        existing.add(record["relative"])
        added += 1
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return added


def main() -> None:
    paths = public_pages()
    records = inspect_pages(paths)
    for record in records:
        inject_metadata(record)
    write_knowledge_graph(records)
    write_sitemap(records)
    write_robots()
    write_llm_indexes(records)
    added = update_search_index(records)
    print(f"AI compatibility generated for {len(records)} pages; {added} missing search entries added.")


if __name__ == "__main__":
    main()
