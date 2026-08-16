# Reusable Local Document Corpus

Use this pattern only when future tasks need repeated search across long or multiple documents. A
one-off PDF question does not need a database.

## Durable Data Contract

For every source, record a stable document ID, absolute source path, source hash, byte size, physical
page count, document version, conversion configuration, tool versions, and one entry per physical
page. Store derived data outside Git unless the user explicitly chooses otherwise.

Each page record must retain its physical page number and path to extracted content. Chunks and
search hits must point back to that page record rather than inventing a second page numbering system.

## Resumable Publication

1. Convert large documents in bounded batches with completion markers bound to the source hash and
   conversion settings.
2. Resume only a batch whose marker, page files, and assets validate; otherwise rebuild it.
3. Assemble new output under a staging directory.
4. Validate expected page coverage, UTF-8, non-empty content, image references, manifest consistency,
   and source hashes.
5. Publish with an atomic directory or database replacement. Preserve the last healthy corpus if
   conversion, disk, or validation fails.
6. Rebuild the local SQLite FTS index from the published corpus and run integrity, count, isolation,
   and retrieval-quality checks.

Never silently accept partial OCR, missing pages, escaping image paths, stale source hashes, or an
index built from staging data.

## Proven Local Implementation

The `esp-hardware-knowledge` repository is a tested reference implementation of this pattern. Its
`espdocs` CLI provides SHA-256 incremental ingest, resumable Docling conversion, physical-page
Markdown, referenced images, atomic corpus/index publication, SQLite FTS5 retrieval, `doctor`,
`verify`, golden cases, and original-PDF rendering.

```powershell
uv run espdocs doctor --json
uv run espdocs verify --json
```

Reuse its reliability mechanisms when building another durable corpus, but do not make unrelated
documents adopt ESP32 chip filters, document types, paths, or the `espdocs` command surface. Extract
the generic pattern or extend the repository deliberately when the new collection warrants it.

## Evidence and Recovery

Search results and generated Markdown locate candidates. Critical claims still require a matching
source hash and original PDF page review. A source change invalidates its derived pages and index
entries. Keep backups for intentional migrations, and make recovery restore corpus, assets, manifest,
and index as one consistent unit.
