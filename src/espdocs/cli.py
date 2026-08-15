"""Stable command-line and JSON boundary for local ESP documentation."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict, is_dataclass
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

import typer

from espdocs.catalog import discover_documents, load_source_roots
from espdocs.config import AppPaths
from espdocs.gpu import gpu_status
from espdocs.index import build_index, supports_trigram
from espdocs.ingest import ingest_document
from espdocs.retrieval import RetrievalError, SearchService, get_indexed_page
from espdocs.source import SourceError, render_source_page

app = typer.Typer(no_args_is_help=True, help="Local, source-traceable ESP documentation")


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _emit(payload: dict[str, Any], json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(_jsonable(payload), ensure_ascii=True))
    else:
        typer.echo(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2))


def _fail(error_type: str, message: str, code: int, json_output: bool) -> None:
    payload = {"schema_version": 1, "error": {"type": error_type, "message": message}}
    _emit(payload, json_output)
    raise typer.Exit(code)


def _paths() -> AppPaths:
    return AppPaths.discover()


def _search_service(paths: AppPaths) -> SearchService:
    return SearchService(paths.index_path, paths.repo_root / "config" / "aliases.toml")


@app.command()
def ingest(
    dry_run: bool = typer.Option(False, "--dry-run", help="List work without conversion"),
    document: str | None = typer.Option(None, "--document", help="Import one exact filename"),
    json_output: bool = typer.Option(False, "--json", help="Emit versioned JSON"),
) -> None:
    """Discover and transactionally import approved ESP PDFs."""
    try:
        paths = _paths()
        roots = load_source_roots(paths.repo_root / "config" / "documents.toml", paths.repo_root)
        records = discover_documents(roots)
        if document is not None:
            records = [record for record in records if record.source_path.name == document]
            if not records:
                _fail("DocumentNotFound", document, 2, json_output)
        if dry_run:
            _emit(
                {
                    "schema_version": 1,
                    "documents": [
                        {
                            "filename": record.source_path.name,
                            "chip": record.chip,
                            "document_type": record.document_type,
                            "sha256": record.sha256,
                            "pdf_pages": record.page_count,
                            "action": "would_ingest",
                        }
                        for record in records
                    ],
                },
                json_output,
            )
            return
        paths.ensure_runtime_dirs()
        results = [ingest_document(record, None, paths.corpus_dir) for record in records]
        index_result = build_index(paths.corpus_dir, paths.index_path)
        _emit(
            {
                "schema_version": 1,
                "documents": results,
                "index": index_result,
            },
            json_output,
        )
    except typer.Exit:
        raise
    except Exception as error:  # noqa: BLE001 - stable CLI boundary
        _fail(type(error).__name__, str(error), 5, json_output)


@app.command()
def search(
    query: str = typer.Argument(..., help="Keyword, phrase, register, or signal"),
    chip: str | None = typer.Option(None, "--chip"),
    document_type: str | None = typer.Option(None, "--type"),
    limit: int = typer.Option(10, "--limit"),
    json_output: bool = typer.Option(False, "--json", help="Emit versioned JSON"),
) -> None:
    """Search candidate evidence without generating an answer."""
    try:
        results = _search_service(_paths()).search(
            query, chip=chip, document_type=document_type, limit=limit
        )
        _emit({"schema_version": 1, "query": query, "results": results}, json_output)
    except RetrievalError as error:
        missing_index = "index does not exist" in str(error)
        _fail(
            "IndexUnavailable" if missing_index else type(error).__name__,
            str(error),
            3 if missing_index else 2,
            json_output,
        )


@app.command()
def show(
    page_id: int = typer.Argument(..., help="Indexed page ID returned by search"),
    json_output: bool = typer.Option(False, "--json", help="Emit versioned JSON"),
) -> None:
    """Show a complete indexed page and its source metadata."""
    try:
        page = get_indexed_page(_paths().index_path, page_id)
        _emit({"schema_version": 1, "page": page}, json_output)
    except RetrievalError as error:
        missing_index = "index does not exist" in str(error)
        _fail(
            "IndexUnavailable" if missing_index else type(error).__name__,
            str(error),
            3 if missing_index else 2,
            json_output,
        )


@app.command("source")
def source_command(
    page_id: int = typer.Argument(..., help="Indexed page ID returned by search"),
    json_output: bool = typer.Option(False, "--json", help="Emit versioned JSON"),
) -> None:
    """Verify and render the authoritative original PDF page."""
    try:
        paths = _paths()
        page = get_indexed_page(paths.index_path, page_id)
        view = render_source_page(
            page.source_path,
            page.sha256,
            page_no=page.pdf_page,
            output_dir=paths.renders_dir,
        )
        _emit({"schema_version": 1, "source": view}, json_output)
    except RetrievalError as error:
        missing_index = "index does not exist" in str(error)
        _fail(
            "IndexUnavailable" if missing_index else type(error).__name__,
            str(error),
            3 if missing_index else 2,
            json_output,
        )
    except SourceError as error:
        _fail(type(error).__name__, str(error), 4, json_output)


@app.command()
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Emit versioned JSON"),
) -> None:
    """Check dependencies, sources, runtime paths, and index state."""
    try:
        paths = _paths()
        roots = load_source_roots(paths.repo_root / "config" / "documents.toml", paths.repo_root)
        connection = sqlite3.connect(":memory:")
        try:
            trigram = supports_trigram(connection)
        finally:
            connection.close()
        gpu = gpu_status()
        requested_device = os.environ.get("ESPDOCS_DEVICE", "cuda").casefold()
        if requested_device == "cpu":
            selected_device = "cpu"
            accelerator_healthy = True
        elif requested_device in {"cuda", "auto"} and gpu.ready:
            selected_device = "cuda"
            accelerator_healthy = True
        else:
            selected_device = "unavailable"
            accelerator_healthy = False
        components = {
            "python": __import__("platform").python_version(),
            "docling": package_version("docling"),
            "rapidocr": package_version("rapidocr"),
            "pymupdf": package_version("pymupdf"),
            "sqlite": sqlite3.sqlite_version,
            "fts5_trigram": trigram,
        }
        payload = {
            "schema_version": 1,
            "healthy": (
                trigram and accelerator_healthy and all(root.path.is_dir() for root in roots)
            ),
            "components": components,
            "gpu": {
                "requested_device": requested_device,
                "selected_device": selected_device,
                "ready": gpu.ready,
                "torch_cuda": gpu.torch_cuda,
                "torch_cuda_version": gpu.torch_cuda_version,
                "onnx_cuda": gpu.onnx_cuda,
                "onnx_providers": gpu.onnx_providers,
                "device_name": gpu.device_name,
                "memory_mib": gpu.memory_mib,
            },
            "sources": {
                "configured": len(roots),
                "roots": [root.path for root in roots],
            },
            "runtime": {
                "data_root": paths.data_root,
                "index_path": paths.index_path,
                "index_exists": paths.index_path.is_file(),
            },
        }
        _emit(payload, json_output)
    except Exception as error:  # noqa: BLE001 - stable CLI boundary
        _fail(type(error).__name__, str(error), 3, json_output)


@app.command()
def verify(
    json_output: bool = typer.Option(False, "--json", help="Emit versioned JSON"),
) -> None:
    """Run corpus integrity and golden retrieval evaluation."""
    try:
        from espdocs.evaluate import verify_runtime

        payload, passed = verify_runtime(_paths())
        _emit(payload, json_output)
        if not passed:
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as error:  # noqa: BLE001 - stable CLI boundary
        _fail(type(error).__name__, str(error), 3, json_output)
