import pytest

from espdocs.evidence import classify_evidence


@pytest.mark.parametrize(
    "query",
    [
        "GPIO_STRAP_REG 复位值",
        "VDD_SPI 电压",
        "eFuse 烧录",
        "启动引脚配置",
        "SPI 时序",
    ],
)
def test_high_risk_queries_require_original_pdf(query: str) -> None:
    decision = classify_evidence(
        query=query,
        content_type="text",
        warnings=(),
        version="1.4",
        verified=True,
    )

    assert decision.requires_source_check is True
    assert decision.grade == "C"
    assert decision.reasons


@pytest.mark.parametrize("content_type", ["table", "picture"])
def test_visual_content_requires_original_pdf(content_type: str) -> None:
    decision = classify_evidence(
        query="GPIO 功能",
        content_type=content_type,
        warnings=(),
        version="1.4",
        verified=True,
    )

    assert decision.requires_source_check is True


def test_unknown_version_requires_original_pdf() -> None:
    decision = classify_evidence(
        query="UART 简介",
        content_type="text",
        warnings=("unknown_document_version",),
        version="unknown",
        verified=True,
    )

    assert decision.requires_source_check is True
    assert "unknown_document_version" in decision.reasons


def test_verified_low_risk_text_is_grade_b() -> None:
    decision = classify_evidence(
        query="UART 简介",
        content_type="text",
        warnings=(),
        version="1.4",
        verified=True,
    )

    assert decision.grade == "B"
    assert decision.requires_source_check is False
