"""Typed records shared across the ESP document pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceRoot:
    chip: str
    path: Path


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


@dataclass(frozen=True)
class SourceView:
    source_path: Path
    pdf_page: int
    render_path: Path
    verified_sha256: str
    evidence_grade: str
    previous_page: int | None
    next_page: int | None
