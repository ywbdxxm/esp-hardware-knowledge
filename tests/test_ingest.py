from pathlib import Path

import pytest

from espdocs.ingest import IngestError, ingest_document, load_manifest
from espdocs.models import DocumentRecord, PageRecord


def make_record(tmp_path: Path, *, pages: int = 2, digest: str = "a" * 64) -> DocumentRecord:
    source = tmp_path / "esp32-c3_datasheet_cn.pdf"
    source.write_bytes(b"source")
    return DocumentRecord(
        document_id=digest[:16],
        chip="esp32-c3",
        document_type="datasheet",
        title="ESP32-C3 Datasheet",
        version="unknown",
        source_path=source,
        sha256=digest,
        page_count=pages,
        size_bytes=6,
        modified_ns=1,
    )


class FakeParser:
    def __init__(
        self,
        *,
        page_texts: list[str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.page_texts = page_texts or ["版本：1.4\n正文", "第二页"]
        self.error = error
        self.calls = 0

    def __call__(self, record: DocumentRecord, output_dir: Path) -> list[PageRecord]:
        self.calls += 1
        if self.error:
            raise self.error
        pages_dir = output_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        pages: list[PageRecord] = []
        for page_no, text in enumerate(self.page_texts, start=1):
            path = pages_dir / f"{page_no:04d}.md"
            path.write_text(text, encoding="utf-8")
            pages.append(
                PageRecord(
                    document_id=record.document_id,
                    page_no=page_no,
                    markdown_path=path,
                    text=text,
                    content_type="text",
                    warnings=(),
                    verified=False,
                )
            )
        return pages


def test_failed_ingest_preserves_active_document(tmp_path: Path) -> None:
    record = make_record(tmp_path)
    corpus = tmp_path / "corpus"
    active = corpus / record.document_id
    active.mkdir(parents=True)
    (active / "marker.txt").write_text("known-good", encoding="utf-8")

    with pytest.raises(IngestError, match="conversion failed"):
        ingest_document(record, FakeParser(error=ValueError("bad OCR")), corpus)

    assert (active / "marker.txt").read_text(encoding="utf-8") == "known-good"


def test_successful_ingest_promotes_validated_manifest(tmp_path: Path) -> None:
    record = make_record(tmp_path)
    corpus = tmp_path / "corpus"

    result = ingest_document(record, FakeParser(), corpus)
    manifest = load_manifest(result.active_dir)

    assert result.status == "imported"
    assert manifest["document"]["sha256"] == record.sha256
    assert manifest["document"]["version"] == "1.4"
    assert manifest["validation"]["passed"] is True
    assert [page["pdf_page"] for page in manifest["pages"]] == [1, 2]
    assert not list((corpus / ".staging").glob(f"{record.document_id}-*"))


def test_matching_hash_skips_conversion(tmp_path: Path) -> None:
    record = make_record(tmp_path)
    corpus = tmp_path / "corpus"
    ingest_document(record, FakeParser(), corpus)
    parser = FakeParser()

    result = ingest_document(record, parser, corpus)

    assert result.status == "unchanged"
    assert parser.calls == 0


def test_page_count_mismatch_rejects_promotion(tmp_path: Path) -> None:
    record = make_record(tmp_path, pages=2)

    with pytest.raises(IngestError, match="page count"):
        ingest_document(record, FakeParser(page_texts=["only one"]), tmp_path / "corpus")


def test_image_reference_cannot_escape_document_directory(tmp_path: Path) -> None:
    record = make_record(tmp_path, pages=1)
    parser = FakeParser(page_texts=["![bad](../../outside.png)"])

    with pytest.raises(IngestError, match="escapes"):
        ingest_document(record, parser, tmp_path / "corpus")


def test_unknown_version_is_explicit_and_warned(tmp_path: Path) -> None:
    record = make_record(tmp_path, pages=1)

    result = ingest_document(record, FakeParser(page_texts=["没有版本声明"]), tmp_path / "corpus")
    manifest = load_manifest(result.active_dir)

    assert manifest["document"]["version"] == "unknown"
    assert "unknown_document_version" in manifest["warnings"]


def test_ingest_reuses_hash_bound_staging_for_interrupted_run(tmp_path: Path) -> None:
    record = make_record(tmp_path, pages=1)
    corpus = tmp_path / "corpus"
    expected_stage = corpus / ".staging" / f"{record.document_id}-{record.sha256[:16]}"
    expected_stage.mkdir(parents=True)
    (expected_stage / "resume.marker").write_text("completed batch", encoding="utf-8")

    class ResumingParser(FakeParser):
        def __call__(self, current: DocumentRecord, output_dir: Path) -> list[PageRecord]:
            assert output_dir == expected_stage
            assert (output_dir / "resume.marker").is_file()
            return super().__call__(current, output_dir)

    result = ingest_document(record, ResumingParser(page_texts=["版本：1.4"]), corpus)

    assert result.status == "imported"
