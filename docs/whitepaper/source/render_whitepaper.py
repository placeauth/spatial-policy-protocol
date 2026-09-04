"""Render the canonical PlaceAuth white paper as a print-ready PDF.

The Markdown paper remains the source of truth. This renderer creates a styled
HTML intermediate, prints it through locally installed Chrome/Chromium, then
adds the running header, footer, page numbers, and PDF metadata.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[3]
MARKDOWN = ROOT / "docs" / "whitepaper.md"
OUTPUT_DIR = ROOT / "docs" / "whitepaper"
CSS_PATH = Path(__file__).with_name("whitepaper.css")
HTML_PATH = OUTPUT_DIR / ".whitepaper.html"
DEFAULT_PDF = OUTPUT_DIR / "PlaceAuth-SPP-White-Paper.pdf"

SECTION_RE = re.compile(r"^## (\d+)\. (.+)$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def inline(value: str) -> str:
    """Render the limited Markdown inline syntax used by the canonical paper."""
    escaped = html.escape(value)
    escaped = LINK_RE.sub(r'<a href="\2">\1</a>', escaped)
    escaped = CODE_RE.sub(r"<code>\1</code>", escaped)
    return BOLD_RE.sub(r"<strong>\1</strong>", escaped)


def diagram(caption: str, labels: list[str]) -> str:
    nodes: list[str] = []
    for index, label in enumerate(labels):
        label_html = html.escape(label).replace("\n", "<br>")
        nodes.append(f'<div class="diagram-box">{label_html}</div>')
        if index < len(labels) - 1:
            nodes.append('<div class="diagram-arrow" aria-hidden="true"></div>')
    return f'<figure class="diagram"><figcaption>{caption}</figcaption>{"".join(nodes)}</figure>'


def transition_diagram() -> str:
    return """
<figure class="diagram transition-diagram">
  <figcaption>Selective requalification across a spatial transition</figcaption>
  <div class="transition-inputs">
    <div class="diagram-box">Existing evidence</div>
    <div class="diagram-plus">+</div>
    <div class="diagram-box">Destination requirements</div>
  </div>
  <div class="diagram-arrow" aria-hidden="true"></div>
  <div class="diagram-box wide">Requirement delta</div>
  <div class="diagram-arrow" aria-hidden="true"></div>
  <div class="transition-output">
    <div class="diagram-box">Reuse still-sufficient evidence</div>
    <div class="diagram-plus">+</div>
    <div class="diagram-box">Requalify new, stricter, or unresolved requirements</div>
  </div>
  <div class="diagram-arrow" aria-hidden="true"></div>
  <div class="diagram-box wide">Updated operating profile</div>
</figure>
"""


def profile_table() -> str:
    return """
<table class="concept-table"><caption>Admission profile outcomes</caption>
<thead><tr><th>Profile</th><th>Meaning</th></tr></thead><tbody>
<tr><td><strong>ADMITTED</strong></td><td>Required guarantees have been demonstrated within the evaluated scope.</td></tr>
<tr><td><strong>DEGRADED</strong></td><td>Operation may continue only with explicit, enforceable restrictions.</td></tr>
<tr><td><strong>DENIED</strong></td><td>The requested operation must not proceed under the evaluated conditions.</td></tr>
</tbody></table>
"""


def architecture_table() -> str:
    return """
<table class="concept-table"><caption>SPP protocol surfaces</caption>
<thead><tr><th>Surface</th><th>Role</th></tr></thead><tbody>
<tr><td><strong>SPP Core</strong></td><td>Place-facing policy and decision contract.</td></tr>
<tr><td><strong>SPP Conformance</strong></td><td>Requirement-to-proof mapping and deterministic plan.</td></tr>
<tr><td><strong>SPP Admission</strong></td><td>Evidence verification and spatially scoped operating profile.</td></tr>
</tbody></table>
"""


def insertion_for(section: int) -> str:
    insertions = {
        1: diagram("Core lifecycle", ["Place requirements", "Conformance plan", "Evidence", "Admission profile", "Physical operation"]),
        4: '<aside class="callout">The place defines the requirements.<br>The machine demonstrates conformance.<br>SPP establishes the operating profile.</aside>',
        8: diagram("Evidence flow", ["Place requirement", "Conformance result", "Evidence bundle\n(binding, digest, freshness, assurance)", "Admission profile"]),
        9: profile_table(),
        10: diagram("Degraded operation", ["Cannot prove zero retention", "Disable video capture", "Continue only with permitted non-video operations", "DEGRADED profile\n(restriction recorded)"]),
        12: transition_diagram(),
        13: architecture_table(),
        15: '<aside class="callout caution">SPP does not itself force a malicious autonomous system to comply.</aside>',
    }
    return insertions.get(section, "")


def section_entries(markdown: str) -> list[tuple[str, str]]:
    """Return a bookmark label and an extracted-text marker for each section."""
    return [
        (f"{match.group(1)}. {match.group(2)}", f"{match.group(1)} {match.group(2)}")
        for line in markdown.splitlines()
        if (match := SECTION_RE.match(line))
    ]


def render_body(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """Render sections 1-20 and return their TOC entries."""
    lines = markdown.splitlines()
    start = next(index for index, line in enumerate(lines) if SECTION_RE.match(line))
    lines = lines[start:]
    parts: list[str] = []
    toc: list[tuple[str, str]] = []
    index = 0
    section_open = False
    while index < len(lines):
        line = lines[index]
        heading = SECTION_RE.match(line)
        if heading:
            number, title = heading.groups()
            anchor = f"section-{number}-{slug(title)}"
            toc.append((f"{number}. {title}", anchor))
            if section_open:
                parts.append("</section>")
            parts.append(f'<section id="{anchor}"><h2><span>{number}</span>{inline(title)}</h2>{insertion_for(int(number))}')
            section_open = True
            index += 1
            continue
        if line.startswith("```"):
            language = line[3:].strip()
            code: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            parts.append(f'<pre class="code-block {html.escape(language)}"><code>{html.escape(chr(10).join(code))}</code></pre>')
            index += 1
            continue
        if line.startswith("- "):
            items: list[str] = []
            while index < len(lines) and lines[index].startswith("- "):
                items.append(f"<li>{inline(lines[index][2:])}</li>")
                index += 1
            parts.append("<ul>" + "".join(items) + "</ul>")
            continue
        if line.startswith("> "):
            quote: list[str] = []
            while index < len(lines) and lines[index].startswith("> "):
                quote.append(lines[index][2:])
                index += 1
            parts.append(f'<blockquote>{inline(" ".join(quote))}</blockquote>')
            continue
        if not line.strip():
            index += 1
            continue
        paragraph = [line]
        index += 1
        while index < len(lines):
            candidate = lines[index]
            if not candidate.strip() or SECTION_RE.match(candidate) or candidate.startswith(("```", "- ", "> ")):
                break
            paragraph.append(candidate)
            index += 1
        parts.append(f'<p>{inline(" ".join(paragraph))}</p>')
    if section_open:
        parts.append("</section>")
    return "\n".join(parts), toc


def toc_html(entries: list[tuple[str, str]]) -> str:
    rows = "".join(f'<li><a href="#{anchor}">{html.escape(label)}</a></li>' for label, anchor in entries)
    return f'<section class="toc-page"><div class="kicker">Publication guide</div><h1>Contents</h1><ol>{rows}</ol></section>'


def render_html(markdown: str) -> str:
    body, toc = render_body(markdown)
    css = CSS_PATH.read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="author" content="PlaceAuth">
<meta name="description" content="An Open Interoperability Model for Autonomous Systems in Physical Environments">
<title>From Permission to Admission | PlaceAuth</title><style>{css}</style></head><body><main>
<section class="title-page"><div class="title-rule"></div><div class="brand">PlaceAuth</div><div class="tagline">A common language for machines and places.</div>
<div class="title-content"><div class="kicker">White paper</div><h1>From Permission<br>to Admission</h1><p class="subtitle">An Open Interoperability Model for Autonomous Systems in Physical Environments</p></div>
<div class="title-meta"><div>Revision 0.1&nbsp;&nbsp;|&nbsp;&nbsp;September 2026</div><div>SPP 0.1.0 Experimental Preview</div><div>Experimental / Pre-standardization</div><div>placeauth.org</div></div>
<p class="patent">Certain technologies described by PlaceAuth are patent pending.</p></section>
<section class="publication-page"><div class="kicker">Publication information</div><h1>PlaceAuth / SPP</h1><table class="publication-table"><tbody>
<tr><th>Project</th><td>PlaceAuth</td></tr><tr><th>Protocol</th><td>Spatial Policy Protocol (SPP)</td></tr><tr><th>Current release</th><td>SPP 0.1.0 Experimental Preview</td></tr>
<tr><th>Repository</th><td><a href="https://github.com/placeauth/spatial-policy-protocol">github.com/placeauth/spatial-policy-protocol</a></td></tr><tr><th>Website</th><td><a href="https://placeauth.org/">placeauth.org</a></td></tr>
<tr><th>General</th><td><a href="mailto:hello@placeauth.org">hello@placeauth.org</a></td></tr><tr><th>Standards &amp; interoperability</th><td><a href="mailto:standards@placeauth.org">standards@placeauth.org</a></td></tr><tr><th>Security</th><td><a href="mailto:security@placeauth.org">security@placeauth.org</a></td></tr>
<tr><th>License</th><td>Apache License 2.0</td></tr><tr><th>Status</th><td>Experimental / Pre-standardization</td></tr></tbody></table>
<aside class="status-note">This publication describes an experimental reference implementation and protocol family. It is not a certification, production security system, or adopted standard.</aside></section>
{toc_html(toc)}<article class="paper">{body}</article></main></body></html>"""


def find_chrome() -> str:
    candidates = [shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser"), r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe", r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError("Chrome or Chromium is required to render the PDF.")


def header_footer_overlay(page_number: int, page_width: float, page_height: float) -> PdfReader:
    stream = BytesIO()
    page = canvas.Canvas(stream, pagesize=(page_width, page_height))
    page.setStrokeColor(HexColor("#B7C7D3")); page.setLineWidth(0.4)
    page.line(48, page_height - 36, page_width - 48, page_height - 36); page.line(48, 30, page_width - 48, 30)
    page.setFillColor(HexColor("#38536D")); page.setFont("Helvetica-Bold", 8); page.drawString(48, page_height - 28, "PlaceAuth  |  Spatial Policy Protocol")
    page.setFont("Helvetica", 8); page.drawString(48, 18, "From Permission to Admission  |  Revision 0.1"); page.drawRightString(page_width - 48, 18, str(page_number))
    page.save(); stream.seek(0)
    return PdfReader(stream)


def add_pdf_finish(chrome_pdf: Path, output_pdf: Path, bookmarks: list[tuple[str, str]]) -> None:
    reader = PdfReader(chrome_pdf); writer = PdfWriter(); writer.clone_document_from_reader(reader)
    for index, page in enumerate(writer.pages):
        if index >= 2:
            overlay = header_footer_overlay(index + 1, float(page.mediabox.width), float(page.mediabox.height))
            page.merge_page(overlay.pages[0])
    page_text = [page.extract_text() or "" for page in reader.pages]
    for label, marker in bookmarks:
        page_number = next((index for index, text in enumerate(page_text[3:], start=3) if marker in text), None)
        if page_number is None:
            raise RuntimeError(f"Could not create a bookmark for {label}.")
        writer.add_outline_item(label, page_number)
    writer.add_metadata({"/Title": "From Permission to Admission", "/Author": "PlaceAuth", "/Subject": "Spatial Policy Protocol", "/Keywords": "PlaceAuth, SPP, robotics, autonomous systems, interoperability, spatial policy, conformance, evidence, admission", "/Creator": "PlaceAuth white paper renderer"})
    with output_pdf.open("wb") as destination:
        writer.write(destination)
    final = PdfReader(output_pdf)
    extracted = "\n".join(page.extract_text() or "" for page in final.pages)
    if "From Permission to Admission" not in extracted or "ADMITTED" not in extracted:
        raise RuntimeError("PDF text validation failed.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path, default=DEFAULT_PDF); args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    markdown = MARKDOWN.read_text(encoding="utf-8")
    HTML_PATH.write_text(render_html(markdown), encoding="utf-8")
    temporary_pdf = OUTPUT_DIR / ".whitepaper-chrome.pdf"
    command = [find_chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--generate-pdf-document-outline", "--export-tagged-pdf", f"--print-to-pdf={temporary_pdf.resolve()}", HTML_PATH.resolve().as_uri()]
    subprocess.run(command, check=True)
    add_pdf_finish(temporary_pdf, args.output, section_entries(markdown))
    temporary_pdf.unlink(missing_ok=True)
    HTML_PATH.unlink(missing_ok=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
