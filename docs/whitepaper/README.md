# PDF edition

`PlaceAuth-SPP-White-Paper.pdf` is the print-ready edition of the canonical Markdown whitepaper at [`../whitepaper.md`](../whitepaper.md). The Markdown document remains the content source of truth.

## Regenerate

From the repository root, run:

```sh
python docs/whitepaper/source/render_whitepaper.py
```

The renderer needs Python 3.11 or newer, Google Chrome or Chromium, and the `pypdf` and `reportlab` Python packages. It creates a temporary styled HTML intermediate, renders a selectable-text PDF with Chrome, then adds the running header, footer, page numbers, and PDF metadata.

## Source files

- `source/render_whitepaper.py` — Markdown-to-HTML and PDF rendering pipeline.
- `source/whitepaper.css` — print layout, typography, diagrams, tables, and callouts.
- `../whitepaper.md` — canonical whitepaper content.
