from pathlib import Path
from types import SimpleNamespace

import pytest

from espdocs.models import DocumentRecord
from espdocs.parser import PageExportError, convert_document, export_pages


class FakeDoclingDocument:
    def __init__(self, missing_page: int | None = None) -> None:
        self.missing_page = missing_page
        self.saved_page_numbers: list[int] = []
        self.image_modes: list[str] = []

    def save_as_markdown(
        self,
        filename: Path,
        *,
        artifacts_dir: Path,
        page_no: int,
        image_mode,
        **_kwargs,
    ) -> None:
        self.saved_page_numbers.append(page_no)
        self.image_modes.append(image_mode.value)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        if page_no != self.missing_page:
            filename.write_text(f"# Page {page_no}\n\n中文内容 {page_no}\n", encoding="utf-8")

    def save_as_json(self, filename: Path, **_kwargs) -> None:
        filename.write_text('{"schema_name":"DoclingDocument"}', encoding="utf-8")


class FakeConverter:
    def __init__(self, document: FakeDoclingDocument) -> None:
        self.document = document
        self.calls: list[tuple[Path, bool]] = []

    def convert(self, source: Path, *, raises_on_error: bool):
        self.calls.append((source, raises_on_error))
        return SimpleNamespace(document=self.document)


def test_export_pages_preserves_physical_page_numbers(tmp_path: Path) -> None:
    document = FakeDoclingDocument()

    pages = export_pages(document, tmp_path, document_id="abc123", expected_pages=2)

    assert [page.page_no for page in pages] == [1, 2]
    assert [page.markdown_path.name for page in pages] == ["0001.md", "0002.md"]
    assert (tmp_path / "pages" / "0001.md").read_text(encoding="utf-8").startswith("# Page 1")
    assert document.saved_page_numbers == [1, 2]
    assert document.image_modes == ["referenced", "referenced"]


def test_export_pages_fails_when_docling_omits_expected_page(tmp_path: Path) -> None:
    document = FakeDoclingDocument(missing_page=2)

    with pytest.raises(PageExportError, match="page 2"):
        export_pages(document, tmp_path, document_id="abc123", expected_pages=2)


def test_export_pages_rejects_non_positive_page_count(tmp_path: Path) -> None:
    with pytest.raises(PageExportError, match="positive"):
        export_pages(FakeDoclingDocument(), tmp_path, document_id="abc123", expected_pages=0)


def test_convert_document_is_fail_fast_and_saves_docling_json(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"test")
    record = DocumentRecord(
        document_id="abc123",
        chip="esp32-c3",
        document_type="datasheet",
        title="test",
        version="unknown",
        source_path=source,
        sha256="0" * 64,
        page_count=1,
        size_bytes=4,
        modified_ns=0,
    )
    converter = FakeConverter(FakeDoclingDocument())

    pages = convert_document(record, tmp_path / "output", converter=converter)

    assert converter.calls == [(source, True)]
    assert [page.page_no for page in pages] == [1]
    assert (tmp_path / "output" / "docling.json").is_file()
