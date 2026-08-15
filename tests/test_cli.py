import json
from pathlib import Path

import pymupdf
import pytest
from typer.testing import CliRunner

from espdocs.catalog import sha256_file
from espdocs.cli import app
from espdocs.index import build_index


def write_pdf(path: Path, pages: int = 2) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open()
    for index in range(pages):
        page = document.new_page()
        page.insert_text((72, 72), f"source page {index + 1}")
    document.save(path)
    document.close()
    return path


@pytest.fixture
def cli_runtime(tmp_path: Path, monkeypatch) -> dict[str, Path]:
    hardware = tmp_path / "AI-HRADWARE"
    repo = hardware / "esp-hardware-knowledge"
    c3_root = hardware / "docs" / "ESP32-C3"
    s3_root = hardware / "docs" / "ESP32-S3"
    source = write_pdf(c3_root / "esp32-c3_datasheet_cn.pdf")
    s3_root.mkdir(parents=True)
    config_dir = repo / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "documents.toml").write_text(
        '[[sources]]\nchip="esp32-c3"\npath="docs/ESP32-C3"\n'
        '[[sources]]\nchip="esp32-s3"\npath="docs/ESP32-S3"\n',
        encoding="utf-8",
    )
    (config_dir / "aliases.toml").write_text(
        '[[groups]]\nterms=["UART", "通用异步收发器"]\n', encoding="utf-8"
    )
    local = tmp_path / "LocalAppData"
    data = local / "esp-hardware-knowledge"
    corpus_doc = data / "corpus" / "doc-c3"
    page_path = corpus_doc / "pages" / "0017.md"
    page_path.parent.mkdir(parents=True)
    page_path.write_text("UART register overview", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "document": {
            "document_id": "doc-c3",
            "chip": "esp32-c3",
            "document_type": "datasheet",
            "title": "ESP32-C3 Datasheet",
            "version": "1.4",
            "source_path": str(source.resolve()),
            "sha256": sha256_file(source),
            "page_count": 2,
            "size_bytes": source.stat().st_size,
            "modified_ns": source.stat().st_mtime_ns,
        },
        "pages": [
            {
                "pdf_page": 1,
                "markdown_path": "pages/0017.md",
                "content_type": "text",
                "warnings": [],
                "verified": True,
            }
        ],
        "warnings": [],
        "validation": {"passed": True},
    }
    (corpus_doc / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    database = data / "index" / "espdocs.sqlite3"
    build_index(data / "corpus", database)
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("ESPDOCS_REPO_ROOT", str(repo))
    monkeypatch.setenv("ESPDOCS_SOURCE_BASE", str(hardware))
    return {"repo": repo, "source": source, "database": database, "data": data}


def test_help_lists_all_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("ingest", "search", "show", "source", "doctor", "verify"):
        assert command in result.stdout


def test_search_json_includes_traceability(cli_runtime: dict[str, Path]) -> None:
    result = CliRunner().invoke(app, ["search", "UART", "--chip", "esp32-c3", "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["schema_version"] == 1
    assert payload["results"][0]["source_path"].endswith("esp32-c3_datasheet_cn.pdf")
    assert payload["results"][0]["pdf_page"] == 1
    assert "requires_source_check" in payload["results"][0]


def test_show_json_returns_full_indexed_page(cli_runtime: dict[str, Path]) -> None:
    result = CliRunner().invoke(app, ["show", "1", "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["page"]["text"] == "UART register overview"
    assert payload["page"]["pdf_page"] == 1


def test_source_json_renders_authoritative_page(cli_runtime: dict[str, Path]) -> None:
    result = CliRunner().invoke(app, ["source", "1", "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["source"]["evidence_grade"] == "A"
    assert Path(payload["source"]["render_path"]).is_file()


def test_doctor_reports_required_components(cli_runtime: dict[str, Path]) -> None:
    result = CliRunner().invoke(app, ["doctor", "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["healthy"] is True
    assert payload["components"]["fts5_trigram"] is True
    assert payload["components"]["docling"] == "2.120.1"
    assert payload["sources"]["configured"] == 2


def test_ingest_dry_run_does_not_convert(cli_runtime: dict[str, Path]) -> None:
    result = CliRunner().invoke(app, ["ingest", "--dry-run", "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["documents"][0]["filename"] == "esp32-c3_datasheet_cn.pdf"
    assert payload["documents"][0]["action"] == "would_ingest"


def test_invalid_filter_uses_configuration_exit_code(cli_runtime: dict[str, Path]) -> None:
    result = CliRunner().invoke(app, ["search", "UART", "--chip", "esp8266", "--json"])

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["type"] == "RetrievalError"


def test_missing_index_uses_runtime_exit_code(cli_runtime: dict[str, Path]) -> None:
    cli_runtime["database"].unlink()

    result = CliRunner().invoke(app, ["search", "UART", "--json"])

    assert result.exit_code == 3
    assert json.loads(result.stdout)["error"]["type"] == "IndexUnavailable"
