"""Atomic SQLite FTS5 trigram index construction."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class IndexBuildError(RuntimeError):
    """Raised when an index cannot be safely constructed."""


class IndexCapabilityError(IndexBuildError):
    """Raised when the local SQLite lacks required FTS capabilities."""


@dataclass(frozen=True)
class IndexBuildResult:
    database_path: Path
    document_count: int
    page_count: int


_SCHEMA = """
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    chip TEXT NOT NULL,
    document_type TEXT NOT NULL,
    title TEXT NOT NULL,
    version TEXT NOT NULL,
    source_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    size_bytes INTEGER NOT NULL,
    modified_ns INTEGER NOT NULL,
    vendor TEXT NOT NULL,
    family TEXT NOT NULL,
    parts_json TEXT NOT NULL,
    variant TEXT,
    language TEXT NOT NULL,
    document_revision TEXT NOT NULL,
    source_format TEXT NOT NULL,
    source_ref TEXT NOT NULL
);

CREATE TABLE pages (
    id INTEGER PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    pdf_page INTEGER NOT NULL,
    markdown_path TEXT NOT NULL,
    text TEXT NOT NULL,
    content_type TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    verified INTEGER NOT NULL,
    locator_kind TEXT NOT NULL,
    physical_page INTEGER,
    anchor TEXT,
    UNIQUE(document_id, pdf_page)
);

CREATE VIRTUAL TABLE pages_fts USING fts5(
    text,
    content='pages',
    content_rowid='id',
    tokenize='trigram'
);

CREATE TABLE index_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def supports_trigram(connection: sqlite3.Connection) -> bool:
    try:
        connection.execute(
            "CREATE VIRTUAL TABLE temp.trigram_probe USING fts5(body, tokenize='trigram')"
        )
        connection.execute("DROP TABLE temp.trigram_probe")
    except sqlite3.Error:
        return False
    return True


def _load_manifest(document_dir: Path) -> dict[str, Any]:
    with (document_dir / "manifest.json").open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("validation", {}).get("passed") is not True:
        raise IndexBuildError(f"Corpus document is not validated: {document_dir.name}")
    return manifest


def _document_dirs(corpus_dir: Path) -> list[Path]:
    if not corpus_dir.is_dir():
        return []
    return sorted(
        (path for path in corpus_dir.iterdir() if path.is_dir() and not path.name.startswith(".")),
        key=lambda path: path.name.casefold(),
    )


def _insert_document(
    connection: sqlite3.Connection,
    document_dir: Path,
    manifest: dict[str, Any],
) -> int:
    document = manifest["document"]
    identity = document.get("identity") or {
        "vendor": "espressif",
        "family": "esp32",
        "parts": [document["chip"]],
        "variant": None,
        "language": "unknown",
        "document_revision": document["version"],
    }
    source_format = str(document.get("source_format", "pdf"))
    source_ref = str(document.get("source_ref", f"sha256:{document['sha256']}"))
    connection.execute(
        """
        INSERT INTO documents (
            document_id, chip, document_type, title, version, source_path,
            sha256, page_count, size_bytes, modified_ns, vendor, family,
            parts_json, variant, language, document_revision, source_format, source_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document["document_id"],
            document["chip"],
            document["document_type"],
            document["title"],
            document["version"],
            document["source_path"],
            document["sha256"],
            document["page_count"],
            document["size_bytes"],
            document["modified_ns"],
            identity["vendor"],
            identity["family"],
            json.dumps(identity["parts"], ensure_ascii=False),
            identity.get("variant"),
            identity["language"],
            identity["document_revision"],
            source_format,
            source_ref,
        ),
    )
    page_count = 0
    document_root = document_dir.resolve()
    global_warnings = list(manifest.get("warnings", []))
    for page in manifest["pages"]:
        locator = page.get("locator") or {
            "source_format": source_format,
            "kind": "pdf_page",
            "physical_page": page["pdf_page"],
            "anchor": None,
        }
        markdown_path = (document_dir / page["markdown_path"]).resolve()
        if not markdown_path.is_relative_to(document_root) or not markdown_path.is_file():
            raise IndexBuildError(f"Invalid Markdown path in {document_dir.name}: {markdown_path}")
        text = markdown_path.read_text(encoding="utf-8")
        warnings = global_warnings + list(page.get("warnings", []))
        cursor = connection.execute(
            """
            INSERT INTO pages (
                document_id, pdf_page, markdown_path, text,
                content_type, warnings_json, verified, locator_kind,
                physical_page, anchor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document["document_id"],
                page["pdf_page"],
                str(markdown_path),
                text,
                page["content_type"],
                json.dumps(warnings, ensure_ascii=False),
                int(bool(page["verified"])),
                locator["kind"],
                locator.get("physical_page"),
                locator.get("anchor"),
            ),
        )
        connection.execute(
            "INSERT INTO pages_fts(rowid, text) VALUES (?, ?)",
            (cursor.lastrowid, text),
        )
        page_count += 1
    return page_count


def build_index(corpus_dir: Path, database_path: Path) -> IndexBuildResult:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = database_path.with_suffix(database_path.suffix + ".tmp")
    temporary_path.unlink(missing_ok=True)
    document_count = 0
    page_count = 0
    try:
        connection = sqlite3.connect(temporary_path)
        try:
            with connection:
                connection.execute("PRAGMA foreign_keys = ON")
                if not supports_trigram(connection):
                    raise IndexCapabilityError("SQLite FTS5 trigram tokenizer is unavailable")
                connection.executescript(_SCHEMA)
                for document_dir in _document_dirs(corpus_dir):
                    manifest = _load_manifest(document_dir)
                    page_count += _insert_document(connection, document_dir, manifest)
                    document_count += 1
                connection.execute(
                    "INSERT INTO index_metadata(key, value) VALUES ('schema_version', '2')"
                )
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                if integrity != ("ok",):
                    raise IndexBuildError(f"SQLite integrity check failed: {integrity}")
                indexed_pages = connection.execute("SELECT count(*) FROM pages_fts").fetchone()[0]
                if indexed_pages != page_count:
                    raise IndexBuildError(
                        f"FTS page count {indexed_pages} does not match corpus page count {page_count}"
                    )
        finally:
            connection.close()
    except IndexBuildError:
        temporary_path.unlink(missing_ok=True)
        raise
    except Exception as error:
        temporary_path.unlink(missing_ok=True)
        raise IndexBuildError(f"Failed to build SQLite index: {error}") from error
    temporary_path.replace(database_path)
    return IndexBuildResult(database_path, document_count, page_count)
