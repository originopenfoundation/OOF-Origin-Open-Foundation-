#!/usr/bin/env python3
"""Import the canonical PGA architecture package from the supplied PDF exports."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / "Downloads"
OUT = ROOT / "content" / "pga"


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
    Standard("pops", "Prediction Object & Purpose Standard (POPS)", "Gmail - Fwd_ PGA 1 Prediction Object & Purpose Standard.pdf", (
        Module("poim", "Prediction Object Identification Module"), Module("ppdm", "Prediction Purpose Definition Module"),
        Module("ptsm", "Prediction Target Specification Module"), Module("phdm", "Prediction Horizon Definition Module"),
        Module("pbem", "Prediction Boundary Establishment Module"))),
    Standard("pmes", "Prediction Methodology Standard (PMES)", "Gmail - Fwd_ 2 Prediction Methodology Standard (PMES).pdf", (
        Module("pmsm", "Prediction Methodology Specification Module"), Module("msdm", "Methodological Structure Definition Module"),
        Module("pldm", "Prediction Logic Documentation Module"), Module("mapm", "Methodology Application Module"),
        Module("mvgm", "Methodology Version Governance Module"))),
    Standard("pbas", "Prediction Basis Standard (PBAS)", "Gmail - Fwd_ 4Prediction Basis Standard (PBAS).pdf", (
        Module("piim", "Prediction Information Identification Module"), Module("psmm", "Prediction Signal Mapping Module"),
        Module("srvm", "Source Relevance & Validity Module"), Module("isum", "Information Sufficiency Module"),
        Module("pbtrm", "Prediction Basis Traceability Module"))),
    Standard("pas", "Prediction Assumption Standard (PAS)", "Gmail - Fwd_ 4Prediction Assumption Standard (PAS).pdf", (
        Module("paim", "Prediction Assumption Identification Module"), Module("admm", "Assumption Dependency Mapping Module"),
        Module("asnm", "Assumption Sensitivity Module"), Module("amam", "Assumption Materiality Assessment Module"),
        Module("acgm", "Assumption Change Governance Module"))),
    Standard("pfos", "Prediction Formation Standard (PFOS)", "Gmail - Fwd_ 5PFOS — Prediction Formation Standard.pdf", (
        Module("pcom", "Prediction Component Organization Module"), Module("pcim", "Prediction Condition Integration Module"),
        Module("pofm", "Prediction Output Formation Module"), Module("psem", "Prediction State Establishment Module"),
        Module("pftm", "Prediction Formation Traceability Module"))),
    Standard("ppus", "Prediction Probability & Uncertainty Standard (PPUS)", "Gmail - 6 standard je tuto zabudol som dat nadpis.pdf", (
        Module("prpm", "Prediction Probability Representation Module"), Module("punm", "Prediction Uncertainty Module"),
        Module("cfrm", "Confidence Representation Module"), Module("prgm", "Prediction Range Governance Module"),
        Module("cpm", "Conditional Probability Module"))),
    Standard("pfes", "Prediction Feasibility Standard (PFES)", "Gmail - Fwd_ 7PFES — Prediction Feasibility Standard.pdf", (
        Module("fcim", "Feasibility Condition Identification Module"), Module("pcmm", "Prediction Constraint Mapping Module"),
        Module("opam", "Operational Plausibility Assessment Module"), Module("eofm", "Execution & Outcome Feasibility Module"),
        Module("fsdm", "Feasibility State Determination Module"))),
    Standard("cpgs", "Collective Prediction Governance Standard (CPGS)", "Gmail - Fwd_ 8CPGS — Collective Prediction Governance Standard.pdf", (
        Module("psdm", "Prediction Source Diversity Module"), Module("pdvm", "Prediction Diversity Validation Module"),
        Module("pagm", "Prediction Aggregation Governance Module"), Module("picm", "Prediction Independence & Concentration Module"),
        Module("cprm", "Collective Prediction Representation Module"))),
    Standard("pcrs", "Prediction Communication & Reliance Standard (PCRS)", "Gmail - Fwd_ 9PCRS — Prediction Communication & Reliance Standard.pdf", (
        Module("prsm", "Prediction Representation & Signaling Module"), Module("pldim", "Prediction-Led Decision Interpretation Module"),
        Module("pibm", "Prediction Interpretation Boundary Module"), Module("rlcm", "Reliance Legitimacy & Context Module"),
        Module("pubm", "Prediction Use Boundary Module"))),
    Standard("pmrs", "Prediction Monitoring & Revision Standard (PMRS)", "Gmail - 10 standard.pdf", (
        Module("pchm", "Prediction Change Monitoring Module"), Module("rtm", "Review Trigger Module"),
        Module("prvm", "Prediction Revision Module"), Module("pssm", "Prediction Supersession Module"),
        Module("pwm", "Prediction Withdrawal Module"))),
    Standard("pofps", "Prediction Outcome & Performance Standard (POFPS)", "Gmail - Fwd_ 11POFPS — Prediction Outcome & Performance Standard.pdf", (
        Module("poam", "Prediction Outcome Association Module"), Module("pocm", "Prediction Outcome Comparison Module"),
        Module("pemm", "Prediction Error Measurement Module"), Module("pcalm", "Prediction Calibration Module"),
        Module("ppcm", "Predictive Performance Comparison Module"))),
    Standard("prcs", "Prediction Record & Continuity Standard (PRCS)", "Gmail - Fwd_ 12PRCS — Prediction Record & Continuity Standard.pdf", (
        Module("prfm", "Prediction Record Formation Module"), Module("pvcm", "Prediction Version Continuity Module"),
        Module("phpm", "Prediction History Preservation Module"), Module("prstm", "Prediction Record State Transition Module"),
        Module("prrm", "Prediction Record Re-Entry Module"))),
)

ARCHITECTURE_DOCS = (
    ("pga-about.html", "About PGA™ — Prediction Governance Architecture", "Gmail - Fwd_ About PGA™ — Prediction Governance Architecture.pdf"),
    ("pga-architecture-map.html", "PGA™ Architecture Map", "Gmail - Fwd_ PGA™ Architecture Map.pdf"),
    ("pga-complete-index.html", "PGA™ Complete Standards & Modules Index", "Gmail - Fwd_ PGA™ Complete Standards & Modules Index.pdf"),
    ("pga-architecture.html", "PGA™ Prediction Governance Architecture — Prediction Governance Layer", "Gmail - Fwd_ PGA™ Prediction Governance Architecture — Prediction Governance Layer.pdf"),
)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_blocks(path: Path) -> list[dict[str, str]]:
    lines: list[dict[str, object]] = []
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages):
            words = page.extract_words(extra_attrs=["fontname", "size"])
            rows: list[list[dict]] = []
            for word in words:
                if word["top"] < 25 or word["top"] > page.height - 32:
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
                black = sum("Arial-Black" in word["fontname"] for word in row)
                max_size = max(float(word["size"]) for word in row)
                lines.append({"text": text, "page": page_no, "top": float(row[0]["top"]),
                              "heading": black >= max(1, len(row) // 2) and max_size >= 13.0,
                              "bold": sum("Bold" in word["fontname"] for word in row) >= max(1, len(row) // 2)})

    # Strip the Gmail envelope before the first document heading.
    start = next((i for i, line in enumerate(lines) if line["heading"]), 0)
    lines = lines[start:]
    blocks: list[dict[str, str]] = []
    current: list[str] = []
    current_type = "p"
    previous: dict[str, object] | None = None

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append({"type": current_type, "text": clean(" ".join(current))})
            current = []

    for line in lines:
        text = str(line["text"])
        if re.fullmatch(r"(?i)modul(?:e)?\s*\d+", text):
            flush()
            blocks.append({"type": "marker", "text": text})
            previous = line
            continue
        metadata_labels = (
            "Standard", "Architecture", "Category", "Subcategory", "Governed Space", "Primary Governed Object",
            "Standard Type", "Module", "Parent Standard", "Module Type", "Canonical Language", "Protection",
            "Current Position", "Governance Flow", "Operational Position", "Official Status",
        )
        is_metadata = any(text.startswith(f"{label}:") for label in metadata_labels)
        line_type = "h" if line["heading"] else "meta" if is_metadata else "p"
        if current:
            same_page = previous is not None and previous["page"] == line["page"]
            gap = float(line["top"]) - float(previous["top"]) if same_page else 99.0
            join = line_type == current_type and same_page and (
                (line_type == "h" and gap < 35) or (line_type == "p" and gap < 16)
            )
            if not join:
                flush()
        current_type = line_type
        current.append(text)
        previous = line
    flush()
    return blocks


def render_blocks(blocks: list[dict[str, str]]) -> str:
    rendered: list[str] = []
    for block in blocks:
        text = html.escape(block["text"], quote=False)
        if block["type"] == "marker":
            continue
        if block["type"] == "h":
            rendered.append(f"<h1>{text}</h1>")
        elif block["type"] == "meta":
            value = re.sub(r"^([^:]+):", r"<b>\1:</b>", text)
            rendered.append(f'<p class="podstand">{value}</p>')
        else:
            rendered.append(f"<p>{text}</p>")
    return "\n".join(rendered)


def page(title: str, body: str, related: str = "") -> str:
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} | OOF®</title>
<link rel="stylesheet" href="../../style.css">
</head>
<body>
<div id="header"></div>
<main><article class="container">
<!-- OOF SEMANTIC CONTENT START -->
<section class="container"><div class="oof-warning3">
{body}
{related}
</div><section class="viewbor"></section></section>
<!-- OOF SEMANTIC CONTENT END -->
<a class="back-btn" href="javascript:history.back()" aria-label="Go back">←</a>
</article></main>
<div id="footer"></div>
<script src="../../header.js"></script>
<script>
fetch("../../header.html").then(r => r.text()).then(d => {{ document.getElementById("header").innerHTML = d; initHeaderMenu(); }});
fetch("../../footer.html").then(r => r.text()).then(d => {{ document.getElementById("footer").innerHTML = d; }});
</script>
</body>
</html>
'''


def related_links(standard: Standard) -> str:
    links = [f'<a href="pga-{standard.code}-about.html">About {html.escape(standard.title)}</a>']
    links.extend(f'<a href="pga-{standard.code}-{m.code}-{i}.html">{html.escape(m.title)} ({m.code.upper()})</a>'
                 for i, m in enumerate(standard.modules, 1))
    return '<hr><h2>Governed Links</h2><p>' + '<br>\n'.join(links) + '</p>'


def architecture_links() -> str:
    links = [f'<a href="pga-{s.code}.html">{html.escape(s.title)}</a>' for s in STANDARDS]
    return '<hr><h2>PGA™ Parent Standards</h2><p>' + '<br>\n'.join(links) + '</p>'


def split_standard(blocks: list[dict[str, str]], standard: Standard) -> tuple[list[dict], list[dict], list[list[dict]]]:
    markers = [i for i, block in enumerate(blocks) if block["type"] == "marker"]
    if len(markers) != 5:
        raise ValueError(f"{standard.code.upper()}: expected 5 module markers, found {len(markers)}")
    module_parts = [blocks[markers[i] + 1: markers[i + 1] if i < 4 else len(blocks)] for i in range(5)]
    pre_modules = blocks[:markers[0]]
    first_title = next(block["text"] for block in pre_modules if block["type"] == "h")
    duplicates = [i for i, block in enumerate(pre_modules) if block["type"] == "h" and block["text"] == first_title]
    about_at = duplicates[1] if len(duplicates) > 1 else next(
        (i for i, block in enumerate(pre_modules) if block["type"] == "h" and block["text"].lower().startswith("about ")), -1)
    if about_at < 1:
        raise ValueError(f"{standard.code.upper()}: could not locate the About-standard section")
    return pre_modules[:about_at], pre_modules[about_at:], module_parts


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, title, source in ARCHITECTURE_DOCS:
        blocks = extract_blocks(DOWNLOADS / source)
        target = OUT / filename
        target.write_text(page(title, render_blocks(blocks), architecture_links()), encoding="utf-8")
        written.append(target)

    for standard in STANDARDS:
        blocks = extract_blocks(DOWNLOADS / standard.filename)
        parent, about, modules = split_standard(blocks, standard)
        outputs = [
            (OUT / f"pga-{standard.code}.html", standard.title, parent, related_links(standard)),
            (OUT / f"pga-{standard.code}-about.html", f"About {standard.title}", about, related_links(standard)),
        ]
        outputs.extend((OUT / f"pga-{standard.code}-{module.code}-{i}.html", module.title, content, "")
                       for i, (module, content) in enumerate(zip(standard.modules, modules), 1))
        for target, title, content, related in outputs:
            target.write_text(page(title, render_blocks(content), related), encoding="utf-8")
            written.append(target)

    print(f"Wrote {len(written)} PGA pages to {OUT}")


if __name__ == "__main__":
    main()
