#!/usr/bin/env python3
"""Import the supplied EGA and enforcement-reference Gmail PDF exports."""
from __future__ import annotations

import argparse
import html
import re
import shutil
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STANDARDS = [
    ("ESOS", "Energy Source & Origin Standard", "*EGA 1Energy Source*.pdf"),
    ("EGS", "Energy Generation Standard", "*2 EGS*Energy Generation*.pdf"),
    ("ECS", "Energy Conversion Standard", "*3Energy Conversion*.pdf"),
    ("ETDS", "Energy Transmission & Distribution Standard", "*4Energy Transmission*.pdf"),
    ("ESS", "Energy Storage Standard", "*5Energy Storage*.pdf"),
    ("EDCS", "Energy Delivery & Consumption Standard", "*6Energy Delivery*.pdf"),
    ("ESBS", "Energy System Balancing Standard", "*7Energy System Balancing*.pdf"),
    ("EMRS", "Energy Measurement & Reconciliation Standard", "*8Energy Measurement*.pdf"),
    ("EFAS", "Energy Flow Attribution Standard", "*9Energy Flow Attribution*.pdf"),
    ("EELS", "Energy Efficiency & Loss Standard", "*10Energy Efficiency*.pdf"),
    ("ESRS", "Energy Supply Reliability Standard", "*11ESRS*.pdf"),
    ("EEIS", "Energy Environmental Impact Standard", "*12EEIS*.pdf"),
    ("ECDS", "Energy Claims & Disclosure Standard", "*ECDS*Energy Claims*.pdf"),
]


def find(downloads: Path, pattern: str) -> Path:
    matches = list(downloads.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"Expected one PDF for {pattern}, found {len(matches)}")
    return matches[0]


def extracted_pages(path: Path) -> list[list[str]]:
    pages = []
    for page in PdfReader(path).pages:
        lines = (page.extract_text() or "").splitlines()
        lines = [line.strip() for line in lines if line.strip()]
        lines = [line for line in lines if not re.match(r"^\d{2}/\d{2}/\d{4},\s*\d{1,2}:\d{2}\s+Gmail\s*-", line)
                 and not line.startswith("https://mail.google.com/")]
        pages.append(lines)
    if not pages or not any(pages):
        raise ValueError(f"No extractable text in {path.name}")
    # Gmail's To: line closes the forwarded-message envelope. It is private
    # correspondence, not part of the supplied reference text.
    for i, line in enumerate(pages[0]):
        if line.startswith("To:"):
            pages[0] = pages[0][i + 1:]
            break
    while pages[0] and ("@" in pages[0][0] or pages[0][0].startswith("<")):
        pages[0].pop(0)
    return pages


def shell(title: str, body: str, description: str) -> str:
    e = html.escape
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | OOF®</title><meta name="description" content="{e(description, quote=True)}">
<link rel="stylesheet" href="../../style.css"><style>.ega-source p{{margin:.3rem 0;overflow-wrap:anywhere}}.ega-source h2{{margin-top:1.4rem;overflow-wrap:anywhere}}</style></head>
<body class="oof-info-page"><div id="header"></div><main class="oof-semantic-main">
<!-- OOF SEMANTIC CONTENT START -->
<article class="oof-semantic-article">{body}</article>
<!-- OOF SEMANTIC CONTENT END -->
</main><div id="footer"></div><script src="../../header.js"></script>
<script>fetch('../../header.html').then(r=>r.text()).then(d=>{{document.getElementById('header').innerHTML=d;initHeaderMenu();}});fetch('../../footer.html').then(r=>r.text()).then(d=>document.getElementById('footer').innerHTML=d);</script></body></html>\n'''


def document(title: str, pages: list[list[str]], *, visual: str = "", links: str = "") -> tuple[str, list[tuple[str, str]]]:
    modules = []
    flat = [line for page in pages for line in page]
    labels = {}
    for i, line in enumerate(flat):
        match = re.search(r"^Module ID:\s*EGA-[A-Z]+-([A-Z]+)-\d+", line)
        if match and i > 0 and 'Module' in flat[i - 1] and len(flat[i - 1]) < 120:
            labels.setdefault(match.group(1), flat[i - 1])
        if re.fullmatch(r"(?:Modul|Module)\s*\d+", line, re.I):
            following = flat[i + 1:i + 8]
            for j, item in enumerate(following):
                if item.startswith('Architecture:'):
                    heading = ' '.join(following[:j])
                    code_match = re.search(r"^([A-Z]{3,8})\s*[—–:-]|\(([A-Z]{3,8})\)", heading)
                    if code_match:
                        code = code_match.group(1) or code_match.group(2)
                        labels[code] = heading
                    break
    body = [f'<section class="container"><div class="oof-warning3"><h1>{html.escape(title)}</h1>', links]
    if visual:
        body.append(visual)
    previous = []
    for page_no, lines in enumerate(pages, 1):
        body.append(f'<div id="source-page-{page_no}" class="ega-source">')
        for idx, line in enumerate(lines):
            module_id = re.search(r"^Module ID:\s*EGA-[A-Z]+-([A-Z]+)-\d+", line)
            if module_id and any('Type: Core Module' in item for item in previous[-45:]):
                code = module_id.group(1)
                anchor = 'module-' + code.lower()
                if not any(existing == anchor for _, existing in modules):
                    label = labels.get(code, 'Core Module')
                    label = re.sub(r'^\s*(?:Module\s*\d+\s*[—–:-]\s*)?', '', label)
                    if not re.search(r'\b' + re.escape(code) + r'\b', label):
                        label = code + ' — ' + label
                    modules.append((label, anchor))
                    body.append(f'<span id="{anchor}"></span>')
            previous.append(line)
            # Module headers are followed immediately by architecture metadata.
            ahead = " ".join(lines[idx + 1:idx + 9])
            match = re.match(r"^([A-Z][A-Z0-9]{2,8})\s*[—–-]\s*(.{3,100})$", line)
            if match and "Module" in line and "Architecture:" in ahead and "Parent Standard:" in ahead:
                code = match.group(1)
                anchor = "module-" + code.lower()
                if not any(existing == anchor for _, existing in modules):
                    modules.append((line, anchor))
                    body.append(f'<h2 id="{anchor}" data-oof-section-id="true">{html.escape(line)}</h2>')
                    continue
            if re.fullmatch(r"(?:Modul|Module)\s*\d+", line, re.I):
                continue
            if re.match(r"^\d{1,2}\.\s+\S", line) and len(line) < 110:
                body.append(f'<h2>{html.escape(line)}</h2>')
            else:
                body.append(f'<p>{html.escape(line)}</p>')
        body.append('</div>')
    body.append('</div></section>')
    return "\n".join(body), modules


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("downloads", type=Path)
    args = parser.parse_args()
    out = ROOT / "content" / "ega"
    out.mkdir(parents=True, exist_ok=True)
    standard_index = []
    for code, name, pattern in STANDARDS:
        title = f"{name} ({code})"
        body, modules = document(title, extracted_pages(find(args.downloads, pattern)), links='<p><a href="ega-complete-index.html">EGA™ Standards &amp; Modules Index</a></p>')
        filename = f"ega-{code.lower()}.html"
        (out / filename).write_text(shell(title, body, f"EGA™ {title}, including its core modules."), encoding="utf-8", newline="\n")
        standard_index.append((code, name, filename, modules))
        print(f"{code}: {len(modules)} identified module headings")
    items = []
    for code, name, filename, modules in standard_index:
        items.append(f'<h2><a href="{filename}">{html.escape(name)} ({code})</a></h2>')
        if modules:
            items.append('<ul>' + ''.join(f'<li><a href="{filename}#{anchor}">{html.escape(label)}</a></li>' for label, anchor in modules) + '</ul>')
    index = '<section class="container"><div class="oof-warning3"><h1>EGA™ Complete Standards &amp; Modules Index</h1><p><a href="ega-governance-layer.html">EGA™ Energy Governance Architecture</a> · <a href="ega-architecture-map.html">EGA™ Architecture Map</a></p>' + ''.join(items) + '</div></section>'
    (out / 'ega-complete-index.html').write_text(shell('EGA™ Complete Standards & Modules Index', index, 'EGA™ Energy Governance Architecture standards and modules.'), encoding='utf-8', newline='\n')
    for pattern, filename, title in [
        ('*EGA™ Architecture Map.pdf', 'ega-architecture-map.html', 'EGA™ Architecture Map'),
        ('*EGA™ Energy Governance Architecture*.pdf', 'ega-governance-layer.html', 'EGA™ Energy Governance Architecture — Physical Energy Lifecycle Governance Layer'),
    ]:
        body, _ = document(title, extracted_pages(find(args.downloads, pattern)), links='<p><a href="ega-complete-index.html">EGA™ Standards &amp; Modules Index</a></p>')
        (out / filename).write_text(shell(title, body, title), encoding='utf-8', newline='\n')
    image_name = 'oof-authority-enforcement-boundary-reference.png'
    shutil.copy2(args.downloads / 'OOF_Authority_Enforcement_Boundary_Reference_FINAL_v1.0.png', ROOT / 'assets' / 'images' / image_name)
    title = 'About the OOF® Authority Enforcement Boundary Reference'
    visual = f'<figure class="oof-reference-figure"><a href="../../assets/images/{image_name}"><img class="oof-reference-visual" src="../../assets/images/{image_name}" alt="Authority Enforcement Boundary Reference showing the eight-stage authority enforcement flow and execution boundaries" width="1536" height="1024"></a></figure>'
    body, _ = document(title, extracted_pages(find(args.downloads, '*About the OOF® Authority Enforcement Boundary Reference.pdf')), visual=visual)
    (ROOT / 'content' / 'a' / 'oof-authority-enforcement-boundary-reference.html').write_text(shell(title, body, title), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
