from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "esp32-ai-hardware-engineering"
DOCLING_SKILL_ROOT = REPO_ROOT / "skills" / "docling-local-document-engineering"
HARDWARE_RESEARCH_SKILL_ROOT = REPO_ROOT / "skills" / "hardware-document-research"


def test_codex_agents_requires_esp32_skill_for_code_and_documentation() -> None:
    text = (REPO_ROOT / "codex" / "AGENTS.md").read_text(encoding="utf-8")

    assert "MUST use" in text
    assert "esp32-ai-hardware-engineering" in text
    assert "datasheet" in text.casefold()
    assert "technical reference manual" in text.casefold()
    assert "build, flash, debug" in text.casefold()


def test_skill_routes_local_document_research_through_espdocs() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    reference = (SKILL_ROOT / "references" / "local-document-retrieval.md").read_text(
        encoding="utf-8"
    )

    assert "documentation research" in skill.casefold()
    assert "local-document-retrieval.md" in skill
    assert "invoke-espdocs.ps1" in reference
    assert "doctor --json" in reference
    assert "search" in reference
    assert "show" in reference
    assert "source" in reference
    assert "--part" in reference
    assert "original pdf" in reference.casefold()


def test_codex_skill_allows_implicit_invocation() -> None:
    metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert 'default_prompt: "Use $esp32-ai-hardware-engineering' in metadata
    assert "allow_implicit_invocation: true" in metadata


def test_esp32_skill_uses_version_matched_local_idf_documentation() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    reference = (SKILL_ROOT / "references" / "esp-idf-local-docs.md").read_text(
        encoding="utf-8"
    )

    assert "esp-idf-local-docs.md" in skill
    assert "$env:IDF_PATH" in reference
    assert r"C:\esp\v6.0.2\esp-idf" not in reference
    assert "IDF_TARGET" in reference
    assert "git describe" in reference
    assert "only::" in reference
    assert "include-build-file" in reference
    assert "report the mismatch" in reference.casefold()
    assert "component header" in reference.casefold()
    assert "original pdf" in reference.casefold()


def test_canonical_esp32_skill_contains_deployed_environment_rules() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    local_docs = (
        SKILL_ROOT / "references" / "local-document-retrieval.md"
    ).read_text(encoding="utf-8")

    assert "windows-esp-idf-environment.md" in skill
    assert "invoke-espdocs.ps1" in local_docs
    assert "Desktop\\AI-HRADWARE" not in local_docs
    assert (SKILL_ROOT / "references" / "windows-esp-idf-environment.md").is_file()


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
    assert "empty output" in workflow.casefold()
    assert "--device $device" in workflow
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


def test_readme_documents_cross_machine_codex_setup() -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "install-codex-assets.ps1" in text
    assert "uv tool install docling" in text
    assert "IDF_PATH" in text
    assert "docling-local-document-engineering" in text


def test_hardware_research_skill_has_portable_exact_source_contract() -> None:
    skill = (HARDWARE_RESEARCH_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    workflow = (
        HARDWARE_RESEARCH_SKILL_ROOT / "references" / "evidence-workflow.md"
    ).read_text(encoding="utf-8")
    context = (
        HARDWARE_RESEARCH_SKILL_ROOT / "references" / "project-context.md"
    ).read_text(encoding="utf-8")
    metadata = (
        HARDWARE_RESEARCH_SKILL_ROOT / "agents" / "openai.yaml"
    ).read_text(encoding="utf-8")

    assert "exact part" in skill.casefold()
    assert "inventory" in workflow
    assert "--compact" in workflow
    assert "source" in workflow
    assert "official vendor" in workflow.casefold()
    assert "ESP_HARDWARE_KNOWLEDGE_ROOT" in context
    assert "Desktop\\AI-HRADWARE" not in skill + workflow + context
    assert "ESP-IDF" not in workflow
    assert "allow_implicit_invocation: true" in metadata


def test_global_agents_routes_by_task_without_embedding_commands() -> None:
    text = (REPO_ROOT / "codex" / "AGENTS.md").read_text(encoding="utf-8")

    assert "hardware-document-research" in text
    assert "esp32-ai-hardware-engineering" in text
    assert "docling-local-document-engineering" in text
    assert "pdf:pdf" in text
    assert "uv run" not in text
    assert "Desktop\\AI-HRADWARE" not in text


def test_managed_skills_have_distinct_ownership() -> None:
    hardware = (HARDWARE_RESEARCH_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    esp32 = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    docling = (DOCLING_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "exact part" in hardware.casefold()
    assert "ESP-IDF" in esp32
    assert "OCR" in docling
    assert "ESP-IDF" not in docling


def test_esp32_document_reference_delegates_general_evidence_workflow() -> None:
    reference = (SKILL_ROOT / "references" / "local-document-retrieval.md").read_text(
        encoding="utf-8"
    )

    assert "hardware-document-research" in reference
    assert "invoke-espdocs.ps1" in reference
    assert "IDF_TARGET" in reference
    assert "uv run --locked --project" not in reference


def test_docling_skill_selects_accelerator_from_verified_runtime() -> None:
    workflow = (
        DOCLING_SKILL_ROOT / "references" / "adaptive-pdf-workflow.md"
    ).read_text(encoding="utf-8")

    assert "verified runtime capability" in workflow.casefold()
    assert "This machine uses" not in workflow
    assert '$device = "cuda"' not in workflow


def test_managed_codex_assets_contain_no_personal_workspace_path() -> None:
    managed = [REPO_ROOT / "codex", REPO_ROOT / "skills"]

    for root in managed:
        for path in root.rglob("*"):
            if path.is_file():
                assert "Desktop\\AI-HRADWARE" not in path.read_text(encoding="utf-8")
