"""Golden source-location evaluation and runtime verification."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Sequence
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from espdocs.config import AppPaths
from espdocs.markdown import local_image_reference_errors
from espdocs.retrieval import SearchService


class EvaluationError(RuntimeError):
    """Raised when an evaluation set or runtime cannot be verified."""


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    query: str
    chip: str
    document_type: str | None
    expected_filename: str
    page_min: int
    page_max: int
    requires_source_check: bool


class SearchHit(Protocol):
    chip: str
    source_path: Path
    pdf_page: int
    requires_source_check: bool


@dataclass(frozen=True)
class CaseDiagnostic:
    case_id: str
    source_hit: bool
    chip_leakage: bool
    source_check_ok: bool


@dataclass(frozen=True)
class EvaluationReport:
    total_cases: int
    source_hits: int
    top5_recall: float
    chip_leakage: int
    source_check_failures: int
    sufficient_cases: bool
    passed: bool
    cases: tuple[CaseDiagnostic, ...]


def _parse_case(payload: dict[str, Any], line_no: int) -> GoldenCase:
    try:
        page_range = payload["pdf_pages"]
        if (
            not isinstance(page_range, list)
            or len(page_range) != 2
            or not all(isinstance(value, int) for value in page_range)
            or page_range[0] < 1
            or page_range[1] < page_range[0]
        ):
            raise ValueError("pdf_pages must be an increasing [first, last] pair")
        return GoldenCase(
            case_id=str(payload["id"]),
            query=str(payload["query"]),
            chip=str(payload["chip"]),
            document_type=(
                str(payload["document_type"]) if payload.get("document_type") is not None else None
            ),
            expected_filename=str(payload["expected_filename"]),
            page_min=page_range[0],
            page_max=page_range[1],
            requires_source_check=bool(payload["requires_source_check"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise EvaluationError(
            f"Invalid golden evaluation record on line {line_no}: {error}"
        ) from error


def load_cases(path: Path) -> list[GoldenCase]:
    cases: list[GoldenCase] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise EvaluationError(
                    f"Invalid golden evaluation JSON on line {line_no}: {error}"
                ) from error
            if not isinstance(payload, dict):
                raise EvaluationError(f"Invalid golden evaluation record on line {line_no}")
            cases.append(_parse_case(payload, line_no))
    if len({case.case_id for case in cases}) != len(cases):
        raise EvaluationError("Golden evaluation case IDs must be unique")
    return cases


def evaluate(
    cases: Sequence[GoldenCase],
    *,
    search: Callable[[GoldenCase], Sequence[SearchHit]],
) -> EvaluationReport:
    diagnostics: list[CaseDiagnostic] = []
    source_hits = 0
    chip_leakage = 0
    source_check_failures = 0
    for case in cases:
        results = list(search(case))[:5]
        leaked = any(result.chip != case.chip for result in results)
        correct = [
            result
            for result in results
            if result.chip == case.chip
            and result.source_path.name.casefold() == case.expected_filename.casefold()
            and case.page_min <= result.pdf_page <= case.page_max
        ]
        source_hit = bool(correct)
        source_check_ok = not correct or any(
            result.requires_source_check == case.requires_source_check for result in correct
        )
        source_hits += int(source_hit)
        chip_leakage += int(leaked)
        source_check_failures += int(not source_check_ok)
        diagnostics.append(CaseDiagnostic(case.case_id, source_hit, leaked, source_check_ok))
    total = len(cases)
    recall = source_hits / total if total else 0.0
    sufficient = total >= 20
    passed = sufficient and recall >= 0.95 and chip_leakage == 0 and source_check_failures == 0
    return EvaluationReport(
        total_cases=total,
        source_hits=source_hits,
        top5_recall=recall,
        chip_leakage=chip_leakage,
        source_check_failures=source_check_failures,
        sufficient_cases=sufficient,
        passed=passed,
        cases=tuple(diagnostics),
    )


def _corpus_health(corpus_dir: Path) -> tuple[int, int, list[str]]:
    documents = 0
    pages = 0
    errors: list[str] = []
    if not corpus_dir.is_dir():
        return documents, pages, [f"missing_corpus:{corpus_dir}"]
    for document_dir in sorted(corpus_dir.iterdir()):
        if not document_dir.is_dir() or document_dir.name.startswith("."):
            continue
        documents += 1
        try:
            manifest = json.loads((document_dir / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("validation", {}).get("passed") is not True:
                errors.append(f"unvalidated:{document_dir.name}")
            for page in manifest["pages"]:
                pages += 1
                path = (document_dir / page["markdown_path"]).resolve()
                if not path.is_relative_to(document_dir.resolve()) or not path.is_file():
                    errors.append(f"missing_page:{document_dir.name}:{page['pdf_page']}")
                    continue
                for image_error in local_image_reference_errors(path, document_dir):
                    errors.append(
                        f"{image_error.reason}_image:{document_dir.name}:"
                        f"{page['pdf_page']}:{image_error.reference}"
                    )
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            errors.append(f"invalid_manifest:{document_dir.name}:{error}")
    return documents, pages, errors


def verify_runtime(paths: AppPaths) -> tuple[dict[str, Any], bool]:
    if not paths.index_path.is_file():
        raise EvaluationError(f"Search index does not exist: {paths.index_path}")
    with closing(sqlite3.connect(paths.index_path)) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        index_documents = connection.execute("SELECT count(*) FROM documents").fetchone()[0]
        index_pages = connection.execute("SELECT count(*) FROM pages").fetchone()[0]
    corpus_documents, corpus_pages, corpus_errors = _corpus_health(paths.corpus_dir)
    cases = load_cases(paths.repo_root / "evaluation" / "golden.jsonl")
    service = SearchService(paths.index_path, paths.repo_root / "config" / "aliases.toml")
    report = evaluate(
        cases,
        search=lambda case: service.search(
            case.query,
            chip=case.chip,
            document_type=case.document_type,
            limit=5,
        ),
    )
    corpus_matches_index = corpus_documents == index_documents and corpus_pages == index_pages
    passed = integrity == "ok" and not corpus_errors and corpus_matches_index and report.passed
    payload = {
        "schema_version": 1,
        "passed": passed,
        "index": {
            "integrity": integrity,
            "documents": index_documents,
            "pages": index_pages,
        },
        "corpus": {
            "documents": corpus_documents,
            "pages": corpus_pages,
            "matches_index": corpus_matches_index,
            "errors": corpus_errors,
        },
        "evaluation": asdict(report),
    }
    return payload, passed
