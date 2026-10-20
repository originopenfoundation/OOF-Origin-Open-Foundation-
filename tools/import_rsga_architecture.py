#!/usr/bin/env python3
"""Import the supplied RSGA standards and modules from canonical PDF exports."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from import_pga_architecture import clean, page


ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / "Downloads"
OUT = ROOT / "content" / "rsga"


@dataclass(frozen=True)
class Module:
    code: str
    title: str


@dataclass(frozen=True)
class Standard:
    code: str
    title: str
    filename: str
    modules: tuple[Module, ...]


STANDARDS = (
    Standard("rchs", "Resource Characterization Standard (RCHS)", "Gmail - Fwd_ RSGA 1 RCHS — Resource Characterization Standard.pdf", (
        Module("rbdm", "Resource Boundary Definition Module"), Module("rtcm", "Resource Type & Constraint Module"),
        Module("rsdm", "Resource State Definition Module"), Module("rosm", "Resource Origin & Source Module"),
        Module("rcxm", "Resource Context Module"))),
    Standard("racs", "Resource Availability & Capacity Standard (RACS)", "Gmail - Fwd_ 2Resource Availability & Capacity Standard (RACS).pdf", (
        Module("radm", "Resource Availability Determination Module"), Module("uccm", "Usable Capacity Condition Module"),
        Module("rvcm", "Reserved Capacity Module"), Module("tavm", "Temporal Availability Module"),
        Module("laam", "Location & Accessibility Module"))),
    Standard("rdgs", "Resource Demand Governance Standard (RDGS)", "Gmail - Fwd_ 3Resource Demand Governance Standard (RDGS).pdf", (
        Module("crdm", "Core Resource Demand Module"), Module("fdim", "Functional Demand Identification Module"),
        Module("pkdm", "Peak Demand Module"), Module("cpdm", "Concurrent & Parallel Demand Module"),
        Module("dcmm", "Demand Consolidation & Management Module"))),
    Standard("rdcs", "Resource Dependency & Criticality Standard (RDCS)", "Gmail - 4Resource Dependency & Criticality Standard (RDCS).pdf", (
        Module("rdmm", "Resource Dependency Mapping Module"), Module("rcam", "Resource Criticality Assessment Module"),
        Module("rcem", "Resource Consequence Evaluation Module"), Module("rdcm", "Resource Dependency Chain Module"),
        Module("rcdm", "Resource Criticality Determination Module"))),
    Standard("rags", "Resource Access Governance Standard (RAGS)", "Gmail - Fwd_ 5Resource Access Governance Standard (RAGS).pdf", (
        Module("raem", "Resource Access Eligibility Module"), Module("racm", "Resource Access Control Module"),
        Module("rrgm", "Resource Rights Governance Module"), Module("rrwm", "Resource Rights & Access Withdrawal Module"),
        Module("racrm", "Resource Access Continuity & Reassessment Module"))),
    Standard("rpas", "Resource Prioritization & Allocation Standard (RPAS)", "Gmail - Fwd_ 6Resource Prioritization & Allocation Standard (RPAS).pdf", (
        Module("rpdm", "Resource Priority Determination Module"), Module("rabm", "Resource Allocation Basis Module"),
        Module("ralm", "Resource Allocation Limits Module"), Module("rrem", "Resource Reallocation & Exception Module"),
        Module("cdbm", "Competing Demand Balancing Module"))),
    Standard("rcus", "Resource Consumption & Utilization Standard (RCUS)", "Gmail - Fwd_ 7Resource Consumption & Utilization Standard (RCUS).pdf", (
        Module("rcmm", "Resource Consumption Measurement Module"), Module("rusm", "Resource Utilization State Module"),
        Module("rcbm", "Resource Consumption Boundary Module"), Module("rucm", "Resource Use Context Module"),
        Module("rccm", "Resource Consumption Compliance Module"))),
    Standard("rscs", "Resource Scarcity & Constraint Standard (RSCS)", "Gmail - Fwd_ 8Resource Scarcity & Constraint Standard (RSCS).pdf", (
        Module("rssm", "Resource Scarcity State Module"), Module("rctm", "Resource Constraint Type Module"),
        Module("rsem", "Resource Scarcity Evaluation Module"), Module("rsrm", "Resource Scarcity Response Module"),
        Module("rcrm", "Resource Constraint Resolution Module"))),
    Standard("rrcs", "Resource Recovery & Circularity Standard (RRCS)", "Gmail - Fwd_ 9Resource Recovery & Circularity Standard (RRCS).pdf", (
        Module("errm", "End-of-Use Resource Recognition Module"), Module("rpmm", "Resource Recovery Potential Module"),
        Module("rurpm", "Resource Recovery Process Module"), Module("rrrgm", "Recovered Resource Recognition & Governance Module"),
        Module("srrm", "Secondary Resource Reintegration Module"))),
    Standard("rsfs", "Resource Substitution & Flexibility Standard (RSFS)", "Gmail - Fwd_ 10RSFS — Resource Substitution & Flexibility Standard.pdf", (
        Module("rsam", "Resource Substitution Assessment Module"), Module("rscm", "Resource Substitution Compatibility Module"),
        Module("rtsm", "Resource Transition & Substitution Module"), Module("rdfm", "Resource Dependency Flexibility Module"),
        Module("rswm", "Resource Substitution & Flexibility Monitoring Module"))),
    Standard("rirs", "Resource Interdependency & Resilience Standard (RIRS)", "Gmail - Fwd_ 11RIRS — Resource Interdependency & Resilience Standard.pdf", (
        Module("ridm", "Resource Interdependency Mapping Module"), Module("rdpm", "Resource Disturbance & Propagation Module"),
        Module("rrvm", "Resource Vulnerability & Resilience Capacity Module"), Module("rrrm", "Resource Response & Recovery Module"),
        Module("rrmm", "Resource Resilience Validation & Monitoring Module"))),
    Standard("rcss", "Resource Continuity & Sustainability Standard (RCSS)", "Gmail - Fwd_ 12 RCSS — Resource Continuity & Sustainability Standard.pdf", (
        Module("rcasm", "Resource Continuity Assessment Module"), Module("rcrsm", "Resource Consumption & Replenishment Sustainability Module"),
        Module("rsitm", "Resource Sustainability Impact & Tradeoff Module"), Module("rsvm", "Resource Sustainability Validation Module"),
        Module("rcsmm", "Resource Continuity & Sustainability Monitoring Module"))),
)

METADATA_LABELS = (
    "Architecture", "Parent Standard", "Category", "Subcategory", "Type", "Governed Space",
    "Standard ID", "Module ID", "Origin ID", "Version", "Status", "Effective Date", "Compatibility",
    "GIE-Compatible", "AI-Readable", "Authority", "Protection", "Canonical Language",
)


def prepare_blocks(path: Path, standard: Standard) -> list[dict[str, str]]:
    blocks = extract_all_blocks(path)
    title_index = next(
        index for index, block in enumerate(blocks)
        if block["text"].strip() in {standard.title, f'{standard.code.upper()} — {standard.title}'}
        or (block["text"].startswith(f'{standard.code.upper()} — ') and "Standard" in block["text"])
    )
    blocks = blocks[title_index:]
    prepared: list[dict[str, str]] = []
    for index, block in enumerate(blocks):
        text = block["text"].strip()
        block_type = block["type"]
        if block_type != "marker":
            if index == 0 or re.fullmatch(r"\d+\.\s+.+", text) or text.startswith("About "):
                block_type = "h"
            elif any(text == label or text.startswith(label + " ") for label in METADATA_LABELS):
                block_type = "meta"
            else:
                block_type = "p"
        prepared.append({"type": block_type, "text": text})
    return prepared


def extract_all_blocks(path: Path) -> list[dict[str, str]]:
    """Extract every content block without relying on PDF-specific heading fonts."""
    lines: list[dict[str, object]] = []
    with pdfplumber.open(path) as pdf:
        for page_no, pdf_page in enumerate(pdf.pages):
            words = pdf_page.extract_words(extra_attrs=["fontname", "size"])
            rows: list[list[dict]] = []
            for word in words:
                if word["top"] < 25 or word["top"] > pdf_page.height - 32:
                    continue
                for row in rows:
                    if abs(row[0]["top"] - word["top"]) <= 2.0:
                        row.append(word)
                        break
                else:
                    rows.append([word])
            rows.sort(key=lambda row: row[0]["top"])
            for row in rows:
                row.sort(key=lambda word: word["x0"])
                text = clean(" ".join(word["text"] for word in row))
                lines.append({"text": text, "page": page_no, "top": float(row[0]["top"])})

    blocks: list[dict[str, str]] = []
    current: list[str] = []
    previous: dict[str, object] | None = None

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append({"type": "p", "text": clean(" ".join(current))})
            current = []

    for line in lines:
        text = str(line["text"])
        if re.fullmatch(r"(?i)modul(?:e)?\s*\d+", text):
            flush()
            blocks.append({"type": "marker", "text": text})
            previous = line
            continue
        if current:
            same_page = previous is not None and previous["page"] == line["page"]
            gap = float(line["top"]) - float(previous["top"]) if same_page else 99.0
            if not same_page or gap >= 16:
                flush()
        current.append(text)
        previous = line
    flush()
    return blocks


def split_standard(blocks: list[dict[str, str]], standard: Standard) -> tuple[list[dict], list[dict], list[list[dict]]]:
    markers = [index for index, block in enumerate(blocks) if block["type"] == "marker"]
    if len(markers) != len(standard.modules):
        raise ValueError(f"{standard.code.upper()}: expected {len(standard.modules)} module markers, found {len(markers)}")
    pre_modules = blocks[:markers[0]]
    about_at = next((
        index for index, block in enumerate(pre_modules)
        if block["text"].startswith("About ")
        and len(block["text"]) > 18
        and block["text"].lower() not in {"about standard", "about srandard"}
    ), -1)
    if about_at < 1:
        raise ValueError(f"{standard.code.upper()}: could not locate the About-standard section")
    preview_at = next((
        index for index, block in enumerate(pre_modules[:about_at])
        if block["text"].strip().lower() in {"nahlad", "náhľad", "preview"}
    ), about_at)
    modules = [
        blocks[markers[index] + 1: markers[index + 1] if index + 1 < len(markers) else len(blocks)]
        for index in range(len(markers))
    ]
    return pre_modules[:preview_at], pre_modules[about_at:], modules


def render_blocks(blocks: list[dict[str, str]]) -> str:
    rendered: list[str] = []
    for block in blocks:
        if block["type"] == "marker":
            continue
        text = html.escape(block["text"], quote=False)
        if block["type"] == "h":
            rendered.append(f"<h1>{text}</h1>")
        elif block["type"] == "meta":
            for label in METADATA_LABELS:
                if text == label:
                    text = f"<b>{html.escape(label)}:</b>"
                    break
                if text.startswith(html.escape(label) + " "):
                    text = f"<b>{html.escape(label)}:</b> " + text[len(html.escape(label)) + 1:]
                    break
            rendered.append(f'<p class="podstand">{text}</p>')
        else:
            rendered.append(f"<p>{text}</p>")
    return "\n".join(rendered)


def normalize_module_code(content: list[dict[str, str]], standard: Standard, module: Module) -> list[dict[str, str]]:
    """Apply approved identifier corrections without altering the canonical module title."""
    if standard.code != "rcss" or module.code != "rcasm":
        return content
    return [{**block, "text": re.sub(r"\bRCAM\b", "RCASM", block["text"])} for block in content]


def related_links(standard: Standard) -> str:
    links = [f'<a href="rsga-{standard.code}-about.html">About {html.escape(standard.title)}</a>']
    links.extend(
        f'<a href="rsga-{standard.code}-{module.code}-{number}.html">{html.escape(module.title)} ({module.code.upper()})</a>'
        for number, module in enumerate(standard.modules, 1)
    )
    return '<hr><h2>Governed Links</h2><p>' + '<br>\n'.join(links) + '</p>'


def index_body() -> str:
    flow = " → ".join(standard.title.split(" Standard")[0] for standard in STANDARDS)
    lines = [
        "<h1>RSGA™ Complete Standards &amp; Modules Index</h1>",
        "<p>Resource Sustainability Governance Architecture</p>",
        '<p class="podstand"><b>Governance Flow:</b></p>',
        f"<p>{html.escape(flow)}</p>",
        "<p>RSGA™ contains 12 Parent Standards and 60 Core Modules governing the Resource Sustainability lifecycle.</p>",
    ]
    for number, standard in enumerate(STANDARDS, 1):
        lines.append(f'<hr><h1><a href="rsga-{standard.code}.html">{number}. {html.escape(standard.title)}</a></h1>')
        lines.append(f'<p><a href="rsga-{standard.code}-about.html">About {html.escape(standard.title)}</a></p>')
        for module_number, module in enumerate(standard.modules, 1):
            lines.append(
                f'<p><a href="rsga-{standard.code}-{module.code}-{module_number}.html">'
                f'{module.code.upper()} — {html.escape(module.title)}</a></p>'
            )
    return "\n".join(lines)


def site_index_block() -> str:
    lines = [
        "<!-- RSGA SITE INDEX START -->",
        '<section class="container site-index-menu-section" data-rsga-site-index="true">',
        '  <div class="oof-warning3 site-index-links site-index-grouped-links">',
        '    <h1>RSGA™ — Resource Sustainability Governance Architecture</h1>',
        '    <a href="content/rsga/rsga-complete-index.html">RSGA™ Complete Standards &amp; Modules Index</a><br>',
    ]
    for standard in STANDARDS:
        lines.extend([
            '    <hr class="site-index-divider">',
            f'    <h2>{html.escape(standard.title)}</h2>',
            f'    <a href="content/rsga/rsga-{standard.code}.html">{html.escape(standard.title)}</a><br>',
            f'    <a href="content/rsga/rsga-{standard.code}-about.html">About {html.escape(standard.title)}</a><br>',
        ])
        lines.extend(
            f'    <a href="content/rsga/rsga-{standard.code}-{module.code}-{number}.html">'
            f'{html.escape(module.title)} ({module.code.upper()})</a><br>'
            for number, module in enumerate(standard.modules, 1)
        )
    lines.extend(['  </div>', '  <section class="viewbor"></section>', '</section>', '<!-- RSGA SITE INDEX END -->'])
    return "\n".join(lines)


def update_site_index() -> None:
    target = ROOT / "oof-site-index.html"
    source = target.read_text(encoding="utf-8")
    block = site_index_block()
    if "<!-- RSGA SITE INDEX START -->" in source:
        source = re.sub(r"<!-- RSGA SITE INDEX START -->.*?<!-- RSGA SITE INDEX END -->", block, source, flags=re.S)
    else:
        marker = "<!-- VEGA SITE INDEX START -->"
        if marker not in source:
            raise ValueError("Could not locate Site Index insertion point")
        source = source.replace(marker, block + "\n" + marker, 1)
    target.write_text(source, encoding="utf-8", newline="\n")


def architecture_index_block() -> str:
    links = "\n".join(
        f'  <a href="content/rsga/rsga-{standard.code}.html">{html.escape(standard.title)}</a><br>'
        for standard in STANDARDS
    )
    return (
        '<!-- RSGA ARCHITECTURE INDEX START -->\n'
        '<section class="container" data-rsga-architecture="true"><div class="oof-warning20">\n'
        '<h1>RSGA™ — Resource Sustainability Governance Architecture (12)</h1>\n'
        f'{links}\n'
        '<p><a href="content/rsga/rsga-complete-index.html">Complete Standards &amp; Modules Index</a></p>\n'
        '</div><section class="viewbor"></section></section>\n'
        '<!-- RSGA ARCHITECTURE INDEX END -->'
    )


def update_architecture_index() -> None:
    target = ROOT / "oof-structured-architecture-index.html"
    source = target.read_text(encoding="utf-8")
    block = architecture_index_block()
    if "<!-- RSGA ARCHITECTURE INDEX START -->" in source:
        source = re.sub(r"<!-- RSGA ARCHITECTURE INDEX START -->.*?<!-- RSGA ARCHITECTURE INDEX END -->", block, source, flags=re.S)
    else:
        marker = '<section class="container" data-vega-architecture="true">'
        if marker not in source:
            raise ValueError("Could not locate Architecture Standards Index insertion point")
        source = source.replace(marker, block + "\n\n" + marker, 1)
    target.write_text(source, encoding="utf-8", newline="\n")


def update_header() -> None:
    target = ROOT / "header.html"
    source = target.read_text(encoding="utf-8")
    block = '''<!-- RSGA HEADER START -->
    <h4 class="burger-toggle burger-subtitle" onclick="toggleBurgerSub('burgerRefRsgaMenu', this)">
      RSGA™ — Resource Sustainability Governance Architecture
    </h4>
    <div id="burgerRefRsgaMenu" class="burger-submenu burger-subsection">
      <a href="content/rsga/rsga-complete-index.html">RSGA™ Complete Standards &amp; Modules Index</a>
''' + "\n".join(
        f'      <a href="content/rsga/rsga-{standard.code}.html">{html.escape(standard.title)}</a>'
        for standard in STANDARDS
    ) + '''
    </div>
    <!-- RSGA HEADER END -->'''
    if "<!-- RSGA HEADER START -->" in source:
        source = re.sub(r"<!-- RSGA HEADER START -->.*?<!-- RSGA HEADER END -->", block, source, flags=re.S)
    else:
        marker = "      VEGA™ — Value Execution Governance Architecture\n"
        at = source.find(marker)
        if at < 0:
            raise ValueError("Could not locate VEGA header section")
        section_at = source.rfind('    <h4 class="burger-toggle burger-subtitle"', 0, at)
        source = source[:section_at] + block + "\n\n" + source[section_at:]
    target.write_text(source, encoding="utf-8", newline="\n")


def write_legacy_rcam_alias() -> Path:
    """Keep the former duplicate identifier reachable while excluding it from discovery."""
    target = OUT / "rsga-rcss-rcam-1.html"
    destination = "/content/rsga/rsga-rcss-rcasm-1.html"
    target.write_text(
        """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="robots" content="noindex, follow" />
<link rel="canonical" href="https://originopenfoundation.org/content/rsga/rsga-rcss-rcasm-1.html" />
<meta http-equiv="refresh" content="0; url=/content/rsga/rsga-rcss-rcasm-1.html" />
<title>Resource Continuity Assessment Module | OOF®</title>
</head>
<body>
<p>This reference has moved to <a href="/content/rsga/rsga-rcss-rcasm-1.html">RCASM — Resource Continuity Assessment Module</a>.</p>
<script>location.replace("/content/rsga/rsga-rcss-rcasm-1.html");</script>
</body>
</html>
""",
        encoding="utf-8",
    )
    return target


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for standard in STANDARDS:
        source = DOWNLOADS / standard.filename
        parent, about, modules = split_standard(prepare_blocks(source, standard), standard)
        outputs = [
            (OUT / f"rsga-{standard.code}.html", standard.title, parent, related_links(standard)),
            (OUT / f"rsga-{standard.code}-about.html", f"About {standard.title}", about, related_links(standard)),
        ]
        outputs.extend(
            (
                OUT / f"rsga-{standard.code}-{module.code}-{number}.html",
                module.title,
                normalize_module_code(content, standard, module),
                "",
            )
            for number, (module, content) in enumerate(zip(standard.modules, modules), 1)
        )
        for target, title, content, related in outputs:
            target.write_text(page(title, render_blocks(content), related), encoding="utf-8")
            written.append(target)

    index_target = OUT / "rsga-complete-index.html"
    index_target.write_text(page("RSGA™ Complete Standards & Modules Index", index_body()), encoding="utf-8")
    written.append(index_target)
    update_header()
    update_site_index()
    update_architecture_index()
    written.append(write_legacy_rcam_alias())
    print(f"Wrote {len(written)} RSGA pages to {OUT}")


if __name__ == "__main__":
    main()
