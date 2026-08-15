import json
import sqlite3
from pathlib import Path

import pytest

import espdocs.index as index_module
from espdocs.index import IndexBuildError, IndexCapabilityError, build_index


def seed_document(
    corpus: Path,
    *,
    document_id: str = "doc-c3",
    chip: str = "esp32-c3",
    text: str = "通用异步收发器 UART 寄存器说明",
    page_no: int = 17,
) -> Path:
    document_dir = corpus / document_id
    page_path = document_dir / "pages" / f"{page_no:04d}.md"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(text, encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "document": {
            "document_id": document_id,
            "chip": chip,
            "document_type": "technical_reference_manual",
            "title": f"{chip} TRM",
            "version": "1.4",
            "source_path": str((corpus.parent / f"{chip}.pdf").resolve()),
            "sha256": "a" * 64,
            "page_count": 20,
            "size_bytes": 100,
            "modified_ns": 1,
        },
        "pages": [
            {
                "pdf_page": page_no,
                "markdown_path": str(page_path.relative_to(document_dir)),
                "content_type": "text",
                "warnings": [],
                "verified": True,
            }
        ],
        "warnings": [],
        "validation": {"passed": True},
    }
    (document_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return document_dir


def test_trigram_index_retrieves_chinese_substring(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    seed_document(corpus)
    database = tmp_path / "index" / "espdocs.sqlite3"

    result = build_index(corpus, database)

    assert result.document_count == 1
    assert result.page_count == 1
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT p.pdf_page, d.chip
            FROM pages_fts f
            JOIN pages p ON p.id = f.rowid
            JOIN documents d ON d.document_id = p.document_id
            WHERE pages_fts MATCH ?
            """,
            ("异步收发器",),
        ).fetchone()
    assert row == (17, "esp32-c3")


def test_index_records_traceability_metadata(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    seed_document(corpus)
    database = tmp_path / "espdocs.sqlite3"

    build_index(corpus, database)

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT version, source_path, sha256, pdf_page, verified FROM documents JOIN pages USING(document_id)"
        ).fetchone()
    assert row[0] == "1.4"
    assert row[1].endswith("esp32-c3.pdf")
    assert row[2] == "a" * 64
    assert row[3:] == (17, 1)


def test_index_ignores_staging_directories(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    seed_document(corpus)
    seed_document(corpus / ".staging", document_id="unfinished")
    database = tmp_path / "espdocs.sqlite3"

    result = build_index(corpus, database)

    assert result.document_count == 1


def test_failed_build_preserves_existing_database(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    broken = corpus / "broken"
    broken.mkdir(parents=True)
    (broken / "manifest.json").write_text("not-json", encoding="utf-8")
    database = tmp_path / "espdocs.sqlite3"
    database.write_bytes(b"known-good")

    with pytest.raises(IndexBuildError):
        build_index(corpus, database)

    assert database.read_bytes() == b"known-good"


def test_index_rejects_sqlite_without_trigram(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(index_module, "supports_trigram", lambda _connection: False)

    with pytest.raises(IndexCapabilityError, match="FTS5 trigram"):
        build_index(tmp_path / "corpus", tmp_path / "espdocs.sqlite3")
