# Codex Hardware Document Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Codex hardware-document lookup portable, exact-part-aware, source-traceable, and fast while preserving the current ESPDocs CLI and validated ESP32 corpus.

**Architecture:** Keep ESPDocs as the compatible implementation and separate global routing, hardware-research decisions, PDF processing, runtime configuration, and source verification. Generalize metadata and agent-facing JSON additively, prove the design with the existing ESP32 corpus and one BQ2407x PDF, then align Skills and deployment around the tested contract.

**Tech Stack:** Python 3.13, Typer, SQLite FTS5, PyMuPDF, Docling, RapidOCR, pytest, Ruff, PowerShell, Codex Skills and `AGENTS.md`.

**Spec:** `docs/superpowers/specs/2026-09-06-codex-hardware-document-research-design.md`

## Global Constraints

- The final Codex lookup experience is the primary optimization target.
- Preserve the `espdocs` command, current schema-v1 JSON fields, current corpus, and current index until replacement artifacts pass all gates.
- Do not rename the repository, Python package, or CLI in this implementation.
- Do not move or delete `docs/esp-hardware-knowledge-data` or any original manual.
- The repository is the canonical source for user-maintained Skills and managed global instructions.
- Skills and deployable instructions contain no personal absolute workspace path.
- Missing CUDA may block ingestion but must not block queries against a healthy existing index.
- Exact component and document identity filters never broaden silently.
- Critical hardware facts require a hash-matched authoritative source locator.
- Bundled system Skills such as `pdf:pdf` and `documents:documents` are not modified.
- Every migration and deployment step is staged, validated, and recoverable.
- New document formats require a real source plus a format-specific golden case; the initial implementation remains PDF-complete and only makes the locator contract format-neutral.

---

## File Responsibility Map

### Canonical Codex Assets

- `AGENTS.md`: development rules for this repository only.
- `codex/AGENTS.md`: portable global routing rules deployed into Codex Home.
- `skills/hardware-document-research/`: chip-agnostic component-document research decisions and the stable ESPDocs launcher.
- `skills/esp32-ai-hardware-engineering/`: ESP32/ESP-IDF engineering rules and ESP32-specific adapters.
- `skills/docling-local-document-engineering/`: adaptive PDF extraction and reusable-corpus engineering.

### ESPDocs Runtime

- `src/espdocs/config.py`: machine, project, source-config, and runtime path discovery.
- `src/espdocs/models.py`: document identity, source locator, readiness, page, and result records.
- `src/espdocs/catalog.py`: versioned explicit source metadata and PDF discovery.
- `src/espdocs/index.py`: backward-compatible index schema and atomic rebuild.
- `src/espdocs/retrieval.py`: data-driven filters, compact results, and exact-scope isolation.
- `src/espdocs/source.py`: hash-verified source locator materialization.
- `src/espdocs/cli.py`: stable JSON command boundary for `doctor`, `inventory`, `search`, `show`, `source`, `ingest`, and `verify`.
- `src/espdocs/evaluate.py`: ESP32 and cross-chip golden evaluation.
- `config/documents.toml`: portable explicit metadata for approved manuals.
- `config/aliases.toml`: reviewed terminology aliases, separated from identity metadata.

### Operations and Evaluation

- `scripts/install-codex-assets.ps1`: validated, drift-aware, transactional managed-asset deployment.
- `scripts/check-research-workflow.ps1`: read-only acceptance workflow from an arbitrary directory.
- `evaluation/golden.jsonl`: exact source-location cases.
- `evaluation/codex-scenarios.md`: fresh-task behavioral scenarios and expected observable outcomes.
- `tests/test_*.py`: unit, compatibility, integration, and deployment gates.
- `README.md`: cross-machine setup, maintenance, recovery, and everyday lookup instructions.

---

### Task 1: Restore a Trustworthy Canonical Baseline

**Files:**

- Create: `AGENTS.md`
- Modify: `tests/test_config.py`
- Modify: `tests/test_codex_assets.py`
- Modify: `skills/esp32-ai-hardware-engineering/SKILL.md`
- Modify: `skills/esp32-ai-hardware-engineering/references/esp-idf-local-docs.md`
- Modify: `skills/esp32-ai-hardware-engineering/references/implementation-checklists.md`
- Modify: `skills/esp32-ai-hardware-engineering/references/local-document-retrieval.md`
- Create: `skills/esp32-ai-hardware-engineering/references/windows-esp-idf-environment.md`

**Interfaces:**

- Consumes: the current deployed ESP32 Skill under `%CODEX_HOME%/skills/esp32-ai-hardware-engineering`.
- Produces: one reviewed canonical ESP32 Skill in Git and a clean repository test baseline.

- [ ] **Step 1: Add a failing environment-isolation regression test**

Add an autouse fixture to `tests/test_config.py` and explicitly verify a test that expects LocalAppData is not affected by the user's real environment:

```python
import pytest


@pytest.fixture(autouse=True)
def isolate_espdocs_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "ESPDOCS_DATA_ROOT",
        "ESPDOCS_DEVICE",
        "ESPDOCS_REPO_ROOT",
        "ESPDOCS_SOURCE_BASE",
    ):
        monkeypatch.delenv(name, raising=False)
```

- [ ] **Step 2: Run the isolated configuration test and confirm the baseline defect is exposed before the fixture is applied**

Run:

```powershell
uv run --locked pytest tests/test_config.py -q
```

Expected before the fixture: `test_discover_uses_local_app_data` fails when the host has
`ESPDOCS_DATA_ROOT` configured. Expected after the fixture: all configuration tests pass.

- [ ] **Step 3: Add repository-local development instructions**

Create a concise root `AGENTS.md` containing these enforceable rules:

```markdown
# ESPDocs Repository Instructions

- Treat this repository as the canonical source for `codex/` and `skills/` assets.
- Do not deploy until source Skills validate and destination drift has been checked.
- Keep PDFs, corpus data, indexes, renders, caches, logs, virtual environments, and backups out of Git.
- Preserve schema-v1 CLI fields and the existing runtime until compatibility and golden tests pass.
- Use failing tests first for code, configuration, deployment, or Skill-contract changes.
- Run targeted tests, Ruff, the full test suite, both Skill validators, `espdocs doctor --json`, and `espdocs verify --json` before completion.
- Never answer critical hardware facts from generated Markdown alone; verify the hash-matched original source locator.
```

- [ ] **Step 4: Add failing canonical-content tests before importing the deployed improvements**

Extend `tests/test_codex_assets.py` with assertions for the Windows environment reference, locked
project invocation, and absence of the personal workspace fallback:

```python
def test_canonical_esp32_skill_contains_deployed_environment_rules() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    local_docs = (
        SKILL_ROOT / "references" / "local-document-retrieval.md"
    ).read_text(encoding="utf-8")

    assert "windows-esp-idf-environment.md" in skill
    assert "uv run --locked --project" in local_docs
    assert "Desktop\\AI-HRADWARE" not in local_docs
    assert (SKILL_ROOT / "references" / "windows-esp-idf-environment.md").is_file()
```

- [ ] **Step 5: Review and import the newer deployed ESP32 files into the repository**

Use a recursive no-index diff, review every difference, then update the canonical files to include
the newer IDF-revision selection, EIM/Windows activation, VS Code consistency, and locked ESPDocs
invocation rules. Remove only the personal path fallback from the imported local-document reference.

Run:

```powershell
git diff --no-index -- skills/esp32-ai-hardware-engineering `
  "$env:CODEX_HOME/skills/esp32-ai-hardware-engineering"
```

Do not run the installer during this reconciliation.

- [ ] **Step 6: Run the baseline gates**

Run:

```powershell
uv run --locked pytest tests/test_config.py tests/test_codex_assets.py -q
uv run --locked ruff check .
uv run --locked pytest -q
uv run --locked python "$env:CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" `
  skills/esp32-ai-hardware-engineering
```

Expected: Ruff passes, every baseline and newly added test passes, and the canonical ESP32 Skill
validates.

- [ ] **Step 7: Commit the recovered baseline**

```powershell
git add AGENTS.md tests/test_config.py tests/test_codex_assets.py `
  skills/esp32-ai-hardware-engineering
git commit -m "fix: restore canonical Codex research baseline"
```

---

### Task 2: Split Query Readiness from Ingestion Readiness

**Files:**

- Modify: `src/espdocs/models.py`
- Modify: `src/espdocs/cli.py`
- Modify: `src/espdocs/evaluate.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_config.py`

**Interfaces:**

- Consumes: existing `AppPaths`, source configuration, index, and GPU diagnostics.
- Produces: `doctor --json` with `readiness.query`, `readiness.source`,
  `readiness.ingest`, and `verify_recommended`, while retaining existing top-level fields.

- [ ] **Step 1: Write failing readiness-contract tests**

Add these cases to `tests/test_cli.py`:

```python
def test_doctor_keeps_existing_index_queryable_without_cuda(
    cli_runtime: dict[str, Path], monkeypatch
) -> None:
    monkeypatch.setattr(
        cli_module,
        "gpu_status",
        lambda: GpuStatus(
            ready=False,
            torch_cuda=False,
            torch_cuda_version=None,
            onnx_cuda=False,
            onnx_providers=("CPUExecutionProvider",),
            device_name=None,
            memory_mib=None,
        ),
    )

    result = CliRunner().invoke(app, ["doctor", "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["readiness"]["query"] is True
    assert payload["readiness"]["source"] is True
    assert payload["readiness"]["ingest"] is False


def test_doctor_reports_missing_index_as_query_unready(
    cli_runtime: dict[str, Path]
) -> None:
    cli_runtime["database"].unlink()

    result = CliRunner().invoke(app, ["doctor", "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["readiness"]["query"] is False
    assert payload["readiness"]["ingest"] is True
```

- [ ] **Step 2: Run the targeted tests and verify that the new readiness fields are absent**

```powershell
uv run --locked pytest tests/test_cli.py -q
```

Expected: the two new tests fail on missing `readiness` keys.

- [ ] **Step 3: Add the typed readiness record**

Add to `src/espdocs/models.py`:

```python
@dataclass(frozen=True)
class ReadinessReport:
    query: bool
    source: bool
    ingest: bool
    verify_recommended: bool
    reasons: tuple[str, ...]
```

The `reasons` values are stable machine-readable identifiers such as `missing_index`,
`missing_source`, `cuda_unavailable`, and `verification_stale`.

- [ ] **Step 4: Compute independent readiness in `doctor`**

Keep `components`, `gpu`, `sources`, `runtime`, and `healthy` for schema-v1 clients. Define
`healthy` as the legacy aggregate and add the new authoritative structure:

```python
readiness = ReadinessReport(
    query=trigram and paths.index_path.is_file(),
    source=all(root.path.is_dir() for root in roots),
    ingest=accelerator_healthy and all(root.path.is_dir() for root in roots),
    verify_recommended=not paths.index_path.is_file(),
    reasons=tuple(readiness_reasons),
)
```

Do not run full `verify_runtime()` from `doctor`; this command remains lightweight.

- [ ] **Step 5: Preserve exit-code behavior and run compatibility tests**

```powershell
uv run --locked pytest tests/test_cli.py tests/test_config.py -q
uv run --locked pytest -q
```

Expected: all existing CLI assertions and the new readiness assertions pass.

- [ ] **Step 6: Measure the ordinary readiness call**

```powershell
Measure-Command {
  uv run --locked --project . espdocs doctor --json | Out-Null
} | Select-Object TotalMilliseconds
```

Record the result in the completion report. The command performs no corpus conversion or golden
evaluation.

- [ ] **Step 7: Commit the readiness contract**

```powershell
git add src/espdocs/models.py src/espdocs/cli.py src/espdocs/evaluate.py `
  tests/test_cli.py tests/test_config.py
git commit -m "feat: separate ESPDocs query and ingest readiness"
```

---

### Task 3: Introduce Portable Explicit Hardware Metadata

**Files:**

- Modify: `config/documents.toml`
- Modify: `src/espdocs/models.py`
- Modify: `src/espdocs/catalog.py`
- Modify: `src/espdocs/ingest.py`
- Modify: `src/espdocs/index.py`
- Modify: `tests/test_catalog.py`
- Modify: `tests/test_ingest.py`
- Modify: `tests/test_index.py`

**Interfaces:**

- Consumes: schema-v1 `[[sources]] chip/path` configuration and corpus manifests.
- Produces: schema-v2 document identity with `vendor`, `family`, `parts`, `variant`,
  `document_type`, `language`, `source_format`, `document_revision`, `source_ref`, and a generic
  locator, while reading legacy records without OCR reprocessing.

- [ ] **Step 1: Write failing schema-v2 configuration tests**

Add representative explicit entries to a temporary test config:

```python
config.write_text(
    """
schema_version = 2

[[documents]]
path = "docs/ESP32-C3/esp32-c3_datasheet_cn.pdf"
vendor = "espressif"
family = "esp32"
parts = ["esp32-c3"]
document_type = "datasheet"
language = "zh-CN"
document_revision = "unknown"

[[documents]]
path = "docs/PMIC/bq2407x.pdf"
vendor = "texas-instruments"
family = "bq2407x"
parts = ["bq24072", "bq24073", "bq24074", "bq24075", "bq24079"]
document_type = "datasheet"
language = "zh-CN"
document_revision = "ZHCSIF0N"
""".strip(),
    encoding="utf-8",
)
```

Assert that paths resolve relative to the configured source base, fields normalize to lowercase
identity values, and unknown keys or missing required identity fields fail with
`SourceConfigurationError`.

- [ ] **Step 2: Write a failing legacy-compatibility test**

Keep the existing two-entry schema-v1 fixture and assert it still returns `SourceRoot` records with
`vendor="espressif"`, `family="esp32"`, `parts=(chip,)`, `source_format="pdf"`, and
`document_revision="unknown"` derived by the compatibility loader.

- [ ] **Step 3: Run the catalog tests and confirm schema-v2 is unsupported**

```powershell
uv run --locked pytest tests/test_catalog.py -q
```

Expected: new explicit-document tests fail while current schema-v1 tests pass.

- [ ] **Step 4: Add document identity and locator types**

Add these records to `src/espdocs/models.py` and embed them in `DocumentRecord`, `SearchResult`, and
`IndexedPage` without removing existing `chip` or `pdf_page` fields:

```python
@dataclass(frozen=True)
class DocumentIdentity:
    vendor: str
    family: str
    parts: tuple[str, ...]
    variant: str | None
    document_type: str
    language: str
    document_revision: str


@dataclass(frozen=True)
class SourceLocator:
    source_format: str
    kind: str
    physical_page: int | None
    anchor: str | None
```

For the first implementation, valid published locators are
`SourceLocator("pdf", "pdf_page", page_no, None)`.

- [ ] **Step 5: Implement strict schema-v2 loading with schema-v1 compatibility**

Use `tomllib`, validate exact supported keys, normalize identity fields with NFKC plus lowercase,
and reject duplicate resolved paths or document IDs. Explicit schema-v2 entries own identity;
filename matching is retained only by the schema-v1 compatibility path and dry-run diagnostics.

- [ ] **Step 6: Convert the canonical configuration to explicit schema-v2 entries**

Declare all ten existing ESP32 PDFs and `docs/PMIC/bq2407x.pdf`. Use these exact BQ fields:

```toml
[[documents]]
path = "docs/PMIC/bq2407x.pdf"
vendor = "texas-instruments"
family = "bq2407x"
parts = ["bq24072", "bq24073", "bq24074", "bq24075", "bq24079"]
document_type = "datasheet"
language = "zh-CN"
document_revision = "ZHCSIF0N"
```

Use `part="esp32-c3"` or `part="esp32-s3"` semantics for chip datasheets, TRMs, and hardware design
guides. Use exact module part lists for MINI and WROOM datasheets. Continue resolving the existing
`docs` library through a portable source-base setting; do not store `C:/Users/ljm75/...` in TOML.

- [ ] **Step 7: Make manifests and the index additive and backward-compatible**

Write an identity object and locator per page in new manifests. When loading a schema-v1 manifest,
derive identity from legacy `chip`, `document_type`, and `version`, with
`vendor="espressif"`, `family="esp32"`, `parts=(chip,)`, and PDF physical-page locators. Add index
columns in a schema-v2 rebuild rather than mutating the active SQLite file in place.

- [ ] **Step 8: Prove existing corpus reuse without Docling conversion**

Add a test that seeds a schema-v1 corpus manifest, wraps the parser with a call counter, rebuilds the
schema-v2 index, and asserts the parser call count remains zero and the resulting row has a PDF
locator plus compatibility fields.

- [ ] **Step 9: Run metadata and compatibility tests**

```powershell
uv run --locked pytest tests/test_catalog.py tests/test_ingest.py tests/test_index.py -q
uv run --locked pytest -q
```

- [ ] **Step 10: Commit portable metadata support**

```powershell
git add config/documents.toml src/espdocs/models.py src/espdocs/catalog.py `
  src/espdocs/ingest.py src/espdocs/index.py tests/test_catalog.py `
  tests/test_ingest.py tests/test_index.py
git commit -m "feat: add portable hardware document identity"
```

---

### Task 4: Make Retrieval Exact, Discoverable, and Token-Efficient

**Files:**

- Modify: `src/espdocs/retrieval.py`
- Modify: `src/espdocs/cli.py`
- Modify: `src/espdocs/models.py`
- Modify: `tests/test_retrieval.py`
- Modify: `tests/test_cli.py`

**Interfaces:**

- Consumes: indexed schema-v2 identity and schema-v1 compatibility fields.
- Produces: `inventory --json`, data-driven search filters, structured exact-scope no-match behavior,
  and `search --compact --json`.

- [ ] **Step 1: Write failing data-driven filter tests**

Seed ESP32-C3 and BQ2407x documents, then assert:

```python
def test_exact_part_filter_never_leaks_another_family(search_service: SearchService) -> None:
    results = search_service.search("ISET", part="bq24075")

    assert results
    assert {result.identity.family for result in results} == {"bq2407x"}
    assert all("bq24075" in result.identity.parts for result in results)


def test_unknown_part_returns_no_results_without_broadening(
    search_service: SearchService,
) -> None:
    assert search_service.search("ISET", part="bq99999") == []
```

Remove `_CHIPS` and `_DOCUMENT_TYPES` as authorities. Reject malformed filter syntax with a structured
`InvalidFilterValue`; a normalized but unindexed identity value returns an empty exact-scope result.

- [ ] **Step 2: Write failing inventory and compact-output CLI tests**

```python
def test_inventory_reports_indexed_identity_values(cli_runtime: dict[str, Path]) -> None:
    result = CliRunner().invoke(app, ["inventory", "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["schema_version"] == 1
    assert "esp32-c3" in payload["inventory"]["parts"]


def test_compact_search_omits_internal_paths(cli_runtime: dict[str, Path]) -> None:
    result = CliRunner().invoke(
        app,
        ["search", "UART", "--part", "esp32-c3", "--compact", "--json"],
    )
    hit = json.loads(result.stdout)["results"][0]

    assert set(hit) == {
        "page_id",
        "source_ref",
        "vendor",
        "family",
        "parts",
        "document_type",
        "document_revision",
        "locator",
        "snippet",
        "evidence_grade",
        "requires_source_check",
        "source_check_reasons",
    }
```

- [ ] **Step 3: Run the targeted tests and confirm missing commands/options**

```powershell
uv run --locked pytest tests/test_retrieval.py tests/test_cli.py -q
```

- [ ] **Step 4: Implement index-derived inventory**

Add `SearchService.inventory() -> DocumentInventory` using `SELECT DISTINCT` over normalized indexed
identity. Return sorted tuples for vendors, families, parts, variants, document types, languages,
revisions, and document count. Expose it as `espdocs inventory --json`.

- [ ] **Step 5: Implement additive exact metadata filters**

Extend `SearchService.search()` and the CLI with:

```python
def search(
    self,
    query: str,
    *,
    chip: str | None = None,
    vendor: str | None = None,
    family: str | None = None,
    part: str | None = None,
    variant: str | None = None,
    document_type: str | None = None,
    language: str | None = None,
    limit: int = 10,
) -> list[SearchResult]:
```

`chip` remains a compatibility filter and cannot be combined with a contradictory `part` filter.

- [ ] **Step 6: Implement compact agent output without changing default JSON**

Add a serializer that returns only the fields asserted in the compact-output test. Default
`search --json` retains all schema-v1 fields plus new identity and locator fields.

- [ ] **Step 7: Run search compatibility and token-size checks**

```powershell
uv run --locked pytest tests/test_retrieval.py tests/test_cli.py -q
$full = uv run --locked espdocs search UART --chip esp32-c3 --limit 5 --json
$compact = uv run --locked espdocs search UART --part esp32-c3 --limit 5 --compact --json
[pscustomobject]@{ FullBytes=$full.Length; CompactBytes=$compact.Length }
```

Record the byte counts. Require compact output to be smaller and to retain every evidence decision
field.

- [ ] **Step 8: Commit the retrieval experience**

```powershell
git add src/espdocs/retrieval.py src/espdocs/cli.py src/espdocs/models.py `
  tests/test_retrieval.py tests/test_cli.py
git commit -m "feat: add exact agent-oriented hardware lookup"
```

---

### Task 5: Prove Cross-Chip PDF Research with BQ2407x

**Files:**

- Modify: `evaluation/golden.jsonl`
- Modify: `src/espdocs/evaluate.py`
- Modify: `tests/test_evaluate.py`
- Modify: `tests/test_source.py`
- Runtime input only: `C:/Users/ljm75/Desktop/AI-HRADWARE/docs/PMIC/bq2407x.pdf`

**Interfaces:**

- Consumes: explicit BQ2407x metadata and the existing 53-page TI PDF.
- Produces: a cross-family golden case and verified original-page render without weakening ESP32
  isolation.

- [ ] **Step 1: Add generic identity fields to golden-case parsing**

Replace the evaluation's required `chip` identity with `vendor`, `family`, and `part`, while accepting
legacy `chip` cases through a compatibility parser. Preserve the existing 23 cases unchanged on disk
until the new parser passes them.

- [ ] **Step 2: Write a failing cross-chip evaluation test**

```python
def test_evaluation_rejects_part_leakage_even_with_correct_hit() -> None:
    case = GoldenCase(
        case_id="bq2407x-iset-programming",
        query="fast charge current ISET resistor",
        vendor="texas-instruments",
        family="bq2407x",
        part="bq24075",
        document_type="datasheet",
        expected_filename="bq2407x.pdf",
        locator_min=25,
        locator_max=25,
        requires_source_check=True,
    )
    leaked = hit(case, family="esp32", part="esp32-c3")

    report = evaluate([case] * 20, search=lambda _: [leaked])

    assert report.identity_leakage == 20
    assert report.passed is False
```

- [ ] **Step 3: Ingest only the approved BQ2407x document into staging**

Run the dry run first:

```powershell
uv run --locked espdocs ingest --document bq2407x.pdf --dry-run --json
```

Confirm the output identity is Texas Instruments, family BQ2407x, the five configured parts,
datasheet, `zh-CN`, document revision `ZHCSIF0N`, source format PDF, and 53 physical pages. Then run:

```powershell
uv run --locked espdocs ingest --document bq2407x.pdf --json
```

The existing corpus and index remain recoverable until full verification passes.

- [ ] **Step 4: Fix the golden query against actual indexed output**

Use this candidate query and filters:

```powershell
uv run --locked espdocs search "fast charge current ISET resistor" `
  --vendor texas-instruments --part bq24075 --type datasheet --limit 5 --compact --json
```

Accept physical page 25 only after `show` text and the original page agree that the fast-charge
current is programmed by the resistor from ISET to VSS. If phrase tokenization ranks the pin table
first, use the exact phrase `charge current translator` while keeping the expected page at 25.

- [ ] **Step 5: Add the reviewed golden record**

Append one JSONL record with ID `bq2407x-iset-programming`, vendor `texas-instruments`, family
`bq2407x`, part `bq24075`, expected filename `bq2407x.pdf`, PDF page range `[25, 25]`, and
`requires_source_check=true`.

- [ ] **Step 6: Verify both representative original pages visually**

Use `espdocs source <page_id> --json` on the page-25 hit and inspect the rendered image. Also inspect
physical page 8 to confirm the package/pin table identifies ISET pin 16 and the 590-ohm to 8.9-kohm
programming range. Record the source hash and document header `ZHCSIF0N - REVISED OCTOBER 2021` in
the test evidence notes.

- [ ] **Step 7: Run the full corpus and retrieval gates**

```powershell
uv run --locked pytest tests/test_evaluate.py tests/test_source.py -q
uv run --locked espdocs verify --json
```

Expected: the evaluation has at least 24 cases, top-5 recall remains at least 0.95, identity leakage
is zero, source-check failures are zero, and corpus/index counts agree.

- [ ] **Step 8: Commit the cross-chip proof**

```powershell
git add evaluation/golden.jsonl src/espdocs/evaluate.py `
  tests/test_evaluate.py tests/test_source.py
git commit -m "test: prove cross-chip source-grounded retrieval"
```

Do not add the PDF, corpus, SQLite index, renders, or conversion outputs to Git.

---

### Task 6: Add the Generic Hardware Research Skill and Stable Launcher

**Files:**

- Create: `skills/hardware-document-research/SKILL.md`
- Create: `skills/hardware-document-research/agents/openai.yaml`
- Create: `skills/hardware-document-research/references/evidence-workflow.md`
- Create: `skills/hardware-document-research/references/project-context.md`
- Create: `skills/hardware-document-research/scripts/invoke-espdocs.ps1`
- Modify: `tests/test_codex_assets.py`
- Create: `tests/test_launcher.py`

**Interfaces:**

- Consumes: `doctor`, `inventory`, exact filtered `search`, `show`, `source`, and the locked ESPDocs
  project environment.
- Produces: a portable task-centered Skill and one launcher usable from any project directory.

- [ ] **Step 1: Initialize the Skill skeleton with only required resources**

```powershell
uv run --locked python "$env:CODEX_HOME/skills/.system/skill-creator/scripts/init_skill.py" `
  hardware-document-research --path skills --resources scripts,references `
  --interface 'display_name=Hardware Document Research' `
  --interface 'short_description=Exact-part hardware research with authoritative evidence' `
  --interface 'default_prompt=Use $hardware-document-research to verify this component question against exact source documentation.'
```

- [ ] **Step 2: Write failing Skill-boundary tests**

Add assertions that the Skill:

```python
def test_hardware_research_skill_has_portable_exact_source_contract() -> None:
    root = REPO_ROOT / "skills" / "hardware-document-research"
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    workflow = (root / "references" / "evidence-workflow.md").read_text(encoding="utf-8")

    assert "exact part" in skill.casefold()
    assert "inventory" in workflow
    assert "--compact" in workflow
    assert "source" in workflow
    assert "official vendor" in workflow.casefold()
    assert "Desktop\\AI-HRADWARE" not in skill + workflow
    assert "ESP-IDF" not in workflow
```

- [ ] **Step 3: Write the concise Skill entrypoint**

The `SKILL.md` entrypoint must route rather than duplicate procedures:

```markdown
---
name: hardware-document-research
description: "Use for source-grounded questions about semiconductor or electronic-component datasheets, reference manuals, errata, application notes, design guides, pins, electrical limits, timing, registers, packages, and hardware integration. Do not use for generic software work or PDF authoring."
---

# Hardware Document Research

Resolve the exact vendor, family, part, variant/package, silicon revision, and project context before
accepting a hardware claim. Mark unknown identity instead of substituting a related device.

For local lookup and evidence grading, read `references/evidence-workflow.md`. For project context
and cross-machine discovery, read `references/project-context.md`.

Use the local corpus when query-ready. Fall back only to authoritative vendor material and disclose
the fallback. Critical values, pins, timing, registers, tables, and diagrams require the original
source locator; generated text is a locator rather than final evidence.
```

- [ ] **Step 4: Implement the stable PowerShell launcher**

`invoke-espdocs.ps1` resolves in this order:

1. process-level `ESP_HARDWARE_KNOWLEDGE_ROOT`;
2. user-level `ESP_HARDWARE_KNOWLEDGE_ROOT`;
3. a bounded current-directory/ancestor candidate containing `pyproject.toml`, `uv.lock`, and
   `src/espdocs`.

For a project root, run this exact boundary:

```powershell
& uv run --locked --project $resolvedRoot espdocs @EspdocsArguments
exit $LASTEXITCODE
```

Reject zero or multiple bounded candidates with one structured stderr message. Do not contain a
Desktop fallback and do not install packages.

- [ ] **Step 5: Test launcher discovery from an unrelated working directory**

In `tests/test_launcher.py`, create a temporary fake `uv.cmd` that records arguments, set
`ESP_HARDWARE_KNOWLEDGE_ROOT` to the real repository, start PowerShell in another temporary directory, and
assert the recorded arguments use the resolved fixture path:

```python
assert recorded_arguments == [
    "run",
    "--locked",
    "--project",
    str(repository.resolve()),
    "espdocs",
    "doctor",
    "--json",
]
```

Add failure cases for a missing root, incomplete root, and conflicting candidates.

- [ ] **Step 6: Write the evidence and project-context references**

The ordinary evidence flow is exactly:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$runner = Join-Path $codexHome "skills/hardware-document-research/scripts/invoke-espdocs.ps1"
& $runner doctor --json
& $runner inventory --json
$search = & $runner search "fast charge current ISET resistor" `
  --part bq24075 --type datasheet --limit 5 --compact --json | ConvertFrom-Json
$pageId = $search.results[0].page_id
& $runner show $pageId --json
& $runner source $pageId --json
```

The reference instructs Codex to skip `inventory` when the exact indexed filter is already known and
to call `source` only when `requires_source_check` is true or context is ambiguous. It requires full
`verify` only after ingestion, index/config migration, suspected corruption, or a readiness
recommendation.

- [ ] **Step 7: Validate and test the new Skill**

```powershell
uv run --locked pytest tests/test_codex_assets.py tests/test_launcher.py -q
uv run --locked python "$env:CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" `
  skills/hardware-document-research
```

- [ ] **Step 8: Commit the generic research interface**

```powershell
git add skills/hardware-document-research tests/test_codex_assets.py tests/test_launcher.py
git commit -m "feat: add portable hardware document research skill"
```

---

### Task 7: Align All Managed Skills and AGENTS Instructions

**Files:**

- Modify: `codex/AGENTS.md`
- Modify: `skills/esp32-ai-hardware-engineering/SKILL.md`
- Modify: `skills/esp32-ai-hardware-engineering/references/local-document-retrieval.md`
- Modify: `skills/docling-local-document-engineering/SKILL.md`
- Modify: `skills/docling-local-document-engineering/references/adaptive-pdf-workflow.md`
- Modify: `skills/docling-local-document-engineering/references/reusable-corpus.md`
- Modify: `skills/esp32-ai-hardware-engineering/agents/openai.yaml`
- Modify: `skills/docling-local-document-engineering/agents/openai.yaml`
- Modify: `tests/test_codex_assets.py`

**Interfaces:**

- Consumes: the working research contract and generic Skill from Tasks 2-6.
- Produces: non-overlapping task routing with progressive disclosure and no machine paths.

- [ ] **Step 1: Write failing routing-responsibility tests**

Add tests proving:

```python
def test_global_agents_routes_by_task_without_embedding_commands() -> None:
    text = (REPO_ROOT / "codex" / "AGENTS.md").read_text(encoding="utf-8")

    assert "hardware-document-research" in text
    assert "esp32-ai-hardware-engineering" in text
    assert "docling-local-document-engineering" in text
    assert "pdf:pdf" in text
    assert "uv run" not in text
    assert "Desktop\\AI-HRADWARE" not in text


def test_managed_skills_have_distinct_ownership() -> None:
    hardware = read_skill("hardware-document-research")
    esp32 = read_skill("esp32-ai-hardware-engineering")
    docling = read_skill("docling-local-document-engineering")

    assert "exact part" in hardware.casefold()
    assert "ESP-IDF" in esp32
    assert "OCR" in docling
    assert "ESP-IDF" not in docling
```

- [ ] **Step 2: Reduce global `AGENTS.md` to portable routing and invariants**

Keep four sections: project context first, hardware research, ESP32 engineering, and document-format
processing. Put commands and detailed procedures in Skills. Require original-source verification for
critical hardware claims and prohibit silent part/revision substitution.

- [ ] **Step 3: Make the ESP32 local-document reference a thin adapter**

Require exact `IDF_TARGET`, module/part, and project-selected ESP-IDF revision. Invoke
`hardware-document-research` for the common evidence flow, then add only ESP32-specific filters and
the ownership split between ESP-IDF source docs and chip PDFs. Remove duplicated launcher discovery
code and the personal data-root sentence.

- [ ] **Step 4: Tighten the Docling Skill around processing**

Keep the adaptive native-text/Docling choice, physical-page traceability, staged corpus publication,
and `pdf:pdf` relationship. Replace `This machine uses cuda` with this portable rule:

```markdown
Select an accelerator from verified runtime capability and explicit configuration. Report the
selected device for large conversion. Never silently change a configured GPU conversion to CPU.
```

The reusable-corpus reference names ESPDocs as a proven PDF implementation but routes unrelated
hardware research to `hardware-document-research` rather than inheriting ESP32 filters.

- [ ] **Step 5: Review metadata and implicit invocation**

Keep `allow_implicit_invocation: true` for all three managed Skills. Make each description selective
enough that ordinary software work does not trigger hardware research and ordinary PDF creation does
not trigger Docling extraction.

- [ ] **Step 6: Run validation and overlap tests**

```powershell
uv run --locked pytest tests/test_codex_assets.py -q
uv run --locked python "$env:CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" `
  skills/hardware-document-research
uv run --locked python "$env:CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" `
  skills/esp32-ai-hardware-engineering
uv run --locked python "$env:CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" `
  skills/docling-local-document-engineering
```

- [ ] **Step 7: Commit the routing cleanup**

```powershell
git add codex/AGENTS.md skills tests/test_codex_assets.py
git commit -m "refactor: align Codex hardware research responsibilities"
```

---

### Task 8: Make Managed Asset Deployment Drift-Aware and Recoverable

**Files:**

- Modify: `scripts/install-codex-assets.ps1`
- Create: `tests/test_deployment.py`
- Modify: `tests/test_codex_assets.py`
- Modify: `README.md`

**Interfaces:**

- Consumes: validated canonical `codex/AGENTS.md` and three canonical Skill directories.
- Produces: `-Check`, safe install/update, explicit `-Force`, a last-deployed hash manifest, and
  complete rollback on failure.

- [ ] **Step 1: Write failing deployment behavior tests in a temporary Codex Home**

Use Python `subprocess.run()` with `powershell.exe -NoProfile -File`. Cover:

1. `-Check` makes no files and returns nonzero when assets are absent.
2. First install stages all three Skills, global instructions, and the manifest.
3. `-Check` then succeeds.
4. An edit to a deployed Skill causes normal update to fail without changing the edit.
5. `-Force` replaces the edited managed asset after reporting its path.
6. An injected staging failure restores all previous files and the previous manifest.
7. An unmanaged Skill remains byte-identical through every mode.

- [ ] **Step 2: Add explicit command modes**

Use this parameter surface:

```powershell
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }),
    [string]$ValidatorPath = $(Join-Path $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }) "skills/.system/skill-creator/scripts/quick_validate.py"),
    [switch]$Check,
    [switch]$Force
)
```

Reject `-Check -Force`. `-Check` compares canonical, deployed, and last-deployed hashes without any
directory creation.

- [ ] **Step 3: Define the deployment manifest**

Write `%CODEX_HOME%/managed/esp-hardware-knowledge-assets.json` with schema version, repository
commit, deployment timestamp, and SHA-256 keyed by managed relative path. Normalize relative paths
with forward slashes and sort them before serialization.

- [ ] **Step 4: Validate sources before staging**

Run `$ValidatorPath` against all three canonical Skill directories. This separate parameter allows a
temporary or alternate destination Codex Home to use the validator owned by the active Codex
installation. Fail before destination writes if the validator is missing or any Skill fails. Verify
the canonical global instructions and every declared source file exist.

- [ ] **Step 5: Detect destination drift against the last manifest**

Safe update rules are exact:

- absent destination: install;
- destination hash equals current canonical hash: no-op and allow manifest bootstrap;
- destination hash equals last-deployed hash: safe to update;
- destination differs from both: fail and list drift unless `-Force` is present.

- [ ] **Step 6: Stage and switch the whole managed set**

Copy global instructions, all three Skills, and the new manifest into one staging root under Codex
Home. Move the current managed assets to one backup root, promote the staged set, verify promoted
hashes, then remove the backup. On any exception, restore the backup and retain the staging path in
the error report for diagnosis.

- [ ] **Step 7: Run deployment tests and a read-only check against the real Codex Home**

```powershell
uv run --locked pytest tests/test_deployment.py tests/test_codex_assets.py -q
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts/install-codex-assets.ps1 -Check
```

The first real `-Check` is expected to report drift because the repository is not deployed yet. Do
not force deployment until the full repository verification in Task 10 passes.

- [ ] **Step 8: Commit deployment safety**

```powershell
git add scripts/install-codex-assets.ps1 tests/test_deployment.py `
  tests/test_codex_assets.py README.md
git commit -m "feat: protect Codex asset deployment from drift"
```

---

### Task 9: Add a Reproducible Codex Research Acceptance Workflow

**Files:**

- Create: `scripts/check-research-workflow.ps1`
- Create: `evaluation/codex-scenarios.md`
- Create: `tests/test_workflow_script.py`
- Modify: `README.md`

**Interfaces:**

- Consumes: the stable launcher, readiness, inventory, compact search, source verification, and
  BQ2407x golden case.
- Produces: one read-only machine check and a small fresh-task acceptance suite focused on Codex
  behavior.

- [ ] **Step 1: Write a failing workflow-script integration test**

The test runs the workflow with a temporary runtime and asserts the JSON summary contains:

```json
{
  "schema_version": 1,
  "passed": true,
  "checks": {
    "query_ready": true,
    "esp32_exact_scope": true,
    "bq2407x_exact_scope": true,
    "source_hash_verified": true,
    "compact_output": true
  }
}
```

- [ ] **Step 2: Implement the read-only workflow script**

The script accepts `-Launcher`, `-EspPart esp32-c3`, and `-BqPart bq24075`. It performs one doctor
call, skips full verify unless `verify_recommended` is true, performs exact compact searches for an
ESP32 register and BQ2407x ISET, calls `show`, calls `source` for the required evidence, verifies
returned identity and hash fields, and emits only the summary JSON plus failures.

- [ ] **Step 3: Document seven behavioral scenarios**

`evaluation/codex-scenarios.md` contains the seven scenarios from the design with:

- the exact user prompt;
- expected Skill routing;
- maximum normal tool-call sequence;
- required identity and source evidence;
- prohibited fallback behavior;
- pass/fail observations.

Use these exact representative prompts:

```text
ESP32-C3 的 GPIO_STRAP_REG 在哪里定义，回答前核对原始手册。
这个项目使用 ESP-IDF 的哪个版本？用对应版本说明这个 API。
BQ24075 的 ISET 电阻如何决定充电电流？核对原始数据手册。
我只有一个模糊丝印 ABC123，能直接按相似芯片给出绝对最大额定值吗？
CUDA 当前不可用，已有手册索引还能不能查？
数据手册文件被替换后，旧索引中的电气参数还能直接引用吗？
解释这张数据手册表格，并检查原始页面与脚注。
```

- [ ] **Step 4: Add measurable experience targets to README**

Document the everyday path as: launcher `doctor`, optional `inventory`, compact exact `search`, one
`show`, and conditional `source`. State that `verify` is a maintenance gate. Document how to add a
manual with explicit identity, how to update the index, and how to recover from a changed source.

- [ ] **Step 5: Run the automated acceptance workflow from outside the repository**

```powershell
$repoRoot = (Resolve-Path -LiteralPath ".").Path
$workflow = Join-Path $repoRoot "scripts/check-research-workflow.ps1"
$launcher = Join-Path $repoRoot "skills/hardware-document-research/scripts/invoke-espdocs.ps1"
Push-Location $env:TEMP
try {
  & $workflow -Launcher $launcher
}
finally {
  Pop-Location
}
```

Expected: `"passed": true` and no corpus, index, render, or source modification.

- [ ] **Step 6: Run fresh Codex-task forward tests only after explicit user authorization**

Create isolated Codex tasks using the exact prompts in `evaluation/codex-scenarios.md`. Do not tell
the test task the intended answer. Record which Skills activated, tool-call count, selected identity,
source locator, and fallback behavior. Fix only failures demonstrated by these outcomes.

- [ ] **Step 7: Commit the acceptance workflow**

```powershell
git add scripts/check-research-workflow.ps1 evaluation/codex-scenarios.md `
  tests/test_workflow_script.py README.md
git commit -m "test: add Codex hardware research acceptance workflow"
```

---

### Task 10: Full Verification, Controlled Deployment, and Final Audit

**Files:**

- Modify only when a verification failure identifies a scoped defect.
- Deploy after all source checks pass: `%CODEX_HOME%/AGENTS.md`
- Deploy after all source checks pass: `%CODEX_HOME%/skills/hardware-document-research/`
- Deploy after all source checks pass: `%CODEX_HOME%/skills/esp32-ai-hardware-engineering/`
- Deploy after all source checks pass: `%CODEX_HOME%/skills/docling-local-document-engineering/`
- Create during deployment: `%CODEX_HOME%/managed/esp-hardware-knowledge-assets.json`

**Interfaces:**

- Consumes: every prior task's tested canonical artifacts.
- Produces: deliberate canonical/deployed parity and an evidence-backed completion report.

- [ ] **Step 1: Scan the plan and implementation for scope violations**

Verify no implementation renamed ESPDocs, moved runtime data, added vector search, modified bundled
system Skills, or added unrelated source formats. Verify Git tracks no PDF, SQLite, render, corpus,
cache, log, backup, or virtual-environment artifact.

```powershell
git status --short
git ls-files | Select-String -Pattern '\.(pdf|sqlite3|png)$|(^|/)(corpus|renders|cache|logs|backups|\.venv)/'
```

Expected: only intended source files are listed by status and the tracked-artifact scan is empty.

- [ ] **Step 2: Run static checks and the complete test suite**

```powershell
uv run --locked ruff check .
uv run --locked pytest -q
```

Expected: zero Ruff errors and all tests pass without inherited user-environment dependence.

- [ ] **Step 3: Validate every canonical Skill**

```powershell
$validator = "$env:CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py"
uv run --locked python $validator skills/hardware-document-research
uv run --locked python $validator skills/esp32-ai-hardware-engineering
uv run --locked python $validator skills/docling-local-document-engineering
```

Expected: each prints `Skill is valid!`.

- [ ] **Step 4: Run runtime and evidence gates**

```powershell
uv run --locked espdocs doctor --json
uv run --locked espdocs verify --json
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check-research-workflow.ps1 `
  -Launcher skills/hardware-document-research/scripts/invoke-espdocs.ps1
```

Expected: query and source readiness are true, full verification passes, ESP32 golden recall remains
at least 0.95, cross-chip identity leakage is zero, and the workflow summary passes.

- [ ] **Step 5: Run a deployment preflight**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts/install-codex-assets.ps1 -Check
```

Review every reported difference. A difference from the last manifest or current canonical source
must be understood before continuing.

- [ ] **Step 6: Deploy without force when destinations are unmodified**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts/install-codex-assets.ps1
```

Use `-Force` only if the preflight identifies a known destination-only change that has already been
intentionally incorporated into the canonical repository. The installer must list that drift before
replacement.

- [ ] **Step 7: Verify deployed parity recursively**

Run the installer's `-Check` again and recursively compare canonical/deployed relative paths and
SHA-256 hashes. Expected: no missing, extra managed, or differing files.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts/install-codex-assets.ps1 -Check
```

- [ ] **Step 8: Re-run a lookup through the deployed launcher**

From a directory outside the repository, run deployed `doctor`, one ESP32 compact search, and one
BQ2407x compact search. Verify exact identity, source locator, and evidence decision fields.

- [ ] **Step 9: Confirm recoverability and no data movement**

Record the existing runtime root, index hash, corpus document/page counts, and original manual paths.
Confirm the runtime remains under its pre-implementation location and no manual was removed.

- [ ] **Step 10: Commit only scoped verification fixes, then report results**

If verification required scoped source corrections, commit them with a message naming the corrected
contract. The completion report includes:

- tests and exact pass counts;
- Skill validation results;
- doctor readiness fields;
- verify document/page counts and top-5 recall;
- BQ2407x source page and hash verification;
- common-path command count and compact/full byte counts;
- deployment parity result;
- unchanged runtime location;
- unsupported non-PDF formats and the real-source gate for adding them.

---

## Follow-On Format Rule

After Tasks 1-10 pass in real Codex development, add one non-PDF adapter in a separate design and
implementation plan. Select the format from an actual project need. Reuse `DocumentIdentity`,
`SourceLocator`, exact filtering, hash/snapshot verification, and golden evaluation. Do not route a
new format through Docling merely because Docling can parse it; choose the source-native or Docling
path that produces the most faithful, stable locator.
