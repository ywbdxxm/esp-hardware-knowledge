"""Transactional corpus ingestion and quality gates."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any
from uuid import uuid4

from espdocs.models import DocumentRecord, PageRecord
from espdocs.parser import convert_document


class IngestError(RuntimeError):
    """Raised when a document cannot be safely promoted into the corpus."""


@dataclass(frozen=True)
class IngestResult:
    document_id: str
    status: str
    active_dir: Path


Parser = Callable[[DocumentRecord, Path], list[PageRecord]]

_VERSION_PATTERN = re.compile(
    r"(?:版本|Version)\s*[:：]?\s*[vV]?\s*(\d+(?:\.\d+)+)",
    re.IGNORECASE,
)
_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def load_manifest(document_dir: Path) -> dict[str, Any]:
    with (document_dir / "manifest.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _existing_sha256(active_dir: Path) -> str | None:
    try:
        return str(load_manifest(active_dir)["document"]["sha256"])
    except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError):
        return None


def _extract_version(pages: list[PageRecord]) -> str:
    front_matter = "\n".join(page.text for page in pages[:5])
    match = _VERSION_PATTERN.search(front_matter)
    return match.group(1) if match else "unknown"


def _validate_pages(record: DocumentRecord, pages: list[PageRecord], stage: Path) -> list[str]:
    if len(pages) != record.page_count:
        raise IngestError(
            f"Exported page count {len(pages)} does not match PDF page count {record.page_count}"
        )
    expected_numbers = list(range(1, record.page_count + 1))
    if [page.page_no for page in pages] != expected_numbers:
        raise IngestError("Exported physical page numbers are incomplete or out of order")

    warnings: list[str] = []
    empty_pages = 0
    stage_root = stage.resolve()
    for page in pages:
        if not page.markdown_path.is_file():
            raise IngestError(f"Missing Markdown for PDF page {page.page_no}")
        text = page.markdown_path.read_text(encoding="utf-8")
        if not text.strip():
            empty_pages += 1
            warnings.append(f"empty_page:{page.page_no}")
        for reference in _IMAGE_PATTERN.findall(text):
            clean_reference = reference.strip().strip("\"'").split(maxsplit=1)[0]
            if clean_reference.startswith(("http://", "https://", "data:", "#")):
                continue
            target = (page.markdown_path.parent / clean_reference).resolve()
            if not target.is_relative_to(stage_root):
                raise IngestError(
                    f"Image reference escapes document directory on page {page.page_no}: {reference}"
                )
    if empty_pages == record.page_count:
        raise IngestError("Every exported page is empty")
    return warnings


def _write_manifest(
    record: DocumentRecord,
    pages: list[PageRecord],
    stage: Path,
    warnings: list[str],
) -> None:
    detected_version = _extract_version(pages)
    if detected_version == "unknown":
        warnings.append("unknown_document_version")
    document = asdict(record)
    document["source_path"] = str(record.source_path)
    document["version"] = detected_version
    payload = {
        "schema_version": 1,
        "document": document,
        "parser": {
            "docling": package_version("docling"),
            "rapidocr": package_version("rapidocr"),
        },
        "imported_at": datetime.now(UTC).isoformat(),
        "pages": [
            {
                "pdf_page": page.page_no,
                "markdown_path": str(page.markdown_path.relative_to(stage)),
                "content_type": page.content_type,
                "warnings": list(page.warnings),
                "verified": True,
            }
            for page in pages
        ],
        "warnings": warnings,
        "validation": {"passed": True},
    }
    (stage / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _default_parser(record: DocumentRecord, output_dir: Path) -> list[PageRecord]:
    return convert_document(record, output_dir)


def ingest_document(
    record: DocumentRecord,
    parser: Parser | None,
    corpus_dir: Path,
) -> IngestResult:
    active_dir = corpus_dir / record.document_id
    if _existing_sha256(active_dir) == record.sha256:
        return IngestResult(record.document_id, "unchanged", active_dir)

    staging_root = corpus_dir / ".staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    stage = staging_root / f"{record.document_id}-{uuid4().hex}"
    stage.mkdir()
    active_parser = parser or _default_parser
    try:
        pages = active_parser(record, stage)
        warnings = _validate_pages(record, pages, stage)
        _write_manifest(record, pages, stage, warnings)
    except IngestError:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    except Exception as error:
        shutil.rmtree(stage, ignore_errors=True)
        raise IngestError(f"Document conversion failed: {error}") from error

    backup = corpus_dir / f".backup-{record.document_id}-{uuid4().hex}"
    had_active = active_dir.exists()
    try:
        if had_active:
            active_dir.replace(backup)
        stage.replace(active_dir)
    except Exception as error:
        if backup.exists() and not active_dir.exists():
            backup.replace(active_dir)
        shutil.rmtree(stage, ignore_errors=True)
        raise IngestError(f"Corpus promotion failed: {error}") from error
    finally:
        shutil.rmtree(backup, ignore_errors=True)
    return IngestResult(record.document_id, "imported", active_dir)
