# Codex Hardware Document Research Architecture Design

## Goal

Make source-grounded hardware documentation research fast, predictable, and portable for Codex
development work. The primary acceptance criterion is the answer Codex produces while working in a
real project: it must select the exact component and document revision, find concise relevant
evidence, return to the authoritative source when required, and report uncertainty without silently
substituting another device or stale extraction.

The design evolves the working ESPDocs implementation. It does not rename the repository or CLI,
move the existing runtime corpus, or implement every document format at once.

## Current Baseline

The repository already provides strong PDF ingestion and evidence mechanics:

- hash-addressed source records;
- physical PDF page preservation;
- resumable Docling conversion;
- staged validation and atomic corpus/index publication;
- deterministic SQLite FTS5 retrieval;
- original-PDF hash verification and page rendering;
- `doctor`, `verify`, and a 23-case ESP32 retrieval evaluation.

The verified local runtime currently contains 10 documents and 2697 physical pages. The corpus and
index pass their integrity and retrieval gates.

The main architectural problems are at the integration boundaries:

1. The repository's ESP32 Skill is older than the deployed global Skill, while deployment can
   overwrite the newer destination without detecting drift.
2. Skill references contain a personal workspace fallback and require both `doctor` and full
   `verify` before ordinary queries.
3. `doctor.healthy` couples read-only retrieval readiness to CUDA and ingestion readiness.
4. Catalog and retrieval code hard-code ESP32-C3/S3, PDF page fields, filename classifications, and
   document types.
5. The global `AGENTS.md` routes ESP32 and PDF work but has no chip-agnostic hardware research route.
6. Tests validate many implementation details but do not exercise the complete Codex experience
   from an arbitrary project and working directory.
7. A process-level `ESPDOCS_DATA_ROOT` leaks into one configuration test, so the clean baseline is
   currently 88 passing tests and one failure.

## Design Principles

### Codex Experience Comes First

Optimize for the common read-only flow. Ingestion, OCR, index rebuilding, and deployment are
maintenance operations and must not make ordinary lookup slower or unavailable.

For a normal hardware question, Codex should need this sequence:

1. Resolve the exact project component context.
2. Run one lightweight readiness check.
3. Search with explicit component and document filters.
4. Inspect the selected evidence unit.
5. Open the authoritative source only when the evidence policy requires it.
6. Answer with component, document revision, locator, and uncertainty.

### Preserve Proven Mechanics

Keep the `espdocs` command, current corpus, current index, and schema-v1 compatibility until a
replacement has passed the same source, integrity, retrieval, and rollback gates. Generalization is
incremental and additive.

### Separate Routing, Research, Processing, and Storage

- `AGENTS.md` routes tasks and states global evidence invariants.
- Skills contain decision guidance for a task or domain.
- ESPDocs implements deterministic ingestion, retrieval, and source verification.
- Configuration declares machine locations, collections, and document identity.
- Generated corpus, index, render, cache, and log data remain outside Git.

No layer should encode a personal absolute path owned by another layer.

### Fail Closed on Identity, Not on Optional Acceleration

A missing or ambiguous component, document revision, source hash, or locator blocks an authoritative
claim. Missing CUDA blocks GPU-backed ingestion but must not block use of an existing healthy index.

### Progressive Disclosure

Skill entrypoints remain short. They route to references only for document research, Windows SDK
activation, reusable corpus work, or other relevant modes. `AGENTS.md` contains routing rules rather
than duplicated procedures.

## Target Architecture

```text
project context and closest AGENTS.md
                  |
                  v
global AGENTS.md routing
                  |
       +----------+-----------+
       |                      |
       v                      v
hardware-document-       ESP32 engineering
research Skill            Skill
       |                      |
       +----------+-----------+
                  |
                  v
      stable ESPDocs research contract
  doctor / inventory / search / show / source
                  |
       +----------+-----------+
       |                      |
       v                      v
 configured metadata     evidence policy
 and format adapters     and source verification
       |                      |
       +----------+-----------+
                  |
                  v
     corpus / index / original documents
```

### Global Routing

The global managed `AGENTS.md` must be concise and portable:

- Use `esp32-ai-hardware-engineering` for ESP32 and ESP-IDF engineering.
- Use `hardware-document-research` for semiconductor and electronic-component facts grounded in
  datasheets, TRMs, errata, application notes, or design guides.
- Use `docling-local-document-engineering` when extraction, OCR, complex PDF structure, or reusable
  corpus engineering is actually required.
- Use `pdf:pdf` for original-page rendering, visual inspection, PDF creation/editing, and forms.
- Read the closest project `AGENTS.md` and project configuration before selecting component filters.

An ESP32 hardware-document question may activate the ESP32 and hardware research Skills. Their
boundaries are distinct: the ESP32 Skill owns SDK, firmware, concurrency, BSP, and ESP-specific
engineering; the hardware research Skill owns source selection and evidence handling.

### Skill Responsibilities

#### `hardware-document-research`

This new task-centered Skill owns the reusable research behavior for chips and electronic
components. It specifies:

- exact part, variant/package, silicon revision, board context, and document revision resolution;
- local-corpus-first lookup when healthy;
- official-vendor fallback when local evidence is missing;
- no silent substitution of a related part;
- the compact ESPDocs query flow;
- evidence and citation requirements;
- failure behavior for unavailable, ambiguous, changed, or unverified sources.

It does not own firmware architecture, SDK environments, OCR implementation, or PDF authoring.

#### `esp32-ai-hardware-engineering`

Keep this Skill ESP32-specific. Preserve its current Windows ESP-IDF environment, version-matched
local IDF documentation, concurrency, board, audio, protocol, persistence, and verification rules.
Replace personal ESPDocs discovery commands with the stable research launcher. Its local-document
reference becomes a thin ESP32 adapter that requires an exact target and defers the general evidence
flow to `hardware-document-research`.

Before canonical synchronization, the newer deployed ESP32 Skill must be reviewed and imported into
the repository, including `windows-esp-idf-environment.md`. Deployment must never be used to perform
that reconciliation implicitly.

#### `docling-local-document-engineering`

Keep this Skill format/processing-centered. It decides between native extraction and Docling for
PDFs, preserves source and physical-page traceability, and defines reusable-corpus publication
guards. Remove machine claims such as a fixed CUDA device. Runtime discovery chooses and reports the
actual device.

This Skill must not become the universal hardware research Skill and must not force unrelated
documents to adopt ESP32 metadata or the ESPDocs CLI.

#### System Skills

Bundled `pdf:pdf`, `documents:documents`, and other system Skills remain externally managed. The
repository documents how user-maintained Skills route to them but does not copy or modify bundled
Skill files.

### Project Instructions

Add a root `AGENTS.md` to the ESPDocs repository for development rules, tests, generated-data
boundaries, and canonical/deployed asset ownership. Do not use the deployable global instructions as
the repository's project instructions.

Project repositories consuming the research system may declare component context in their closest
`AGENTS.md` or a project research configuration. They do not copy machine paths or the full global
workflow.

## Stable Research Contract

Keep the existing commands and JSON schema-v1 behavior compatible while adding agent-oriented
capabilities:

### `doctor`

Report independent readiness states:

- `query_ready`: configuration, index, schema, and readable source metadata are sufficient for
  lookup;
- `source_ready`: original documents required by indexed records exist;
- `ingest_ready`: parser and selected acceleration are ready for conversion;
- `verify_recommended`: the corpus changed, the index is stale, or no successful verification is
  recorded for the active corpus identity.

The top-level command succeeds when diagnostics execute. Codex uses `query_ready`, not a process exit
code or a single combined `healthy` field, to decide whether local lookup is available.

### `inventory`

Provide a compact, structured list of indexed vendors, families, parts, variants, document types,
languages, revisions, and source counts. Codex uses it to resolve filters instead of guessing an
allowed value.

### `search`

Retain `--chip` for compatibility and add normalized metadata filters. At minimum:

- `--vendor`;
- `--family`;
- `--part`;
- `--variant`;
- `--type`;
- `--language`;
- `--limit`;
- `--compact` for token-efficient agent output.

Allowed filter values come from the active index/configuration rather than Python constants. A
specified filter producing no exact matching document returns a structured no-match result; it does
not broaden the search silently.

### `show`

Return the complete selected evidence unit and its identity fields. For PDF schema-v1 records this
remains one physical page. Output includes stable `source_ref` and `locator` fields while retaining
`page_id` and `pdf_page` during compatibility.

### `source`

Recompute the original source hash and materialize the authoritative locator. For PDFs this renders
the physical page and returns adjacent physical-page locators. A hash mismatch or missing source is
a structured evidence failure.

### `verify`

Remain the full maintenance gate for corpus/index integrity and golden retrieval evaluation. Run it
after ingest, configuration/schema migration, index rebuilding, or suspected corruption. Ordinary
Codex queries do not run it unconditionally.

## Metadata and Configuration

Introduce a versioned configuration schema while continuing to read the current two-entry schema.
Configuration is explicit and portable; filename inference may assist a dry run but cannot silently
publish unidentified documents.

Every indexed document eventually carries:

- stable `document_id` and `source_ref`;
- `vendor`;
- `family`;
- `part`;
- optional `variant`, package, and silicon revision;
- `document_type`;
- document title, revision, publication date, and language when known;
- `source_format` and original path or official URL;
- source hash, byte size, and modification/snapshot time;
- source-specific locator model.

Collection defaults avoid repeating vendor/family/part data for a directory, while per-document
overrides establish exact identity and revision. Paths in versioned configuration are relative to
the configuration file or an explicitly configured source base.

Resolution precedence is:

1. explicit CLI option;
2. process or user environment variable;
3. project-local research configuration discovered from the current project upward;
4. user-level shared-library configuration;
5. documented platform data-directory fallback.

Skills contain none of these absolute paths. A single maintained launcher resolves the ESPDocs
project and invokes its locked environment from any current working directory.

`ESP_HARDWARE_KNOWLEDGE_ROOT` is the sole explicit environment variable for the ESPDocs repository
root. Do not introduce a second repository-root variable. `ESPDOCS_SOURCE_BASE` and
`ESPDOCS_DATA_ROOT` remain the separate source-library and generated-runtime overrides.

## Source and Locator Model

PDF remains the first fully supported format. The general contract must not assume that every source
has pages:

- PDF: physical page plus optional printed label;
- HTML: canonical URL or snapshot plus heading/anchor;
- Markdown/text: file hash plus heading and line/section locator;
- DOCX and other structured formats: source hash plus stable structural path supplied by the format
  adapter.

All search hits point to an evidence unit, and all evidence units point to their original source.
Derived Markdown is always a locator, never the final authority for critical hardware claims.

Only PDF behavior and the generic locator fields are required in the first implementation. Add
another format adapter only with a real source and a format-specific golden evaluation case.

## Evidence Policy

Evidence grading remains independent from retrieval ranking.

The source check is mandatory for:

- absolute maximum, recommended operating, electrical, thermal, RF, and timing values;
- pin assignments, strap/boot behavior, package differences, register definitions, and reset values;
- power sequencing, safety, security, programming, and irreversible operations;
- tables, diagrams, plots, footnotes, OCR warnings, unknown revisions, and source discrepancies.

An answer based on local documents reports the exact part, document title/revision, and physical page
or other authoritative locator. If the exact source is unavailable, Codex reports that limitation and
may use an official vendor source with its provenance stated. It must not answer from a similar part
without explicitly labeling the comparison and obtaining a source for that part.

## Deployment and Ownership

The Git repository is the only canonical source for managed global `AGENTS.md` and user-maintained
Skills. Deployment has three modes:

- check: report source/deployed parity without writes;
- install/update: update only destinations that still match the last deployed manifest;
- force: explicitly replace a locally modified managed destination after presenting the drift.

The installer validates every source Skill before any destination change, stages the complete managed
asset set, writes a hash manifest, and restores the previous complete set on failure. It never deletes
unmanaged Skills.

Repository and deployed parity is a release gate, not a unit-test assumption. A global edit must be
reconciled into the repository before the next deployment.

## Data and Migration

The existing `docs/esp-hardware-knowledge-data` runtime remains in place during this work. No corpus,
index, backup, render, cache, log, or original document is deleted.

Schema/configuration changes use side-by-side staging and rebuild the index from validated corpus
manifests. Publish only after old and new golden evaluations pass and the cross-chip isolation case
passes. Preserve the old index and deployment assets until the new Codex acceptance scenarios pass.

Any later decision to move runtime data is a separate, reversible migration based on measured
portability or organization benefits.

## Evaluation Strategy

### Automated Gates

- isolate all `ESPDOCS_*` variables in configuration tests;
- validate canonical Skill syntax;
- validate global routing and Skill responsibility boundaries;
- exercise the launcher from an unrelated working directory;
- prove query readiness is independent from CUDA ingestion readiness;
- prove inventory and filters are data-driven;
- prove exact-part filtering never leaks another part;
- preserve schema-v1 CLI behavior;
- verify source-hash mismatch and locator errors fail closed;
- retain corpus/index integrity and ESP32 golden recall;
- add at least one non-ESP32 PDF golden case from `docs/PMIC/bq2407x.pdf`.

The BQ2407x case uses the original 53-page PDF. Representative authoritative locators include the
ISET pin definition on physical page 8 and the detailed fast-charge programming discussion on
physical page 25. The exact evaluation query is fixed during implementation after confirming the
new ingestion output and original pages agree.

### Codex Acceptance Scenarios

Run these scenarios from a project other than the ESPDocs repository:

1. An ESP32-C3 register or strap question resolves the correct chip and requires original-page
   verification.
2. An ESP32-S3 SDK API question uses the project-selected ESP-IDF revision rather than a random
   installed revision.
3. A BQ2407x ISET question returns the TI source and never an ESP32 document.
4. An unknown or ambiguous component produces an explicit evidence limitation rather than a guessed
   answer.
5. Existing-index lookup remains available when CUDA is unavailable, while ingestion is reported as
   unavailable.
6. A changed source PDF is rejected until re-ingested.
7. A table or figure answer cites and visually inspects the original physical page.

Measure command count, wall time, and approximate JSON size for the common read-only path. The target
is one readiness call, one search, and no more than one `show` plus one conditional `source` call.

## Delivery Phases

1. Restore a trustworthy baseline and canonical source ownership.
2. Establish the agent-oriented readiness and invocation contract.
3. Generalize configured metadata and prove one non-ESP32 PDF without renaming ESPDocs.
4. Align global/project `AGENTS.md` and all managed Skills around the working contract.
5. Make deployment drift-aware, transactional, and verifiable.
6. Validate real Codex workflows and document operations.
7. Add non-PDF adapters only when backed by real sources and golden cases.

Each phase must leave the existing ESP32 corpus and CLI usable. A phase does not begin by deleting or
moving the output of the previous one.

## Out of Scope for the Initial Implementation

- renaming `espdocs`, the Python package, or the repository;
- moving the 406 MiB runtime tree;
- adding embeddings, a vector database, or a remote RAG service;
- downloading manuals without explicit task scope;
- ingesting every document already present under the workspace `docs` directory;
- implementing DOCX, spreadsheet, presentation, audio, or video adapters without a real research
  requirement and golden case;
- modifying bundled Codex system Skills;
- silently replacing official-source verification with generated Markdown.

## Acceptance Criteria

The architecture is accepted when:

- an arbitrary project can invoke local research without knowing the ESPDocs repository path;
- Codex can discover supported parts and issue an exact, compact query;
- existing healthy indexes remain searchable without Docling or CUDA readiness;
- the ESP32 and BQ2407x scenarios return isolated, traceable evidence;
- critical hardware claims resolve to a hash-matched original PDF page;
- all user-maintained Skills have distinct, documented responsibilities and pass validation;
- global and project `AGENTS.md` files contain routing rather than duplicated procedures;
- repository and deployed managed assets have deliberate, checked parity;
- no existing corpus, index, document, or user modification is lost during migration or deployment.
