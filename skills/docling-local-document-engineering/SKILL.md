---
name: docling-local-document-engineering
description: "Use when reading, analyzing, extracting, converting, OCRing, or building a reusable local corpus from PDF documents, especially scans, tables, figures, multi-column layouts, or long technical manuals."
---

# Docling Local Document Engineering

## Overview

Choose the lightest local PDF path that preserves structure and traceability. Treat extracted text
as a locator and the hash-matched original page as final evidence.

## Workflow

1. Preserve the original PDF. Establish the task, page count, native-text quality, scan coverage,
   layout complexity, and whether outputs are one-off or reusable.
2. Read [adaptive-pdf-workflow.md](references/adaptive-pdf-workflow.md) before extracting or
   converting content.
3. Use direct native-text extraction for simple short documents when it is more faithful. Use local
   Docling for scans, tables, figures, multi-column layouts, mixed pages, or long documents.
4. Keep physical-page provenance. For critical facts, render and inspect the original page and any
   adjacent page carrying the same table, figure, footnote, or section.
5. For a durable multi-document knowledge base, also read
   [reusable-corpus.md](references/reusable-corpus.md) before designing or publishing derived data.
6. Report the extraction route, verification performed, and any OCR, layout, version, or source-hash
   uncertainty.

**REQUIRED SUB-SKILL:** Use `pdf:pdf` for original-page rendering and visual inspection, AcroForms,
PDF creation or editing, and final layout QA. Docling does not replace those workflows.

## Quick Reference

| Document or task | Route |
| --- | --- |
| Short, simple, native text | Direct extraction plus relevant-page rendering |
| Scan or mixed text/bitmap | Docling with OCR; use full-page OCR only when needed |
| Tables, figures, multi-column layout | Docling Markdown + JSON + referenced images |
| Long manual or batch collection | Resumable page-traceable corpus workflow |
| Form, signature, edit, or PDF authoring | `pdf:pdf` |

## Non-Negotiables

- Never claim Docling or OCR is uniformly more accurate than native extraction.
- Never cite generated Markdown alone for critical numbers, tables, diagrams, or ambiguous text.
- Never publish a reusable corpus after page-count, hash, conversion, or asset validation fails.
- Never silently fall back from configured GPU execution to CPU for a large conversion.

## Common Mistakes

- Running full OCR over clean embedded text and introducing character errors.
- Losing physical page numbers when splitting, chunking, or indexing output.
- Keeping one-off artifacts as an undocumented corpus with no source hashes.
- Treating successful conversion as proof that tables, figures, and footnotes are correct.
