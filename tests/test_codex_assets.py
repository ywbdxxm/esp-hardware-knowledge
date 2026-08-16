from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "esp32-ai-hardware-engineering"


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
    assert "espdocs doctor --json" in reference
    assert "espdocs search" in reference
    assert "espdocs show" in reference
    assert "espdocs source" in reference
    assert "--chip" in reference
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
    assert r"C:\esp\v6.0.2\esp-idf" in reference
    assert "IDF_TARGET" in reference
    assert "git describe" in reference
    assert "only::" in reference
    assert "include-build-file" in reference
    assert "version mismatch" in reference.casefold()
    assert "component header" in reference.casefold()
    assert "original pdf" in reference.casefold()
