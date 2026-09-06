"""Typed records shared across the ESP document pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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


@dataclass(frozen=True)
class SourceRoot:
    chip: str
    path: Path
    vendor: str = "espressif"
    family: str = "esp32"
    parts: tuple[str, ...] = ()
    variant: str | None = None
    document_type: str | None = None
    language: str = "unknown"
    source_format: str = "pdf"
    document_revision: str = "unknown"

    def __post_init__(self) -> None:
        if not self.parts:
            object.__setattr__(self, "parts", (self.chip,))


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    chip: str
    document_type: str
    title: str
    version: str
    source_path: Path
    sha256: str
    page_count: int
    size_bytes: int
    modified_ns: int
    identity: DocumentIdentity | None = None
    source_ref: str | None = None
    source_format: str = "pdf"


@dataclass(frozen=True)
class PageRecord:
    document_id: str
    page_no: int
    markdown_path: Path
    text: str
    content_type: str
    warnings: tuple[str, ...]
    verified: bool


@dataclass(frozen=True)
class EvidenceDecision:
    grade: str
    requires_source_check: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessReport:
    query: bool
    source: bool
    ingest: bool
    verify_recommended: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class DocumentInventory:
    vendors: tuple[str, ...]
    families: tuple[str, ...]
    parts: tuple[str, ...]
    variants: tuple[str, ...]
    document_types: tuple[str, ...]
    languages: tuple[str, ...]
    revisions: tuple[str, ...]
    document_count: int


@dataclass(frozen=True)
class SearchResult:
    page_id: int
    document_id: str
    chip: str
    document_type: str
    title: str
    version: str
    source_path: Path
    sha256: str
    pdf_page: int
    markdown_path: Path
    snippet: str
    content_type: str
    warnings: tuple[str, ...]
    verified: bool
    score: float
    matched_terms: tuple[str, ...]
    evidence_grade: str
    requires_source_check: bool
    source_check_reasons: tuple[str, ...]
    identity: DocumentIdentity | None = None
    source_ref: str | None = None
    locator: SourceLocator | None = None


@dataclass(frozen=True)
class SourceView:
    source_path: Path
    pdf_page: int
    render_path: Path
    verified_sha256: str
    evidence_grade: str
    previous_page: int | None
    next_page: int | None


@dataclass(frozen=True)
class IndexedPage:
    page_id: int
    document_id: str
    chip: str
    document_type: str
    title: str
    version: str
    source_path: Path
    sha256: str
    pdf_page: int
    markdown_path: Path
    text: str
    content_type: str
    warnings: tuple[str, ...]
    verified: bool
    identity: DocumentIdentity | None = None
    source_ref: str | None = None
    locator: SourceLocator | None = None
