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
