import json
from pathlib import Path

import pytest

from espdocs.index import build_index
from espdocs.retrieval import RetrievalError, SearchService


def seed_document(
    corpus: Path,
    *,
    document_id: str,
    chip: str,
    text: str,
    page_no: int,
    version: str = "1.4",
) -> None:
    directory = corpus / document_id
    page_path = directory / "pages" / f"{page_no:04d}.md"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(text, encoding="utf-8")
    payload = {
        "schema_version": 1,
        "document": {
            "document_id": document_id,
            "chip": chip,
            "document_type": "technical_reference_manual",
            "title": f"{chip} TRM",
            "version": version,
            "source_path": str((corpus.parent / f"{chip}.pdf").resolve()),
            "sha256": ("a" if chip == "esp32-c3" else "b") * 64,
            "page_count": 100,
            "size_bytes": 100,
            "modified_ns": 1,
        },
        "pages": [
            {
                "pdf_page": page_no,
                "markdown_path": str(page_path.relative_to(directory)),
                "content_type": "text",
                "warnings": [] if version != "unknown" else ["unknown_document_version"],
                "verified": True,
            }
        ],
        "warnings": [],
        "validation": {"passed": True},
    }
    (directory / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


@pytest.fixture
def search_service(tmp_path: Path) -> SearchService:
    corpus = tmp_path / "corpus"
    seed_document(
        corpus,
        document_id="c3-uart",
        chip="esp32-c3",
        text="UART0 是通用异步串行收发器。GPIO_STRAP_REG 保存启动配置。",
        page_no=17,
    )
    seed_document(
        corpus,
        document_id="s3-uart",
        chip="esp32-s3",
        text="ESP32-S3 的 UART 控制器说明。",
        page_no=23,
        version="1.8",
    )
    database = tmp_path / "espdocs.sqlite3"
    build_index(corpus, database)
    aliases = tmp_path / "aliases.toml"
    aliases.write_text(
        '[[groups]]\nterms=["UART", "通用异步收发器", "通用异步串行收发器"]\n',
        encoding="utf-8",
    )
    return SearchService(database, aliases)


def test_chip_filter_never_silently_mixes_s3(search_service: SearchService) -> None:
    results = search_service.search("UART", chip="esp32-c3")

    assert results
    assert {result.chip for result in results} == {"esp32-c3"}


def test_reviewed_alias_expands_chinese_query(search_service: SearchService) -> None:
    results = search_service.search("通用异步收发器", chip="esp32-c3")

    assert results[0].pdf_page == 17
    assert "UART" in results[0].matched_terms


def test_exact_register_term_is_preserved(search_service: SearchService) -> None:
    results = search_service.search("GPIO_STRAP_REG", chip="esp32-c3")

    assert results[0].pdf_page == 17
    assert results[0].requires_source_check is True


def test_short_query_uses_literal_fallback(search_service: SearchService) -> None:
    results = search_service.search("S3", chip="esp32-s3")

    assert results[0].chip == "esp32-s3"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chip": "esp8266"},
        {"document_type": "blog"},
        {"limit": 0},
        {"limit": 51},
    ],
)
def test_invalid_search_filters_are_rejected(search_service: SearchService, kwargs: dict) -> None:
    with pytest.raises(RetrievalError):
        search_service.search("UART", **kwargs)


def test_unknown_version_result_requires_source_check(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    seed_document(
        corpus,
        document_id="unknown-version",
        chip="esp32-c3",
        text="UART 简介",
        page_no=5,
        version="unknown",
    )
    database = tmp_path / "espdocs.sqlite3"
    build_index(corpus, database)
    aliases = tmp_path / "aliases.toml"
    aliases.write_text("", encoding="utf-8")

    result = SearchService(database, aliases).search("UART")[0]

    assert result.requires_source_check is True
    assert "unknown_document_version" in result.source_check_reasons
