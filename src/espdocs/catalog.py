"""Approved PDF discovery, classification, hashing, and source configuration."""

from __future__ import annotations

import hashlib
import os
import re
import tomllib
from pathlib import Path

import pymupdf

from espdocs.models import DocumentRecord, SourceRoot


class CatalogError(RuntimeError):
    """Base error for catalog construction."""


class SourceConfigurationError(CatalogError):
    """Raised when configured source roots cannot be resolved."""


class UnclassifiedDocumentError(CatalogError):
    """Raised when an approved source contains an unknown PDF name."""


_DOCUMENT_PATTERNS = (
    (re.compile(r"technical_reference_manual", re.IGNORECASE), "technical_reference_manual"),
    (re.compile(r"hardware-design-guidelines", re.IGNORECASE), "hardware_design_guidelines"),
    (re.compile(r"(?:mini|wroom).+datasheet", re.IGNORECASE), "module_datasheet"),
    (re.compile(r"datasheet", re.IGNORECASE), "datasheet"),
)


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def classify_document(filename: str) -> str:
    for pattern, document_type in _DOCUMENT_PATTERNS:
        if pattern.search(filename):
            return document_type
    raise UnclassifiedDocumentError(f"Cannot classify approved PDF: {filename}")


def discover_documents(source_roots: list[SourceRoot]) -> list[DocumentRecord]:
    records: list[DocumentRecord] = []
    for source in source_roots:
        if not source.path.is_dir():
            raise SourceConfigurationError(f"Source root does not exist: {source.path}")
        for pdf_path in source.path.rglob("*.pdf"):
            resolved = pdf_path.resolve()
            digest = sha256_file(resolved)
            stat = resolved.stat()
            with pymupdf.open(resolved) as document:
                page_count = document.page_count
            records.append(
                DocumentRecord(
                    document_id=digest[:16],
                    chip=source.chip,
                    document_type=classify_document(resolved.name),
                    title=resolved.stem,
                    version="unknown",
                    source_path=resolved,
                    sha256=digest,
                    page_count=page_count,
                    size_bytes=stat.st_size,
                    modified_ns=stat.st_mtime_ns,
                )
            )
    return sorted(records, key=lambda item: (item.chip, item.source_path.name.casefold()))


def _find_source_base(repo_root: Path, relative_paths: list[Path]) -> Path:
    override = os.environ.get("ESPDOCS_SOURCE_BASE")
    candidates = (
        [Path(override).resolve()]
        if override
        else [repo_root.resolve(), *repo_root.resolve().parents]
    )
    for candidate in candidates:
        if all((candidate / relative_path).is_dir() for relative_path in relative_paths):
            return candidate
    paths = ", ".join(str(path) for path in relative_paths)
    raise SourceConfigurationError(f"Cannot locate configured source directories: {paths}")


def load_source_roots(config_path: Path, repo_root: Path) -> list[SourceRoot]:
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    entries = config.get("sources")
    if not isinstance(entries, list) or not entries:
        raise SourceConfigurationError(f"No sources configured in {config_path}")
    relative_paths = [Path(str(entry["path"])) for entry in entries]
    base = _find_source_base(repo_root, relative_paths)
    return [
        SourceRoot(chip=str(entry["chip"]), path=(base / relative_path).resolve())
        for entry, relative_path in zip(entries, relative_paths, strict=True)
    ]
