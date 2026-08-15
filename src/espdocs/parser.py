"""Docling construction and physical-page-preserving corpus export."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, cast

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    OcrMode,
    PdfPipelineOptions,
    RapidOcrOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode

from espdocs.models import DocumentRecord, PageRecord


class PageExportError(RuntimeError):
    """Raised when Docling output cannot be mapped to every physical PDF page."""


class MarkdownExportDocument(Protocol):
    def save_as_markdown(
        self,
        filename: Path,
        *,
        artifacts_dir: Path,
        page_no: int,
        image_mode: ImageRefMode,
        **kwargs: object,
    ) -> None: ...

    def save_as_json(
        self,
        filename: Path,
        *,
        artifacts_dir: Path,
        image_mode: ImageRefMode,
    ) -> None: ...


class ConverterResult(Protocol):
    document: MarkdownExportDocument


class Converter(Protocol):
    def convert(self, source: Path, *, raises_on_error: bool) -> ConverterResult: ...


def build_converter() -> DocumentConverter:
    pipeline = PdfPipelineOptions(
        accelerator_options=AcceleratorOptions(num_threads=4, device=AcceleratorDevice.CPU),
        enable_remote_services=False,
        allow_external_plugins=False,
        do_ocr=True,
        ocr_options=RapidOcrOptions(
            mode=OcrMode.FULL_PAGE,
            lang=["chinese"],
            backend="onnxruntime",
        ),
        do_table_structure=True,
        generate_picture_images=True,
        images_scale=2.0,
    )
    pipeline.table_structure_options.mode = TableFormerMode.ACCURATE
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)},
    )


def _content_type(markdown: str) -> str:
    if any(line.lstrip().startswith("|") for line in markdown.splitlines()):
        return "table"
    if "![" in markdown or "<!-- image -->" in markdown:
        return "picture"
    return "text"


def export_pages(
    document: MarkdownExportDocument,
    output_dir: Path,
    *,
    document_id: str,
    expected_pages: int,
) -> list[PageRecord]:
    if expected_pages <= 0:
        raise PageExportError("Expected PDF page count must be positive")
    pages_dir = output_dir / "pages"
    assets_root = output_dir / "assets"
    pages_dir.mkdir(parents=True, exist_ok=True)
    assets_root.mkdir(parents=True, exist_ok=True)
    pages: list[PageRecord] = []
    for page_no in range(1, expected_pages + 1):
        markdown_path = pages_dir / f"{page_no:04d}.md"
        document.save_as_markdown(
            markdown_path,
            artifacts_dir=assets_root / f"{page_no:04d}",
            page_no=page_no,
            image_mode=ImageRefMode.REFERENCED,
        )
        if not markdown_path.is_file():
            raise PageExportError(f"Docling did not export expected PDF page {page_no}")
        text = markdown_path.read_text(encoding="utf-8")
        pages.append(
            PageRecord(
                document_id=document_id,
                page_no=page_no,
                markdown_path=markdown_path,
                text=text,
                content_type=_content_type(text),
                warnings=(),
                verified=False,
            )
        )
    return pages


def convert_document(
    record: DocumentRecord,
    output_dir: Path,
    *,
    converter: Converter | None = None,
) -> list[PageRecord]:
    active_converter = converter or cast(Converter, build_converter())
    result = active_converter.convert(record.source_path, raises_on_error=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    result.document.save_as_json(
        output_dir / "docling.json",
        artifacts_dir=output_dir / "docling-artifacts",
        image_mode=ImageRefMode.REFERENCED,
    )
    return export_pages(
        result.document,
        output_dir,
        document_id=record.document_id,
        expected_pages=record.page_count,
    )
