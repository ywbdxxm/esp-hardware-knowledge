from pathlib import Path

import pymupdf
import pytest

from espdocs.catalog import (
    UnclassifiedDocumentError,
    classify_document,
    discover_documents,
    load_source_roots,
)
from espdocs.models import SourceRoot


def write_pdf(path: Path, pages: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open()
    for index in range(pages):
        page = document.new_page()
        page.insert_text((72, 72), f"page {index + 1}")
    document.save(path)
    document.close()
    return path


def test_discovery_excludes_unconfigured_sibling(tmp_path: Path) -> None:
    c3 = tmp_path / "ESP32-C3"
    mic = tmp_path / "MIC"
    target = write_pdf(c3 / "esp32-c3_datasheet_cn.pdf", pages=2)
    write_pdf(mic / "unrelated.pdf")

    records = discover_documents([SourceRoot(chip="esp32-c3", path=c3)])

    assert [record.source_path for record in records] == [target.resolve()]
    assert records[0].page_count == 2
    assert records[0].document_type == "datasheet"
    assert len(records[0].sha256) == 64
    assert records[0].document_id == records[0].sha256[:16]


def test_discovery_is_stably_sorted(tmp_path: Path) -> None:
    root = tmp_path / "ESP32-S3"
    write_pdf(root / "esp32-s3-wroom-1_wroom-1u_datasheet_cn.pdf")
    write_pdf(root / "esp32-s3_datasheet_cn.pdf")

    records = discover_documents([SourceRoot(chip="esp32-s3", path=root)])

    assert [record.source_path.name for record in records] == [
        "esp32-s3-wroom-1_wroom-1u_datasheet_cn.pdf",
        "esp32-s3_datasheet_cn.pdf",
    ]


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("esp32-c3_technical_reference_manual_cn.pdf", "technical_reference_manual"),
        ("esp-hardware-design-guidelines-zh_CN-master-esp32c3.pdf", "hardware_design_guidelines"),
        ("esp32-c3-mini-1_datasheet_cn.pdf", "module_datasheet"),
        ("esp32-c3-wroom-02_datasheet_cn.pdf", "module_datasheet"),
        ("esp32-c3_datasheet_cn.pdf", "datasheet"),
    ],
)
def test_classifies_supported_document_names(filename: str, expected: str) -> None:
    assert classify_document(filename) == expected


def test_unmatched_pdf_is_reported_instead_of_guessed(tmp_path: Path) -> None:
    root = tmp_path / "ESP32-C3"
    write_pdf(root / "mystery.pdf")

    with pytest.raises(UnclassifiedDocumentError, match="mystery.pdf"):
        discover_documents([SourceRoot(chip="esp32-c3", path=root)])


def test_source_config_finds_shared_hardware_root_from_worktree(tmp_path: Path) -> None:
    hardware_root = tmp_path / "AI-HRADWARE"
    repo = hardware_root / "esp-hardware-knowledge" / ".worktrees" / "feature"
    c3 = hardware_root / "docs" / "ESP32-C3"
    s3 = hardware_root / "docs" / "ESP32-S3"
    c3.mkdir(parents=True)
    s3.mkdir(parents=True)
    config = repo / "config" / "documents.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[[sources]]\nchip="esp32-c3"\npath="docs/ESP32-C3"\n'
        '[[sources]]\nchip="esp32-s3"\npath="docs/ESP32-S3"\n',
        encoding="utf-8",
    )

    roots = load_source_roots(config, repo_root=repo)

    assert roots == [
        SourceRoot(chip="esp32-c3", path=c3.resolve()),
        SourceRoot(chip="esp32-s3", path=s3.resolve()),
    ]
