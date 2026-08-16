# ESP-IDF Local Docs and Docling Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add version-aware local ESP-IDF documentation research and an adaptive Docling PDF workflow to the portable Codex assets, deploy them locally, and publish them on GitHub.

**Architecture:** Keep the existing ESP32 Skill small and route source-document questions to a dedicated reference. Add a separate generic Docling Skill that chooses direct extraction or full structured conversion by document characteristics, then delegates original-page visual validation and PDF authoring/forms to `pdf:pdf`. Canonical assets remain in Git and a PowerShell installer deploys only the managed global instructions and Skill directories.

**Tech Stack:** Codex Skills (Markdown/YAML), PowerShell, Python/pytest asset tests, uv, Docling CLI, Git.

---

## File Map

- Modify `skills/esp32-ai-hardware-engineering/SKILL.md`: route ESP-IDF software facts to the local source-doc reference.
- Create `skills/esp32-ai-hardware-engineering/references/esp-idf-local-docs.md`: version, target, RST, source-header, and evidence workflow.
- Create `skills/docling-local-document-engineering/SKILL.md`: concise adaptive PDF research workflow and reference routing.
- Create `skills/docling-local-document-engineering/references/adaptive-pdf-workflow.md`: one-off extraction/conversion and original-page verification.
- Create `skills/docling-local-document-engineering/references/reusable-corpus.md`: durable corpus reliability pattern based on this repository.
- Create `skills/docling-local-document-engineering/agents/openai.yaml`: Codex UI metadata and implicit invocation policy.
- Modify `codex/AGENTS.md`: mandatory ESP32 routing plus adaptive PDF research routing.
- Create `scripts/install-codex-assets.ps1`: deploy the canonical instructions and both managed Skills.
- Modify `README.md`: document IDF source use, Docling routing, installation, and cross-machine deployment.
- Modify `tests/test_codex_assets.py`: deterministic contract tests for every canonical asset and routing rule.

### Task 1: Version-Aware ESP-IDF Source Documentation

**Files:**
- Modify: `tests/test_codex_assets.py`
- Modify: `skills/esp32-ai-hardware-engineering/SKILL.md`
- Create: `skills/esp32-ai-hardware-engineering/references/esp-idf-local-docs.md`

- [x] **Step 1: Write the failing asset test**

Add a test that reads the new reference and asserts the required behavior:

```python
def test_esp32_skill_uses_version_matched_local_idf_documentation() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    reference = (SKILL_ROOT / "references" / "esp-idf-local-docs.md").read_text(
        encoding="utf-8"
    )

    assert "esp-idf-local-docs.md" in skill
    assert "$env:IDF_PATH" in reference
    assert r"C:\esp\v6.0.2\esp-idf" in reference
    assert "IDF_TARGET" in reference
    assert "git describe" in reference
    assert "only::" in reference
    assert "include-build-file" in reference
    assert "version mismatch" in reference.casefold()
    assert "component header" in reference.casefold()
    assert "original pdf" in reference.casefold()
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```powershell
uv run pytest tests/test_codex_assets.py::test_esp32_skill_uses_version_matched_local_idf_documentation -v
```

Expected: FAIL because `esp-idf-local-docs.md` does not exist.

- [x] **Step 3: Add the minimal reference and routing**

The new reference must define this deterministic order:

```text
project-confirmed IDF root -> matching IDF_PATH -> C:\esp\v6.0.2\esp-idf fallback
```

It must include concrete PowerShell commands using `git -C <root> describe`, `git -C <root>
rev-parse HEAD`, `rg --glob '*.rst'`, and `rg` over matching component headers/Kconfig. It must tell
the agent to establish `IDF_TARGET`, interpret Sphinx target conditions and includes, prefer English
when translations disagree, report any version mismatch, and assign hardware facts to the exact-chip
original PDF/TRM.

Update the main Skill workflow and quick-reference table so API, Kconfig, build, migration, and
example questions load this reference.

- [x] **Step 4: Run the focused test and Skill validator and verify GREEN**

Run:

```powershell
uv run pytest tests/test_codex_assets.py -v
uv run python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" skills/esp32-ai-hardware-engineering
```

Expected: all asset tests pass and validator prints `Skill is valid!`.

- [x] **Step 5: Commit Task 1**

```powershell
git add tests/test_codex_assets.py skills/esp32-ai-hardware-engineering
git commit -m "feat: ground ESP32 work in local IDF docs"
```

### Task 2: Adaptive Docling PDF Skill

**Files:**
- Modify: `tests/test_codex_assets.py`
- Create: `skills/docling-local-document-engineering/SKILL.md`
- Create: `skills/docling-local-document-engineering/references/adaptive-pdf-workflow.md`
- Create: `skills/docling-local-document-engineering/references/reusable-corpus.md`
- Create: `skills/docling-local-document-engineering/agents/openai.yaml`

- [x] **Step 1: Write failing metadata and workflow tests**

Define `DOCLING_SKILL_ROOT` and tests that assert:

```python
DOCLING_SKILL_ROOT = REPO_ROOT / "skills" / "docling-local-document-engineering"


def test_docling_skill_routes_pdf_research_adaptively() -> None:
    skill = (DOCLING_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    workflow = (
        DOCLING_SKILL_ROOT / "references" / "adaptive-pdf-workflow.md"
    ).read_text(encoding="utf-8")

    assert "Use when" in skill
    assert "native text" in workflow.casefold()
    assert "scanned" in workflow.casefold()
    assert "docling convert" in workflow
    assert "full OCR" in workflow
    assert "physical page" in workflow.casefold()
    assert "SHA-256" in workflow
    assert "adjacent" in workflow.casefold()
    assert "original PDF" in workflow
    assert "pdf:pdf" in skill


def test_docling_skill_documents_reusable_corpus_guards() -> None:
    reference = (
        DOCLING_SKILL_ROOT / "references" / "reusable-corpus.md"
    ).read_text(encoding="utf-8")

    for term in ("resumable", "staging", "atomic", "SQLite", "source hash", "espdocs"):
        assert term.casefold() in reference.casefold()


def test_docling_skill_allows_implicit_invocation() -> None:
    metadata = (DOCLING_SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert 'default_prompt: "Use $docling-local-document-engineering' in metadata
    assert "allow_implicit_invocation: true" in metadata
```

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
uv run pytest tests/test_codex_assets.py -v
```

Expected: FAIL because the Docling Skill directory does not exist.

- [x] **Step 3: Initialize the Skill using the Codex generator**

Run:

```powershell
uv run python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\init_skill.py" docling-local-document-engineering --path skills --resources references --interface 'display_name=Docling Local Document Engineering' --interface 'short_description=Adaptive local PDF extraction and traceable research' --interface 'default_prompt=Use $docling-local-document-engineering to analyze this PDF with traceable original-page evidence.'
```

Expected: the Skill, reference directory, and `agents/openai.yaml` are created.

- [x] **Step 4: Replace generated placeholders with the minimal Skill**

Use this trigger-only frontmatter description:

```yaml
---
name: docling-local-document-engineering
description: "Use when reading, analyzing, extracting, converting, OCRing, or building a reusable local corpus from PDF documents, especially scans, tables, figures, multi-column layouts, or long technical manuals."
---
```

The Skill body must make `adaptive-pdf-workflow.md` required for PDF content research and
`reusable-corpus.md` required only for durable batch collections. It must explicitly require
`pdf:pdf` for original-page visual checks, forms, creation, editing, and final layout QA.

The adaptive reference must distinguish a native-text fast path from full local Docling conversion,
use temporary task-local outputs for one-off work, and require source-page fallback for critical
evidence. The corpus reference must reuse the proven design principles without making unrelated PDFs
depend on ESP32-specific document types or commands.

- [x] **Step 5: Run tests and validator and verify GREEN**

Run:

```powershell
uv run pytest tests/test_codex_assets.py -v
uv run python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" skills/docling-local-document-engineering
```

Expected: all asset tests pass and validator prints `Skill is valid!`.

- [x] **Step 6: Commit Task 2**

```powershell
git add tests/test_codex_assets.py skills/docling-local-document-engineering
git commit -m "feat: add adaptive Docling PDF skill"
```

### Task 3: Global Routing and Portable Deployment

**Files:**
- Modify: `tests/test_codex_assets.py`
- Modify: `codex/AGENTS.md`
- Create: `scripts/install-codex-assets.ps1`
- Modify: `README.md`

- [ ] **Step 1: Write failing routing and installer tests**

Add tests requiring the global rules to load the Docling Skill for PDF research without claiming it
owns creation/forms, and requiring a deployment script that accepts a custom Codex home:

```python
def test_codex_agents_routes_pdf_research_without_owning_pdf_authoring() -> None:
    text = (REPO_ROOT / "codex" / "AGENTS.md").read_text(encoding="utf-8")

    assert "docling-local-document-engineering" in text
    assert "PDF reading" in text
    assert "adaptive" in text.casefold()
    assert "pdf:pdf" in text
    assert "forms" in text.casefold()


def test_portable_codex_installer_manages_both_skills() -> None:
    text = (REPO_ROOT / "scripts" / "install-codex-assets.ps1").read_text(encoding="utf-8")

    assert "CodexHome" in text
    assert "esp32-ai-hardware-engineering" in text
    assert "docling-local-document-engineering" in text
    assert "AGENTS.md" in text
```

- [ ] **Step 2: Run focused tests and verify RED**

Run `uv run pytest tests/test_codex_assets.py -v`.

Expected: FAIL because the global PDF rule and installer do not exist.

- [ ] **Step 3: Add the routing rule, installer, and README guidance**

The installer accepts:

```powershell
param(
    [string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else {
        Join-Path $env:USERPROFILE ".codex"
    })
)
```

It resolves the repository root from `$PSScriptRoot`, creates `$CodexHome\skills`, copies canonical
`codex\AGENTS.md`, and replaces only the two repository-managed Skill directories. It must validate
that all canonical source paths exist before changing the destination and print each deployed path.

Update README with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-codex-assets.ps1
```

Document the custom `-CodexHome` option, `uv tool install docling`, IDF discovery order, local-only
runtime data, and the distinction between Docling research and `pdf:pdf` visual/authoring work.

- [ ] **Step 4: Test installer in an isolated temporary destination**

Run:

```powershell
$testCodexHome = Join-Path $env:TEMP "esp-hardware-knowledge-codex-assets-test"
powershell -ExecutionPolicy Bypass -File .\scripts\install-codex-assets.ps1 -CodexHome $testCodexHome
Get-FileHash .\codex\AGENTS.md, "$testCodexHome\AGENTS.md"
Get-ChildItem "$testCodexHome\skills" -Directory
```

Expected: both AGENTS hashes match and exactly the two managed Skill directories are present in the
fresh destination. Remove this exact temporary test directory after verification.

- [ ] **Step 5: Run asset tests and both Skill validators**

Run:

```powershell
uv run pytest tests/test_codex_assets.py -v
uv run python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" skills/esp32-ai-hardware-engineering
uv run python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" skills/docling-local-document-engineering
```

Expected: all pass.

- [ ] **Step 6: Commit Task 3**

```powershell
git add codex/AGENTS.md scripts/install-codex-assets.ps1 README.md tests/test_codex_assets.py
git commit -m "feat: deploy portable Codex document workflows"
```

### Task 4: Local Deployment, Full Verification, and Publication

**Files:**
- Deploy: `%USERPROFILE%\.codex\AGENTS.md`
- Deploy: `%USERPROFILE%\.codex\skills\esp32-ai-hardware-engineering\`
- Deploy: `%USERPROFILE%\.codex\skills\docling-local-document-engineering\`

- [ ] **Step 1: Run the installer against the real Codex home**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-codex-assets.ps1
```

Expected: the global AGENTS path and both Skill paths are printed.

- [ ] **Step 2: Verify canonical/deployed hashes recursively**

Compare `codex/AGENTS.md` with `%USERPROFILE%\.codex\AGENTS.md`, then compare every relative file
and SHA-256 under each canonical and deployed Skill directory. Expected: no missing, extra, or
different files.

- [ ] **Step 3: Run fresh complete quality gates**

Run:

```powershell
uv run ruff check .
uv run pytest -q
uv run espdocs doctor --json
uv run espdocs verify --json
git status --short
```

Expected: Ruff passes; all tests pass; doctor reports healthy; verify reports passed with at least 20
golden cases and top-5 recall at or above 95%; only the implementation-plan checkbox update may be
uncommitted.

- [ ] **Step 4: Update this plan's completed checkboxes and commit**

```powershell
git add docs/superpowers/plans/2026-08-16-idf-docs-and-docling-skills.md
git commit -m "docs: complete IDF and Docling skill rollout"
```

- [ ] **Step 5: Merge to main and push**

From the primary checkout, fast-forward `main` to the feature branch after confirming the primary
worktree is clean, then run:

```powershell
git push origin main
git status --short --branch
```

Expected: `main` tracks `origin/main` with no uncommitted files.
