"""Docling construction and physical-page-preserving corpus export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, cast

from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    OcrMode,
    PdfPipelineOptions,
    RapidOcrOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode

from espdocs.gpu import resolve_accelerator_device
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
    def convert(
        self,
        source: Path,
        *,
        raises_on_error: bool,
        page_range: tuple[int, int],
    ) -> ConverterResult: ...


def build_converter() -> DocumentConverter:
    device = resolve_accelerator_device()
    pipeline = PdfPipelineOptions(
        accelerator_options=AcceleratorOptions(num_threads=4, device=device),
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
    first_page: int = 1,
) -> list[PageRecord]:
    if expected_pages <= 0:
        raise PageExportError("Expected PDF page count must be positive")
    pages_dir = output_dir / "pages"
    assets_root = output_dir / "assets"
    pages_dir.mkdir(parents=True, exist_ok=True)
    assets_root.mkdir(parents=True, exist_ok=True)
    pages: list[PageRecord] = []
    last_page = first_page + expected_pages - 1
    for page_no in range(first_page, last_page + 1):
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


def _marker_path(output_dir: Path, first_page: int, last_page: int) -> Path:
    return output_dir / "batches" / f"batch-{first_page:04d}-{last_page:04d}.complete.json"


def _load_completed_batch(
    record: DocumentRecord,
    output_dir: Path,
    first_page: int,
    last_page: int,
) -> list[PageRecord] | None:
    marker = _marker_path(output_dir, first_page, last_page)
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if payload != {
        "sha256": record.sha256,
        "first_page": first_page,
        "last_page": last_page,
    }:
        return None
    pages: list[PageRecord] = []
    for page_no in range(first_page, last_page + 1):
        markdown_path = output_dir / "pages" / f"{page_no:04d}.md"
        if not markdown_path.is_file():
            return None
        text = markdown_path.read_text(encoding="utf-8")
        pages.append(
            PageRecord(
                document_id=record.document_id,
                page_no=page_no,
                markdown_path=markdown_path,
                text=text,
                content_type=_content_type(text),
                warnings=(),
                verified=False,
            )
        )
    return pages


def _mark_batch_complete(
    record: DocumentRecord,
    output_dir: Path,
    first_page: int,
    last_page: int,
) -> None:
    marker = _marker_path(output_dir, first_page, last_page)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "sha256": record.sha256,
                "first_page": first_page,
                "last_page": last_page,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def convert_document(
    record: DocumentRecord,
    output_dir: Path,
    *,
    converter: Converter | None = None,
    batch_size: int = 32,
) -> list[PageRecord]:
    if batch_size < 1:
        raise ValueError("Docling batch size must be positive")
    active_converter = converter or cast(Converter, build_converter())
    output_dir.mkdir(parents=True, exist_ok=True)
    pages: list[PageRecord] = []
    for first_page in range(1, record.page_count + 1, batch_size):
        last_page = min(first_page + batch_size - 1, record.page_count)
        completed = _load_completed_batch(record, output_dir, first_page, last_page)
        if completed is not None:
            pages.extend(completed)
            continue
        result = active_converter.convert(
            record.source_path,
            raises_on_error=True,
            page_range=(first_page, last_page),
        )
        batch_name = f"batch-{first_page:04d}-{last_page:04d}"
        (output_dir / "docling").mkdir(parents=True, exist_ok=True)
        result.document.save_as_json(
            output_dir / "docling" / f"{batch_name}.json",
            artifacts_dir=output_dir / "docling-artifacts" / batch_name,
            image_mode=ImageRefMode.REFERENCED,
        )
        batch_pages = export_pages(
            result.document,
            output_dir,
            document_id=record.document_id,
            expected_pages=last_page - first_page + 1,
            first_page=first_page,
        )
        _mark_batch_complete(record, output_dir, first_page, last_page)
        pages.extend(batch_pages)
    return pages
