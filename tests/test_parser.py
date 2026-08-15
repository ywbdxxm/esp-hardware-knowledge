from pathlib import Path
from types import SimpleNamespace

import pytest
from docling.datamodel.accelerator_options import AcceleratorDevice

import espdocs.parser as parser_module
from espdocs.models import DocumentRecord
from espdocs.parser import PageExportError, convert_document, export_pages


class FakeDoclingDocument:
    def __init__(
        self,
        missing_page: int | None = None,
        allowed_pages: range | None = None,
    ) -> None:
        self.missing_page = missing_page
        self.allowed_pages = allowed_pages
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
        allowed = self.allowed_pages is None or page_no in self.allowed_pages
        if allowed and page_no != self.missing_page:
            filename.write_text(f"# Page {page_no}\n\n中文内容 {page_no}\n", encoding="utf-8")

    def save_as_json(self, filename: Path, **_kwargs) -> None:
        filename.write_text('{"schema_name":"DoclingDocument"}', encoding="utf-8")


class FakeConverter:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, bool, tuple[int, int]]] = []

    def convert(
        self,
        source: Path,
        *,
        raises_on_error: bool,
        page_range: tuple[int, int],
    ):
        self.calls.append((source, raises_on_error, page_range))
        first, last = page_range
        return SimpleNamespace(document=FakeDoclingDocument(allowed_pages=range(first, last + 1)))


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
    converter = FakeConverter()

    pages = convert_document(record, tmp_path / "output", converter=converter)

    assert converter.calls == [(source, True, (1, 1))]
    assert [page.page_no for page in pages] == [1]
    assert (tmp_path / "output" / "docling" / "batch-0001-0001.json").is_file()


def test_convert_document_batches_large_pdf(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"test")
    record = DocumentRecord(
        document_id="abc123",
        chip="esp32-c3",
        document_type="technical_reference_manual",
        title="test",
        version="unknown",
        source_path=source,
        sha256="1" * 64,
        page_count=5,
        size_bytes=4,
        modified_ns=0,
    )
    converter = FakeConverter()

    pages = convert_document(record, tmp_path / "output", converter=converter, batch_size=2)

    assert [call[2] for call in converter.calls] == [(1, 2), (3, 4), (5, 5)]
    assert [page.page_no for page in pages] == [1, 2, 3, 4, 5]


def test_convert_document_resumes_completed_batches(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"test")
    record = DocumentRecord(
        document_id="abc123",
        chip="esp32-c3",
        document_type="technical_reference_manual",
        title="test",
        version="unknown",
        source_path=source,
        sha256="2" * 64,
        page_count=3,
        size_bytes=4,
        modified_ns=0,
    )
    output = tmp_path / "output"
    convert_document(record, output, converter=FakeConverter(), batch_size=2)
    resumed_converter = FakeConverter()

    pages = convert_document(record, output, converter=resumed_converter, batch_size=2)

    assert resumed_converter.calls == []
    assert [page.page_no for page in pages] == [1, 2, 3]


def test_build_converter_uses_resolved_accelerator(monkeypatch) -> None:
    calls: list[bool] = []

    def resolve() -> AcceleratorDevice:
        calls.append(True)
        return AcceleratorDevice.CUDA

    monkeypatch.setattr(parser_module, "resolve_accelerator_device", resolve)

    parser_module.build_converter()

    assert calls == [True]
