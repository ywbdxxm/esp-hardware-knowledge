# ESP-IDF Local Docs and Docling Skills Design

## Goal

Extend the Codex integration with two reusable capabilities:

1. Make the installed ESP-IDF documentation source at
   `C:\esp\v6.0.2\esp-idf\docs` an authoritative, version-bound source for ESP32 work.
2. Add a general Codex Skill that routes PDF reading and research through an adaptive Docling
   workflow while retaining original-page visual verification.

The versioned repository must contain every portable Skill, rule, test, and deployment instruction
needed on another Windows machine. Source PDFs, generated corpora, indexes, model caches, renders,
and machine-specific secrets remain local and outside Git.

## Scope

This change updates the existing `esp32-ai-hardware-engineering` Skill, adds one new Codex-only
Skill, updates the canonical global instructions, tests the assets, deploys them under
`%USERPROFILE%\.codex`, and pushes the portable result to the existing GitHub repository.

It does not ingest ESP-IDF RST sources into the ESPDocs PDF index, build the Sphinx documentation,
duplicate the installed ESP-IDF tree, or add adapters for Claude Code, OpenCode, or Hermes.

## ESP-IDF Documentation Source

### Source Resolution

For an ESP-IDF task, Codex must establish the project IDF version and `IDF_TARGET` before using
version-sensitive documentation. It resolves the documentation root in this order:

1. The active project's confirmed ESP-IDF root.
2. `$env:IDF_PATH`, when set and consistent with the project.
3. This machine's known fallback `C:\esp\v6.0.2\esp-idf`.

The selected tree must be identified with Git metadata or equivalent version evidence. The known
fallback is currently tag `v6.0.2`, commit `7101770dc6db2667b3c477cc31365dd1acd6db4e`.
Codex must report a mismatch rather than silently using v6.0.2 documentation for another version.
An unavailable version-matched local tree may be replaced by the matching official rendered
Espressif documentation, with the external source and version stated explicitly.

### Reading RST Correctly

The local documentation is authoritative source material, not fully rendered output. It contains
Sphinx `only::` conditions, chip-specific `.inc` files, substitutions such as
`{IDF_TARGET_PATH_NAME}`, and `include-build-file` references generated from Doxygen. Therefore:

- Search the English and Chinese sources with `rg`, preferring English when translations differ.
- Apply `IDF_TARGET` and SoC capability conditions before treating a passage as applicable.
- Follow referenced `.inc` files and adjacent sections.
- For generated API declarations, verify the matching component header and implementation in the
  same ESP-IDF tree.
- For Kconfig symbols, inspect the matching Kconfig source and the project's resolved configuration.

### Evidence Ownership

Use version-matched ESP-IDF documentation and source for APIs, component behavior, Kconfig, build
system behavior, migration notes, and examples. Use the exact-chip datasheet, TRM, hardware design
guidelines, errata, and original PDF pages for registers, addresses, bit fields, pins, boot straps,
electrical limits, timing, RF, and hardware safety. When sources overlap or disagree, report the
discrepancy and prefer the source that owns the fact instead of merging claims silently.

The existing `esp32-ai-hardware-engineering` Skill gains a direct reference named
`references/esp-idf-local-docs.md`. Its main workflow and quick-reference table route ESP-IDF API,
configuration, build, and migration questions to that reference while preserving the existing
ESPDocs PDF evidence flow.

## Adaptive Docling Skill

### Skill Boundary

Create `docling-local-document-engineering`. It triggers for PDF reading, analysis, extraction,
conversion, OCR, tables, figures, long technical manuals, scanned documents, batch corpora, and
page-traceable local retrieval.

It complements the bundled `pdf:pdf` Skill:

| Need | Primary capability |
| --- | --- |
| Content understanding and structural extraction | `docling-local-document-engineering` |
| OCR, tables, figures, multi-column layout, batch corpus | `docling-local-document-engineering` |
| Original-page rendering and visual inspection | `pdf:pdf` |
| AcroForms, PDF editing, creation, and layout QA | `pdf:pdf` |

All PDF research may enter through the Docling Skill, but not every PDF must run full OCR. The
Skill first classifies the document and task, then selects the lightest path that preserves
accuracy.

### Adaptive Flow

1. Preserve the original file and record its absolute path, size, page count, and SHA-256 when the
   task creates reusable derived data.
2. Inspect whether the PDF has usable native text, scanned pages, complex tables, figures,
   multi-column layout, or a large page count.
3. For a short native-text PDF with simple structure, use direct text extraction and render the
   relevant original pages. Full Docling conversion is optional.
4. For scanned, mixed, table-heavy, figure-heavy, multi-column, or long documents, run local
   Docling conversion with OCR and required structural outputs.
5. For one-off work, keep outputs in a task-local temporary directory and remove intermediates
   after verification. For a reusable collection, use a manifest, stable source hashes, physical
   page mapping, resumable batches, staging validation, atomic publication, and a local index.
6. Treat generated Markdown and search results as locators. Verify critical evidence against the
   hash-matched original PDF page and inspect adjacent pages when context crosses a boundary.

Docling must not be described as uniformly more accurate than native extraction. Native text can
preserve exact characters better; OCR and layout analysis can introduce errors. Docling is the
preferred structural parser when layout or scans make direct extraction incomplete.

### Reusable Corpus Pattern

The Skill documents two levels of use:

- `docling convert` for a local one-off conversion.
- The `esp-hardware-knowledge` repository as the proven implementation pattern for large,
  resumable, page-traceable corpora with Docling, OCR, SQLite FTS, health checks, evaluation, and
  original-PDF fallback.

The generic Skill does not hard-code ESP32 document types or require the `espdocs` CLI for unrelated
PDFs. It points to the repository when a future task needs to build a durable corpus rather than
reimplementing the reliability mechanisms from scratch.

### Failure Behavior

- If Docling is unavailable, report that condition and fall back to direct extraction plus rendered
  original-page inspection when possible.
- If OCR, conversion, page counts, source hashes, image references, or staging validation fail, do
  not publish or trust the derived corpus.
- If the source PDF changes, invalidate or rebuild the corresponding derived data.
- If extraction disagrees with the original page, the original page wins and the discrepancy is
  reported.
- Never silently switch from configured GPU execution to CPU for a large conversion. A deliberate
  one-off CPU fallback must be stated.

## Codex Routing and Portable Deployment

Canonical assets live in this repository:

```text
codex/AGENTS.md
skills/esp32-ai-hardware-engineering/
skills/docling-local-document-engineering/
```

The global `AGENTS.md` retains mandatory ESP32 routing and adds adaptive PDF research routing. The
new PDF rule must not force Docling for unrelated PDF creation or form editing; those remain under
`pdf:pdf`.

Deployment copies canonical Skill directories to `%USERPROFILE%\.codex\skills` and the canonical
instructions to `%USERPROFILE%\.codex\AGENTS.md`. Documentation must use environment variables and
discovery rules for portable locations. The known `C:\esp\v6.0.2` path is a documented fallback,
not the only valid installation path.

The repository contains setup and validation guidance for another machine, including uv-managed
Docling installation, optional GPU prerequisites, Skill deployment, and environment-variable
configuration. It does not commit installed virtual environments, model weights, PDFs, SQLite
databases, generated Markdown, or page renders.

## Testing and Acceptance

Add failing asset tests before changing either Skill. Tests must assert:

- The ESP32 Skill routes version-sensitive ESP-IDF questions to the new reference.
- The reference resolves a version-matched IDF root, requires `IDF_TARGET`, understands RST
  conditions and Doxygen includes, and rejects silent version mismatch.
- The Docling Skill metadata triggers on the intended PDF research cases.
- The adaptive workflow distinguishes native-text fast paths from full Docling conversion.
- Original-PDF fallback, SHA-256 traceability, physical page mapping, and adjacent-page checks are
  explicit.
- The new Skill delegates forms, editing, creation, rendering, and visual QA to `pdf:pdf`.
- Canonical and deployed assets match.

Run the Codex Skill validator for both Skills, targeted asset tests, Ruff, the complete pytest suite,
`espdocs doctor --json`, and `espdocs verify --json`. Confirm Git tracks no runtime document data.
Commit the implementation to `main` and push it to `origin/main` only after all gates pass.

