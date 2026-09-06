"""Approved PDF discovery, classification, hashing, and source configuration."""

from __future__ import annotations

import hashlib
import os
import re
import tomllib
import unicodedata
from pathlib import Path

import pymupdf

from espdocs.models import DocumentIdentity, DocumentRecord, SourceRoot


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
    document_ids: set[str] = set()
    for source in source_roots:
        if not source.path.exists():
            raise SourceConfigurationError(f"Source root does not exist: {source.path}")
        candidates = [source.path] if source.path.is_file() else source.path.rglob("*.pdf")
        for pdf_path in candidates:
            resolved = pdf_path.resolve()
            digest = sha256_file(resolved)
            document_id = digest[:16]
            if document_id in document_ids:
                raise SourceConfigurationError(f"Duplicate document content: {resolved}")
            document_ids.add(document_id)
            stat = resolved.stat()
            with pymupdf.open(resolved) as document:
                page_count = document.page_count
            document_type = source.document_type or classify_document(resolved.name)
            identity = DocumentIdentity(
                vendor=source.vendor,
                family=source.family,
                parts=source.parts,
                variant=source.variant,
                document_type=document_type,
                language=source.language,
                document_revision=source.document_revision,
            )
            records.append(
                DocumentRecord(
                    document_id=document_id,
                    chip=source.chip,
                    document_type=document_type,
                    title=resolved.stem,
                    version=source.document_revision,
                    source_path=resolved,
                    sha256=digest,
                    page_count=page_count,
                    size_bytes=stat.st_size,
                    modified_ns=stat.st_mtime_ns,
                    identity=identity,
                    source_ref=f"sha256:{digest}",
                    source_format=source.source_format,
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
        if all((candidate / relative_path).exists() for relative_path in relative_paths):
            return candidate
    paths = ", ".join(str(path) for path in relative_paths)
    raise SourceConfigurationError(f"Cannot locate configured source directories: {paths}")


def load_source_roots(config_path: Path, repo_root: Path) -> list[SourceRoot]:
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    schema_version = config.get("schema_version", 1)
    if schema_version == 1:
        if set(config) != {"sources"}:
            raise SourceConfigurationError("Schema-v1 supports only [[sources]]")
        entries = config.get("sources")
        if not isinstance(entries, list) or not entries:
            raise SourceConfigurationError(f"No sources configured in {config_path}")
        relative_paths = [Path(str(entry["path"])) for entry in entries]
        base = _find_source_base(repo_root, relative_paths)
        return [
            SourceRoot(
                chip=_normalize(str(entry["chip"])),
                path=(base / relative_path).resolve(),
                parts=(_normalize(str(entry["chip"])),),
            )
            for entry, relative_path in zip(entries, relative_paths, strict=True)
        ]
    if schema_version != 2 or set(config) != {"schema_version", "documents"}:
        raise SourceConfigurationError(f"Unsupported document configuration in {config_path}")

    entries = config.get("documents")
    if not isinstance(entries, list) or not entries:
        raise SourceConfigurationError(f"No documents configured in {config_path}")
    required = {
        "path",
        "vendor",
        "family",
        "parts",
        "document_type",
        "language",
        "document_revision",
    }
    allowed = required | {"variant", "source_format", "compatibility_chip"}
    relative_paths: list[Path] = []
    for entry in entries:
        if not isinstance(entry, dict) or not required <= set(entry) or not set(entry) <= allowed:
            raise SourceConfigurationError("Each schema-v2 document requires exact identity fields")
        relative_path = Path(str(entry["path"]))
        if relative_path.is_absolute():
            raise SourceConfigurationError("Document paths must be relative")
        parts = entry["parts"]
        if not isinstance(parts, list) or not parts or not all(isinstance(p, str) for p in parts):
            raise SourceConfigurationError("Document parts must be a non-empty string list")
        relative_paths.append(relative_path)
    if len(set(relative_paths)) != len(relative_paths):
        raise SourceConfigurationError("Duplicate document path")

    base = _find_source_base(repo_root, relative_paths)
    roots: list[SourceRoot] = []
    for entry, relative_path in zip(entries, relative_paths, strict=True):
        parts = tuple(_normalize(part) for part in entry["parts"])
        family = _normalize(str(entry["family"]))
        compatibility_chip = entry.get("compatibility_chip")
        roots.append(
            SourceRoot(
                chip=(
                    _normalize(str(compatibility_chip))
                    if compatibility_chip is not None
                    else parts[0]
                    if len(parts) == 1
                    else family
                ),
                path=(base / relative_path).resolve(),
                vendor=_normalize(str(entry["vendor"])),
                family=family,
                parts=parts,
                variant=_normalize_optional(entry.get("variant")),
                document_type=_normalize(str(entry["document_type"])),
                language=_normalize(str(entry["language"])),
                source_format=_normalize(str(entry.get("source_format", "pdf"))),
                document_revision=unicodedata.normalize(
                    "NFKC", str(entry["document_revision"])
                ).strip(),
            )
        )
    return roots


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    if not normalized:
        raise SourceConfigurationError("Identity values must not be empty")
    return normalized


def _normalize_optional(value: object) -> str | None:
    if value is None:
        return None
    return _normalize(str(value))
