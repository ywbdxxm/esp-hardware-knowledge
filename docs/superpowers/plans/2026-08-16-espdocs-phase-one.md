# ESPDocs Phase One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible local ESP32-C3/S3 document ingestion and deterministic retrieval CLI that always traces results to an original PDF page and forces source checks for safety-critical facts.

**Architecture:** A Python 3.13 package managed by uv discovers only configured PDF roots, hashes and converts changed documents with Docling plus RapidOCR, writes page-oriented Markdown and metadata under `%LOCALAPPDATA%`, and atomically builds a SQLite FTS5 trigram index. The `espdocs` CLI exposes stable text/JSON commands for search, context display, source-page rendering, diagnostics, and evaluation; generated data and source PDFs remain outside Git.

**Tech Stack:** Python 3.13, uv, Docling 2.120.1 with RapidOCR, PyMuPDF, SQLite 3.53 FTS5 trigram, Typer, pytest, Ruff.

---

## File Map

```text
.gitignore                         Exclude virtualenvs and all generated runtime data
.python-version                    Pin project interpreter to CPython 3.13
pyproject.toml                     Package metadata, dependencies and tool configuration
uv.lock                            Reproducible dependency lock
README.md                          Setup, commands, evidence rules and runtime locations
config/documents.toml              Allowed source roots and document classification rules
config/aliases.toml                Reviewed Chinese/English ESP terminology aliases
evaluation/golden.jsonl            Source-location retrieval evaluation cases
src/espdocs/__init__.py            Package version
src/espdocs/cli.py                 Typer command boundary and JSON output
src/espdocs/config.py              Repository and runtime path resolution
src/espdocs/models.py              Typed document, page and result records
src/espdocs/catalog.py             PDF discovery, classification, hashing and manifest records
src/espdocs/parser.py              Docling/RapidOCR construction and per-page export
src/espdocs/ingest.py              Staging, quality checks and atomic corpus promotion
src/espdocs/index.py               SQLite schema, FTS5 indexing and capability check
src/espdocs/retrieval.py           Query normalization, aliases, filtering and ranking
src/espdocs/evidence.py            Evidence grade and mandatory source-check policy
src/espdocs/source.py              Source hash validation and PDF page rendering
src/espdocs/evaluate.py            Golden-set recall evaluation
tests/                              Unit, integration and CLI contract tests
```

## Task 1: Bootstrap the uv Package and Runtime Boundary

**Files:**
- Create: `.python-version`
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `src/espdocs/__init__.py`
- Create: `src/espdocs/config.py`
- Create: `tests/test_config.py`

- [x] **Step 1: Write the failing runtime-path test**

```python
from pathlib import Path

from espdocs.config import AppPaths


def test_runtime_data_stays_outside_repository(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    local = tmp_path / "LocalAppData"
    paths = AppPaths.from_roots(repo_root=repo, local_app_data=local)

    assert paths.data_root == local / "esp-hardware-knowledge"
    assert paths.corpus_dir == paths.data_root / "corpus"
    assert paths.index_path == paths.data_root / "index" / "espdocs.sqlite3"
    assert repo not in paths.data_root.parents
```

- [x] **Step 2: Run the focused test and verify the import fails**

Run: `uv run pytest tests/test_config.py -v`

Expected: FAIL because `espdocs.config` does not exist.

- [x] **Step 3: Add project metadata and minimal path implementation**

Use Python 3.13 in `.python-version`. Define the package and tools in `pyproject.toml`:

```toml
[project]
name = "esp-hardware-knowledge"
version = "0.1.0"
description = "Local, source-traceable ESP hardware documentation retrieval"
requires-python = ">=3.13,<3.14"
dependencies = [
  "docling[rapidocr]==2.120.1",
  "pymupdf>=1.26,<2",
  "typer>=0.21,<1",
]

[project.scripts]
espdocs = "espdocs.cli:app"

[dependency-groups]
dev = ["pytest>=9,<10", "ruff>=0.14,<1"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/espdocs"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py313"
```

Ignore `.venv/`, Python caches, coverage files, `*.sqlite3`, `corpus/`, `renders/`, `cache/`, and `logs/`. Implement immutable `AppPaths` with `from_roots`, `discover`, and `ensure_runtime_dirs`; `discover` uses `%LOCALAPPDATA%` and fails with a clear message if it is unavailable.

- [x] **Step 4: Lock dependencies and run the test**

Run: `uv lock && uv sync --dev && uv run pytest tests/test_config.py -v`

Expected: PASS, and `uv.lock` is created.

- [x] **Step 5: Run formatting and commit**

Run: `uv run ruff check . && uv run ruff format --check .`

Expected: both commands exit 0.

Commit:

```powershell
git add .python-version .gitignore pyproject.toml uv.lock src tests
git commit -m "build: bootstrap espdocs uv project"
```

## Task 2: Discover and Classify Only the Approved ESP PDFs

**Files:**
- Create: `config/documents.toml`
- Create: `src/espdocs/models.py`
- Create: `src/espdocs/catalog.py`
- Create: `tests/test_catalog.py`

- [x] **Step 1: Write failing catalog tests**

Tests must prove that discovery is allow-list based, recursive only inside the two configured roots, stable under ordering changes, and records SHA-256 and one-based PDF page counts. Representative assertions:

```python
def test_discovery_excludes_unconfigured_sibling(tmp_path, write_pdf):
    c3 = tmp_path / "ESP32-C3"
    mic = tmp_path / "MIC"
    target = write_pdf(c3 / "esp32-c3_datasheet_cn.pdf", pages=2)
    write_pdf(mic / "unrelated.pdf", pages=1)

    records = discover_documents([SourceRoot(chip="esp32-c3", path=c3)])

    assert [record.source_path for record in records] == [target.resolve()]
    assert records[0].page_count == 2
    assert len(records[0].sha256) == 64
```

- [x] **Step 2: Run tests and confirm failure**

Run: `uv run pytest tests/test_catalog.py -v`

Expected: FAIL because catalog types and discovery functions do not exist.

- [x] **Step 3: Implement typed records and deterministic discovery**

Define frozen dataclasses `SourceRoot`, `DocumentRecord`, `PageRecord`, and `SearchResult`. Use `hashlib.file_digest` for SHA-256 and PyMuPDF for page count. Document ID is `sha256[:16]`; classification uses explicit filename regex rules from `config/documents.toml`, and an unmatched file is reported as an error rather than guessed.

The committed configuration contains exactly these source roots:

```toml
[[sources]]
chip = "esp32-c3"
path = "docs/ESP32-C3"

[[sources]]
chip = "esp32-s3"
path = "docs/ESP32-S3"
```

Resolve logical paths from the nearest ancestor containing both configured source directories; allow an explicit `ESPDOCS_SOURCE_BASE` environment override for clones with a different directory layout. Rules classify `technical_reference_manual`, `datasheet`, `module_datasheet`, and `hardware_design_guidelines`. Store the resolved source path in local manifests and sort records by `(chip, source_path.name.casefold())`.

- [x] **Step 4: Run focused and full tests**

Run: `uv run pytest tests/test_catalog.py -v && uv run pytest -q`

Expected: all tests PASS.

- [x] **Step 5: Commit catalog support**

```powershell
git add config/documents.toml src/espdocs/models.py src/espdocs/catalog.py tests/test_catalog.py
git commit -m "feat: add deterministic ESP PDF catalog"
```

## Task 3: Convert Documents into Page-Traceable Corpus Files

**Files:**
- Create: `src/espdocs/parser.py`
- Create: `tests/test_parser.py`

- [x] **Step 1: Write parser contract tests with a fake Docling document**

The tests must not run OCR. Use a fake object whose `save_as_markdown(..., page_no=N)` records calls. Verify one output file per physical page, one-based page numbers, referenced image mode, and failure if any expected page is absent.

```python
def test_export_pages_preserves_physical_page_numbers(tmp_path, fake_conversion):
    pages = export_pages(fake_conversion, tmp_path, expected_pages=2)

    assert [page.page_no for page in pages] == [1, 2]
    assert (tmp_path / "pages" / "0001.md").exists()
    assert (tmp_path / "pages" / "0002.md").exists()
    assert fake_conversion.saved_page_numbers == [1, 2]
```

- [x] **Step 2: Run the focused parser tests and confirm failure**

Run: `uv run pytest tests/test_parser.py -v`

Expected: FAIL because `espdocs.parser` does not exist.

- [x] **Step 3: Build a pinned local Docling converter**

Construct `PdfPipelineOptions` with `RapidOcrOptions(mode=OcrMode.FULL_PAGE, lang=["chinese"], backend="onnxruntime")`, accurate table mode, picture and page image generation, no remote services, and four CPU threads. Register it through `PdfFormatOption` on `DocumentConverter`.

Conversion must use `raises_on_error=True`. For each page call `save_as_markdown` with `page_no`, `ImageRefMode.REFERENCED`, and a page-specific artifact directory. Save Docling JSON once per document for diagnostics. Never concatenate pages before indexing.

- [x] **Step 4: Run parser tests and an explicit API smoke check**

Run:

```powershell
uv run pytest tests/test_parser.py -v
uv run python -c "from espdocs.parser import build_converter; build_converter(); print('converter-ok')"
```

Expected: tests PASS and output contains `converter-ok` without downloading a VLM.

- [x] **Step 5: Commit the parser adapter**

```powershell
git add src/espdocs/parser.py tests/test_parser.py
git commit -m "feat: add page-traceable Docling conversion"
```

## Task 4: Add Transactional Ingestion and Corpus Quality Gates

**Files:**
- Create: `src/espdocs/ingest.py`
- Create: `tests/test_ingest.py`

- [x] **Step 1: Write failing ingestion tests**

Cover unchanged-hash skipping, stage-directory cleanup, failed conversion preserving the active corpus, manifest persistence, empty-page warnings, replacement only after validation, and UTF-8 Markdown round trips.

```python
def test_failed_ingest_preserves_active_document(tmp_path, failing_parser):
    active = seed_active_document(tmp_path, marker="known-good")

    with pytest.raises(IngestError):
        ingest_document(failing_parser.record, failing_parser, active.parent)

    assert (active / "marker.txt").read_text() == "known-good"
```

- [x] **Step 2: Run tests and confirm failure**

Run: `uv run pytest tests/test_ingest.py -v`

Expected: FAIL because the ingestion coordinator is missing.

- [x] **Step 3: Implement staging, manifest and quality checks**

Write each conversion below `corpus/.staging/<document-id>-<uuid>`. Persist `manifest.json` with document metadata, parser versions, timestamp, page list, warnings, and validation status. Extract a declared document version/date from the converted title and front-matter pages using reviewed regexes; store `unknown` rather than inferring when no unambiguous declaration is present, and force source checks for unknown versions. Reject promotion when page file count differs from PDF page count, every page is empty, Markdown cannot decode as UTF-8, or an image reference escapes the document directory.

Promote with `Path.replace` only after validation. Move an older active directory to a local backup, restore it if promotion fails, and remove the backup after success. Do not delete an active corpus solely because a source file vanished; mark it missing in the next manifest.

- [x] **Step 4: Run ingestion tests and complete suite**

Run: `uv run pytest tests/test_ingest.py -v && uv run pytest -q`

Expected: all tests PASS.

- [x] **Step 5: Commit transactional ingestion**

```powershell
git add src/espdocs/ingest.py tests/test_ingest.py
git commit -m "feat: add transactional corpus ingestion"
```

## Task 5: Build the SQLite FTS5 Trigram Index

**Files:**
- Create: `src/espdocs/index.py`
- Create: `tests/test_index.py`

- [x] **Step 1: Write failing Chinese retrieval and atomic-index tests**

```python
def test_trigram_index_retrieves_chinese_substring(indexed_db):
    rows = indexed_db.search("异步收发器")
    assert rows[0].page_no == 17
    assert rows[0].chip == "esp32-c3"


def test_index_rejects_sqlite_without_trigram(monkeypatch):
    monkeypatch.setattr(index_module, "supports_trigram", lambda _: False)
    with pytest.raises(IndexCapabilityError, match="FTS5 trigram"):
        build_index([], Path("unused.sqlite3"))
```

- [x] **Step 2: Run tests and confirm failure**

Run: `uv run pytest tests/test_index.py -v`

Expected: FAIL because the index module does not exist.

- [x] **Step 3: Implement schema and atomic database build**

Create normalized `documents` and `pages` tables plus:

```sql
CREATE VIRTUAL TABLE pages_fts USING fts5(
  text,
  content='pages',
  content_rowid='id',
  tokenize='trigram'
);
```

Store chip, document type, title, version, source path, SHA-256, page number, Markdown path, content type, warnings, and verification state in ordinary columns. Check FTS5 trigram support in an in-memory database before building. Build into `espdocs.sqlite3.tmp`, run `PRAGMA integrity_check` and an FTS smoke query, close connections, then use `Path.replace` to publish the active database.

- [x] **Step 4: Run tests and inspect SQLite integrity**

Run: `uv run pytest tests/test_index.py -v && uv run pytest -q`

Expected: all tests PASS.

- [x] **Step 5: Commit the index**

```powershell
git add src/espdocs/index.py tests/test_index.py
git commit -m "feat: add Chinese FTS5 trigram index"
```

## Task 6: Add Search Filters, Alias Expansion and Evidence Policy

**Files:**
- Create: `config/aliases.toml`
- Create: `src/espdocs/evidence.py`
- Create: `src/espdocs/retrieval.py`
- Create: `tests/test_retrieval.py`
- Create: `tests/test_evidence.py`

- [ ] **Step 1: Write failing retrieval and safety-policy tests**

Cover exact register terms, Chinese aliases, chip and document-type filters, invalid filters, result limits, stable ordering, and mandatory source checks.

```python
@pytest.mark.parametrize(
    "query",
    ["GPIO_STRAP_REG 复位值", "VDD_SPI 电压", "eFuse 烧录", "启动引脚配置"],
)
def test_high_risk_queries_require_original_pdf(query):
    decision = classify_evidence(query=query, content_type="text", warnings=[])
    assert decision.requires_source_check is True
    assert decision.grade == "C"


def test_chip_filter_never_silently_mixes_s3(search_service):
    results = search_service.search("UART", chip="esp32-c3")
    assert results
    assert {result.chip for result in results} == {"esp32-c3"}
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `uv run pytest tests/test_retrieval.py tests/test_evidence.py -v`

Expected: FAIL because retrieval and evidence modules are absent.

- [ ] **Step 3: Implement deterministic retrieval and fail-closed evidence grading**

Normalize whitespace and Unicode width without altering register punctuation. Load only reviewed aliases from TOML; initially include `UART/通用异步收发器`, `GPIO/通用输入输出`, `GDMA/通用 DMA`, `eFuse/电子熔丝`, and common C3/S3 spellings.

Escape all user terms before constructing FTS MATCH expressions and use SQL parameters for values. Queries shorter than three Unicode code points bypass trigram and use a parameterized exact `instr` search with a strict result limit; they are never padded or silently broadened. Apply chip/document filters in SQL. Rank by BM25, exact literal occurrence, and alias matches; use document ID and page number as deterministic tie breakers.

Evidence policy returns grade C and `requires_source_check=true` for register addresses, bit fields, reset values, electrical quantities, timing, pins, boot, eFuse, security, flashing, tables, pictures, OCR warnings, version conflicts, or inferred answers. A result can become grade B only when page mapping and corpus checks pass and no mandatory-source rule applies. Grade A is assigned only after `source` verifies the hash and provides the original page.

- [ ] **Step 4: Run policy and retrieval tests**

Run: `uv run pytest tests/test_retrieval.py tests/test_evidence.py -v && uv run pytest -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit retrieval and evidence policy**

```powershell
git add config/aliases.toml src/espdocs/evidence.py src/espdocs/retrieval.py tests/test_retrieval.py tests/test_evidence.py
git commit -m "feat: add filtered retrieval and source-check policy"
```

## Task 7: Verify and Render Original PDF Pages

**Files:**
- Create: `src/espdocs/source.py`
- Create: `tests/test_source.py`

- [ ] **Step 1: Write failing source-page tests**

Cover one-based page validation, SHA-256 mismatch, missing source file, deterministic render names, adjacent-page suggestions, and successful PNG rendering.

```python
def test_source_refuses_changed_pdf(tmp_path, sample_pdf):
    expected = sha256_file(sample_pdf)
    sample_pdf.write_bytes(sample_pdf.read_bytes() + b"changed")

    with pytest.raises(SourceChangedError):
        render_source_page(sample_pdf, expected, page_no=1, output_dir=tmp_path)
```

- [ ] **Step 2: Run source tests and confirm failure**

Run: `uv run pytest tests/test_source.py -v`

Expected: FAIL because source verification does not exist.

- [ ] **Step 3: Implement hash-verified rendering**

Recompute SHA-256 before opening the source. Reject page 0 and pages beyond `document.page_count`. Render with PyMuPDF at a fixed 200 DPI to `<sha256-prefix>-p<page-no>-200dpi.png`; write via a temporary file and replace atomically. Return a `SourceView` containing the original absolute path, one-based page, render path, verified hash, evidence grade A, and valid previous/next page numbers.

- [ ] **Step 4: Run source and full tests**

Run: `uv run pytest tests/test_source.py -v && uv run pytest -q`

Expected: all tests PASS and the test PNG has non-zero dimensions.

- [ ] **Step 5: Commit source rendering**

```powershell
git add src/espdocs/source.py tests/test_source.py
git commit -m "feat: add hash-verified PDF page rendering"
```

## Task 8: Expose the Stable `espdocs` CLI and JSON Contract

**Files:**
- Create: `src/espdocs/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI contract tests**

Use Typer's `CliRunner`. Test `doctor`, `ingest --dry-run`, `search`, `show`, `source`, and `--json`. JSON responses contain `schema_version`, stable field names, UTF-8 Chinese, and non-zero exit codes for invalid filters, stale source hashes, missing indexes, and empty queries.

```python
def test_search_json_includes_traceability(cli_runner, seeded_runtime):
    result = cli_runner.invoke(app, ["search", "UART", "--chip", "esp32-c3", "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["schema_version"] == 1
    assert payload["results"][0]["source_path"].endswith("esp32-c3.pdf")
    assert payload["results"][0]["pdf_page"] == 17
    assert "requires_source_check" in payload["results"][0]
```

- [ ] **Step 2: Run CLI tests and confirm failure**

Run: `uv run pytest tests/test_cli.py -v`

Expected: FAIL because the CLI boundary is absent.

- [ ] **Step 3: Implement commands and error mapping**

Wire commands to the existing modules without duplicating domain logic. `ingest` supports `--dry-run` and optional `--document`; `search` supports `--chip`, `--type`, `--limit`, and `--json`; `show` accepts a result/page ID; `source` verifies and renders; `doctor` reports Python, Docling, RapidOCR, PyMuPDF, SQLite/FTS5, source roots, disk paths, and index state; `verify` delegates to Task 9.

Map configuration errors to exit 2, unavailable runtime/index to exit 3, stale or invalid source to exit 4, conversion failures to exit 5, and unexpected failures to exit 1. Never print a traceback unless `--debug` is passed.

- [ ] **Step 4: Run CLI tests and manual help**

Run:

```powershell
uv run pytest tests/test_cli.py -v
uv run espdocs --help
uv run espdocs doctor --json
```

Expected: tests PASS, help lists all six commands, and doctor returns valid schema-versioned JSON.

- [ ] **Step 5: Commit the CLI**

```powershell
git add src/espdocs/cli.py tests/test_cli.py
git commit -m "feat: expose stable espdocs CLI"
```

## Task 9: Add Golden Retrieval Evaluation

**Files:**
- Create: `evaluation/golden.jsonl`
- Create: `src/espdocs/evaluate.py`
- Create: `tests/test_evaluate.py`

- [ ] **Step 1: Write failing evaluation tests**

Test top-five source recall calculation, chip isolation, source-check expectations, malformed evaluation records, empty sets, and a failing threshold exit status.

```python
def test_evaluation_requires_95_percent_top_five_recall(fake_search):
    report = evaluate(cases=twenty_cases_with_one_miss(), search=fake_search)
    assert report.top5_recall == 0.95
    assert report.passed is True
```

- [ ] **Step 2: Run evaluation tests and confirm failure**

Run: `uv run pytest tests/test_evaluate.py -v`

Expected: FAIL because evaluation support is missing.

- [ ] **Step 3: Implement evaluation format and runner**

Each JSONL line contains `id`, `query`, `chip`, optional `document_type`, expected filename, accepted PDF page range, and expected `requires_source_check`. The evaluator queries at limit five, checks source/page matches and chip leakage, and emits per-case diagnostics plus aggregate top-five recall. It exits non-zero below 95% or on any unmarked C3/S3 mixing.

Seed the file with verified location questions only after the pilot corpus exists. Do not store generated answers. Until 20 verified cases exist, report `insufficient_cases` and fail release verification rather than claiming the 95% metric.

- [ ] **Step 4: Run evaluation tests**

Run: `uv run pytest tests/test_evaluate.py -v && uv run pytest -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit evaluation tooling**

```powershell
git add evaluation/golden.jsonl src/espdocs/evaluate.py tests/test_evaluate.py
git commit -m "test: add source-location retrieval evaluation"
```

## Task 10: Pilot, Full Ingestion and Operational Documentation

**Files:**
- Create: `README.md`
- Modify: `evaluation/golden.jsonl`
- Test: all tests and real local corpus checks

- [ ] **Step 1: Run static checks and complete automated suite before real OCR**

Run:

```powershell
uv run ruff format .
uv run ruff check .
uv run pytest -q
uv run espdocs doctor --json
```

Expected: Ruff exits 0, all tests PASS, and doctor confirms Docling 2.120.1, RapidOCR, PyMuPDF, SQLite FTS5 trigram, both source roots, and writable local runtime directories.

- [ ] **Step 2: Run a small real-document pilot**

Run one data sheet first:

```powershell
uv run espdocs ingest --document esp32-c3_datasheet_cn.pdf
uv run espdocs search "UART" --chip esp32-c3 --type datasheet --limit 5 --json
```

Expected: imported page count equals the source PDF page count; every result has source path and PDF page; no S3 result appears.

- [ ] **Step 3: Inspect representative Chinese, table and image pages against PDF**

For at least one Chinese paragraph, one electrical table and one block diagram, run `search`, then `show`, then `source`. Record the expected source filename/page in `evaluation/golden.jsonl`. Confirm the rendered page is readable and the Markdown is treated only as a locator when it differs from the PDF.

- [ ] **Step 4: Ingest all ten approved ESP documents**

Run:

```powershell
uv run espdocs ingest
uv run espdocs verify --json
```

Expected: exactly 10 active documents from the two configured roots, no `MIC` document, all hashes and page counts present, SQLite integrity check `ok`, and no broken page/image references. If full OCR takes longer than the interactive session, keep the command running and report measured progress; do not claim completion from a partial corpus.

- [ ] **Step 5: Complete at least 20 verified golden cases and meet the gate**

Run: `uv run espdocs verify --json`

Expected: at least 20 cases, top-five source recall at least 95%, zero chip leakage, and every high-risk case marked `requires_source_check=true`. Fix aliases or deterministic ranking if the gate fails; do not add semantic retrieval in this phase.

- [ ] **Step 6: Write operational documentation**

Document uv setup, runtime locations, each CLI command, JSON contract, incremental re-ingestion, backup behavior, evidence grades, mandatory original-PDF rules, troubleshooting, and the fact that only `config`, source, tests, evaluation cases, and documentation enter Git.

- [ ] **Step 7: Run final verification and confirm repository hygiene**

Run:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run espdocs doctor --json
uv run espdocs verify --json
git status --short
git ls-files | rg "(sqlite3|corpus/|renders/|\.pdf$)"
```

Expected: all verification commands pass; Git status contains only intended README/evaluation changes before commit; the final `rg` returns no matches because generated data and PDFs are untracked.

- [ ] **Step 8: Commit the verified phase-one system**

```powershell
git add README.md evaluation/golden.jsonl
git commit -m "docs: document verified local ESP knowledge workflow"
```

After this commit, Phase One is ready for a separate design cycle for cross-Agent Skills and optional adapters. Semantic retrieval remains out of scope unless the golden evaluation demonstrates that deterministic retrieval cannot reach the agreed recall threshold.
