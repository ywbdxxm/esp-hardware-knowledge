"""Hash-verified access to authoritative original PDF pages."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pymupdf

from espdocs.catalog import sha256_file
from espdocs.models import SourceView


class SourceError(RuntimeError):
    """Base error for authoritative source access."""


class SourceChangedError(SourceError):
    """Raised when the indexed source no longer exists or its hash changed."""


class SourcePageError(SourceError):
    """Raised when a requested physical PDF page is invalid."""


def render_source_page(
    source_path: Path,
    expected_sha256: str,
    *,
    page_no: int,
    output_dir: Path,
) -> SourceView:
    source = source_path.resolve()
    if not source.is_file():
        raise SourceChangedError(f"Indexed source PDF does not exist: {source}")
    actual_sha256 = sha256_file(source)
    if actual_sha256 != expected_sha256:
        raise SourceChangedError(
            f"Source PDF SHA-256 changed: expected {expected_sha256}, got {actual_sha256}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    render_path = output_dir / f"{actual_sha256[:16]}-p{page_no:04d}-200dpi.png"
    with pymupdf.open(source) as document:
        if page_no < 1 or page_no > document.page_count:
            raise SourcePageError(
                f"PDF page {page_no} is outside the valid range 1-{document.page_count}"
            )
        if not render_path.is_file():
            page = document.load_page(page_no - 1)
            png_bytes = page.get_pixmap(dpi=200, alpha=False).tobytes("png")
            temporary_path = render_path.with_name(f".{render_path.name}.{uuid4().hex}.tmp")
            try:
                temporary_path.write_bytes(png_bytes)
                temporary_path.replace(render_path)
            finally:
                temporary_path.unlink(missing_ok=True)
        previous_page = page_no - 1 if page_no > 1 else None
        next_page = page_no + 1 if page_no < document.page_count else None

    return SourceView(
        source_path=source,
        pdf_page=page_no,
        render_path=render_path,
        verified_sha256=actual_sha256,
        evidence_grade="A",
        previous_page=previous_page,
        next_page=next_page,
    )
