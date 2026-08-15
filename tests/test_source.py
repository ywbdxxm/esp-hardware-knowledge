from pathlib import Path

import pymupdf
import pytest

from espdocs.catalog import sha256_file
from espdocs.source import (
    SourceChangedError,
    SourcePageError,
    render_source_page,
)


def write_pdf(path: Path, pages: int = 2) -> Path:
    document = pymupdf.open()
    for index in range(pages):
        page = document.new_page(width=300, height=200)
        page.insert_text((40, 50), f"source page {index + 1}")
    document.save(path)
    document.close()
    return path


def test_source_refuses_changed_pdf(tmp_path: Path) -> None:
    source = write_pdf(tmp_path / "source.pdf")
    expected = sha256_file(source)
    source.write_bytes(source.read_bytes() + b"changed")

    with pytest.raises(SourceChangedError, match="SHA-256"):
        render_source_page(source, expected, page_no=1, output_dir=tmp_path / "renders")


@pytest.mark.parametrize("page_no", [0, 3])
def test_source_rejects_out_of_range_pages(tmp_path: Path, page_no: int) -> None:
    source = write_pdf(tmp_path / "source.pdf", pages=2)

    with pytest.raises(SourcePageError, match="page"):
        render_source_page(
            source,
            sha256_file(source),
            page_no=page_no,
            output_dir=tmp_path / "renders",
        )


def test_source_reports_missing_pdf(tmp_path: Path) -> None:
    with pytest.raises(SourceChangedError, match="does not exist"):
        render_source_page(
            tmp_path / "missing.pdf",
            "a" * 64,
            page_no=1,
            output_dir=tmp_path / "renders",
        )


def test_source_renders_verified_page_with_adjacent_pages(tmp_path: Path) -> None:
    source = write_pdf(tmp_path / "source.pdf", pages=3)
    digest = sha256_file(source)

    view = render_source_page(
        source,
        digest,
        page_no=2,
        output_dir=tmp_path / "renders",
    )

    assert view.source_path == source.resolve()
    assert view.pdf_page == 2
    assert view.previous_page == 1
    assert view.next_page == 3
    assert view.evidence_grade == "A"
    assert view.verified_sha256 == digest
    assert view.render_path.name == f"{digest[:16]}-p0002-200dpi.png"
    with pymupdf.open(view.render_path) as image:
        assert image[0].rect.width > 300
        assert image[0].rect.height > 200
