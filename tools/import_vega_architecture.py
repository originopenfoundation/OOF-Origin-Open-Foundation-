#!/usr/bin/env python3
"""Import the canonical VEGA architecture package from the supplied PDF exports."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from import_pga_architecture import extract_blocks, page, render_blocks


ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / "Downloads"
OUT = ROOT / "content" / "vega"


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
    Standard("vgs", "Value Governance Standard (VGS™)", "Gmail - Fwd_ VEGA 1 Value Governance Standard (VGS™).pdf", (
        Module("vdm", "Value Definition Module"), Module("vclm", "Value Classification Module"),
        Module("vqm", "Value Qualification Module"), Module("vvm", "Value Validation Module"),
        Module("vtm", "Value Threshold Module"))),
    Standard("xgs", "Execution Governance Standard (XGS™)", "Gmail - Fwd_ 2Execution Governance Standard (XGS™).pdf", (
        Module("elm", "Execution Legitimacy Module"), Module("ecm", "Execution Configuration Module"),
        Module("etgm", "Execution Trigger Module"), Module("ebm", "Execution Boundary Module"),
        Module("etm", "Execution Termination Module"))),
    Standard("ips", "Intelligence Productivity Standard (IPS)", "Gmail - Fwd_ 3Intelligence Productivity Standard (IPS).pdf", (
        Module("hpem", "Human Power Equivalency Module"), Module("iopm", "Intelligence Output Productivity Module"),
        Module("vcpm", "Validated Completion Productivity Module"), Module("cpm", "Cognitive Productivity Module"),
        Module("pnm", "Productivity Normalization Module"))),
    Standard("rgs", "Resource Governance Standard (RGS)", "Gmail - Fwd_ 4Resource Governance Standard (RGS).pdf", (
        Module("rim", "Resource Identification Module"), Module("rsam", "Resource Scope & Allocation Module"),
        Module("drrm", "Dynamic Resource Reallocation Module"), Module("rcm", "Resource Constraint Module"),
        Module("rctm", "Resource Consumption Traceability Module"))),
    Standard("cos", "Computational Optimization Standard (COS)", "Gmail - Fwd_ 5Computational Optimization Standard (COS) 8.pdf", (
        Module("psem", "Problem-Space Efficiency Module"), Module("cgem", "Cognitive Efficiency Governance Module"),
        Module("oem", "Orchestration Efficiency Module"), Module("maem", "Model Allocation Efficiency Module"),
        Module("caem", "Compute Allocation Efficiency Module"), Module("heem", "Hardware Execution Efficiency Module"))),
    Standard("ies", "Intelligence Economy Standard (IES)", "Gmail - Fwd_ 6Intelligence Economy Standard (IES).pdf", (
        Module("etcm", "Effective Task Cost Module"), Module("fsm", "Failure Spend Module"),
        Module("ccm", "Correction Cost Module"), Module("iroim", "Intelligence Return on Investment Module"),
        Module("vcm", "Value-to-Cost Module"))),
    Standard("svgs", "Strategic Value Governance Standard (SVGS)", "Gmail - Fwd_ 7Strategic Value Governance Standard (SVGS).pdf", (
        Module("svim", "Strategic Value Identification Module"), Module("cvm", "Capability Value Module"),
        Module("dvm", "Deferred Value Module"), Module("smm", "Strategic Milestone Module"),
        Module("carm", "Capital-at-Risk Module"))),
    Standard("iss", "Intelligence Sustainability Standard (ISS)", "Gmail - Fwd_ 8Intelligence Sustainability Standard (ISS).pdf", (
        Module("stm", "Sustainability Threshold Module"), Module("eevm", "Execution Energy Viability Module"),
        Module("ism", "Infrastructure Sustainability Module"), Module("ecom", "Economic Continuity Module"),
        Module("dsm", "Dependency Sustainability Module"))),
    Standard("vas", "Value Attribution Standard (VAS)", "Gmail - Fwd_ 9Value Attribution Standard (VAS).pdf", (
        Module("vsim", "Value Source Identification Module"), Module("catm", "Contribution Attribution Module"),
        Module("haam", "Human–AI Attribution Module"), Module("maam", "Multi-Agent Attribution Module"),
        Module("aem", "Attribution Evidence Module"))),
    Standard("dgs", "Decision Governance Standard (DGS)", "Gmail - Fwd_ 10Decision Governance Standard (DGS).pdf", (
        Module("decm", "Decision Evidence Consolidation Module"), Module("cdm", "Continuation Decision Module"),
        Module("sdm", "Scaling Decision Module"), Module("mdm", "Migration Decision Module"),
        Module("rdm", "Retirement Decision Module"))),
)

ARCHITECTURE_DOCS = (
    ("vega-about.html", "About VEGA™ — Value Execution Governance Architecture", "Gmail - Fwd_ About VEGA™ — Value Execution Governance Architecture.pdf"),
    ("vega-architecture-map.html", "VEGA™ Architecture Map", "Gmail - Fwd_ VEGA™ Architecture Map.pdf"),
    ("vega-complete-index.html", "VEGA™ Complete Standards & Modules Index", "Gmail - Fwd_ VEGA™ Complete Standards & Modules Index.pdf"),
    ("vega-architecture.html", "VEGA™ Value Execution Governance Architecture — Intelligence Value & Resource Governance Layer", "Gmail - Fwd_ VEGA™ Value Execution Governance Architecture — Intelligence Value & Resource Governance Layer.pdf"),
)

ABOUT_DOCS = (
    (ROOT / "content" / "m" / "mgia-about.html", "About MGIA™ — Memory Governance Intelligence Architecture", "Gmail - About MGIA™ — Memory Governance Intelligence Architecture.pdf", (
        ("MGIA™ Architecture Map", "../a/ais-mgia-map.html"),
        ("MGIA™ Architecture Index", "../r/ref-mgia-architecture-index.html"),
        ("MGIA™ Complete Standards & Modules Index", "../r/ref-mgia-complete-index.html"))),
    (ROOT / "content" / "a" / "aga-about.html", "About AGA™ — Accountability Governance Architecture", "Gmail - About AGA™ — Accountability Governance Architecture.pdf", (
        ("AGA™ Architecture Map", "ais-aga-map.html"),
        ("AGA™ Architecture Index", "../r/ref-aga-architecture-index.html"),
        ("AGA™ Complete Standards & Modules Index", "../r/ref-aga-complete-index.html"))),
    (ROOT / "content" / "c" / "clia-about.html", "About CLIA® — Cognitive Governance Intelligence Architecture", "Gmail - About CLIA® — Cognitive Governance Intelligence Architecture.pdf", (
        ("CLIA® Architecture Map", "../a/ais-clia-map.html"),
        ("CLIA® Architecture Index", "../r/ref-clia-architecture-index.html"),
        ("CLIA® Complete Standards & Modules Index", "../r/ref-clia-complete-index.html"))),
)

SITE_INDEX_START = "<!-- VEGA SITE INDEX START -->"
SITE_INDEX_END = "<!-- VEGA SITE INDEX END -->"


def related_links(standard: Standard) -> str:
    links = [f'<a href="vega-{standard.code}-about.html">About {html.escape(standard.title)}</a>']
    links.extend(
        f'<a href="vega-{standard.code}-{module.code}-{number}.html">{html.escape(module.title)} ({module.code.upper()})</a>'
        for number, module in enumerate(standard.modules, 1)
    )
    return '<hr><h2>Governed Links</h2><p>' + '<br>\n'.join(links) + '</p>'


def architecture_links() -> str:
    links = [f'<a href="vega-{standard.code}.html">{html.escape(standard.title)}</a>' for standard in STANDARDS]
    return '<hr><h2>VEGA™ Parent Standards</h2><p>' + '<br>\n'.join(links) + '</p>'


def split_standard(blocks: list[dict[str, str]], standard: Standard) -> tuple[list[dict], list[dict], list[list[dict]]]:
    markers = [index for index, block in enumerate(blocks) if block["type"] == "marker"]
    expected = len(standard.modules)
    if len(markers) != expected:
        raise ValueError(f"{standard.code.upper()}: expected {expected} module markers, found {len(markers)}")
    module_parts = [
        blocks[markers[index] + 1: markers[index + 1] if index + 1 < expected else len(blocks)]
        for index in range(expected)
    ]
    pre_modules = blocks[:markers[0]]
    first_title = next(block["text"] for block in pre_modules if block["type"] == "h")
    duplicates = [index for index, block in enumerate(pre_modules) if block["type"] == "h" and block["text"] == first_title]
    about_at = duplicates[1] if len(duplicates) > 1 else next(
        (index for index, block in enumerate(pre_modules) if block["type"] == "h" and block["text"].lower().startswith("about ")), -1
    )
    if about_at < 1:
        raise ValueError(f"{standard.code.upper()}: could not locate the About-standard section")
    return pre_modules[:about_at], pre_modules[about_at:], module_parts


def render_complete_index(blocks: list[dict[str, str]]) -> str:
    body = render_blocks(blocks)
    for number, standard in enumerate(STANDARDS, 1):
        heading_text = f"{number}. {standard.title.replace('™', '')}"
        heading_pattern = re.compile(rf"<h1>({re.escape(str(number) + '. ')}[^<]*{re.escape(standard.code.upper())}[^<]*)</h1>")
        body, count = heading_pattern.subn(
            rf'<h1><a href="vega-{standard.code}.html">\1</a></h1>', body, count=1
        )
        if count != 1:
            raise ValueError(f"{standard.code.upper()}: standard heading not found in complete index")
        for module_number, module in enumerate(standard.modules, 1):
            label = html.escape(f"{module.code.upper()} — {module.title}", quote=False)
            linked = f'<a href="vega-{standard.code}-{module.code}-{module_number}.html">{label}</a>'
            if label not in body:
                raise ValueError(f"{standard.code.upper()}: module label not found: {module.code.upper()}")
            body = body.replace(label, linked, 1)
    return body


def local_links(items: tuple[tuple[str, str], ...]) -> str:
    return '<hr><h2>Governed Links</h2><p>' + '<br>\n'.join(
        f'<a href="{href}">{html.escape(label)}</a>' for label, href in items
    ) + '</p>'


def site_index_section() -> str:
    lines = [
        SITE_INDEX_START,
        '<section class="container site-index-menu-section" data-vega-site-index="true">',
        '  <div class="oof-warning3 site-index-links site-index-grouped-links">',
        '    <h1>VEGA™ — Value Execution Governance Architecture</h1>',
        '    <h2>Architecture Documents</h2>',
        '    <a href="content/vega/vega-architecture-map.html">VEGA™ Architecture Map</a><br>',
        '    <a href="content/vega/vega-about.html">About VEGA™ — Value Execution Governance Architecture</a><br>',
        '    <a href="content/vega/vega-architecture.html">VEGA™ Value Execution Governance Architecture — Intelligence Value &amp; Resource Governance Layer</a><br>',
        '    <a href="content/vega/vega-complete-index.html">VEGA™ Complete Standards &amp; Modules Index</a><br>',
    ]
    for standard in STANDARDS:
        lines.extend([
            '    <hr class="site-index-divider">',
            f'    <h2>{html.escape(standard.title)}</h2>',
            f'    <a href="content/vega/vega-{standard.code}.html">{html.escape(standard.title)}</a><br>',
            f'    <a href="content/vega/vega-{standard.code}-about.html">About {html.escape(standard.title)}</a><br>',
        ])
        lines.extend(
            f'    <a href="content/vega/vega-{standard.code}-{module.code}-{number}.html">'
            f'{html.escape(module.title)} ({module.code.upper()})</a><br>'
            for number, module in enumerate(standard.modules, 1)
        )
    lines.extend(['  </div>', '  <section class="viewbor"></section>', '</section>', SITE_INDEX_END])
    return "\n".join(lines)


def update_site_index() -> None:
    target = ROOT / "oof-site-index.html"
    source = target.read_text(encoding="utf-8")
    block = site_index_section()
    if SITE_INDEX_START in source and SITE_INDEX_END in source:
        source = re.sub(
            rf"{re.escape(SITE_INDEX_START)}.*?{re.escape(SITE_INDEX_END)}",
            block,
            source,
            flags=re.S,
        )
    else:
        marker = "<!-- OOF SEMANTIC CONTENT END -->"
        if marker not in source:
            raise ValueError("Could not locate the Site Index semantic content boundary")
        source = source.replace(marker, block + "\n" + marker, 1)
    target.write_text(source, encoding="utf-8", newline="\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, title, source in ARCHITECTURE_DOCS:
        blocks = extract_blocks(DOWNLOADS / source)
        body = render_complete_index(blocks) if filename == "vega-complete-index.html" else render_blocks(blocks)
        target = OUT / filename
        target.write_text(page(title, body, architecture_links()), encoding="utf-8")
        written.append(target)

    for standard in STANDARDS:
        parent, about, modules = split_standard(extract_blocks(DOWNLOADS / standard.filename), standard)
        outputs = [
            (OUT / f"vega-{standard.code}.html", standard.title, parent, related_links(standard)),
            (OUT / f"vega-{standard.code}-about.html", f"About {standard.title}", about, related_links(standard)),
        ]
        outputs.extend(
            (OUT / f"vega-{standard.code}-{module.code}-{number}.html", module.title, content, "")
            for number, (module, content) in enumerate(zip(standard.modules, modules), 1)
        )
        for target, title, content, related in outputs:
            target.write_text(page(title, render_blocks(content), related), encoding="utf-8")
            written.append(target)

    for target, title, source, links in ABOUT_DOCS:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(title, render_blocks(extract_blocks(DOWNLOADS / source)), local_links(links)), encoding="utf-8")
        written.append(target)

    update_site_index()

    print(f"Wrote {len(written)} VEGA and architecture About pages")


if __name__ == "__main__":
    main()
