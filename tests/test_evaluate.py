import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from espdocs.evaluate import EvaluationError, GoldenCase, evaluate, load_cases


def make_cases(count: int = 20) -> list[GoldenCase]:
    return [
        GoldenCase(
            case_id=f"case-{index:02d}",
            query=f"query {index}",
            chip="esp32-c3",
            document_type="technical_reference_manual",
            expected_filename="esp32-c3_technical_reference_manual_cn.pdf",
            page_min=index + 1,
            page_max=index + 1,
            requires_source_check=index % 2 == 0,
        )
        for index in range(count)
    ]


def hit(case: GoldenCase, *, chip: str | None = None, source_check: bool | None = None):
    return SimpleNamespace(
        chip=chip or case.chip,
        source_path=Path(case.expected_filename),
        pdf_page=case.page_min,
        requires_source_check=(
            case.requires_source_check if source_check is None else source_check
        ),
    )


def test_evaluation_accepts_95_percent_top_five_recall() -> None:
    cases = make_cases()

    report = evaluate(
        cases,
        search=lambda case: [] if case.case_id == "case-19" else [hit(case)],
    )

    assert report.top5_recall == 0.95
    assert report.passed is True


def test_evaluation_rejects_chip_leakage_even_with_correct_hit() -> None:
    cases = make_cases()

    report = evaluate(cases, search=lambda case: [hit(case), hit(case, chip="esp32-s3")])

    assert report.chip_leakage == 20
    assert report.passed is False


def test_evaluation_rejects_missing_source_check_flag() -> None:
    cases = make_cases()

    report = evaluate(cases, search=lambda case: [hit(case, source_check=False)])

    assert report.source_check_failures == 10
    assert report.passed is False


def test_evaluation_requires_at_least_twenty_verified_cases() -> None:
    cases = make_cases(19)

    report = evaluate(cases, search=lambda case: [hit(case)])

    assert report.sufficient_cases is False
    assert report.passed is False


def test_load_cases_rejects_malformed_record(tmp_path: Path) -> None:
    path = tmp_path / "golden.jsonl"
    path.write_text(json.dumps({"id": "missing-fields"}), encoding="utf-8")

    with pytest.raises(EvaluationError, match="line 1"):
        load_cases(path)


def test_load_cases_reads_page_range(tmp_path: Path) -> None:
    path = tmp_path / "golden.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "uart-overview",
                "query": "UART 简介",
                "chip": "esp32-c3",
                "document_type": "technical_reference_manual",
                "expected_filename": "trm.pdf",
                "pdf_pages": [10, 12],
                "requires_source_check": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    case = load_cases(path)[0]

    assert (case.page_min, case.page_max) == (10, 12)
