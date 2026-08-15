"""Filtered deterministic retrieval over the local FTS5 index."""

from __future__ import annotations

import json
import sqlite3
import tomllib
import unicodedata
from contextlib import closing
from pathlib import Path

from espdocs.evidence import classify_evidence
from espdocs.models import SearchResult


class RetrievalError(RuntimeError):
    """Raised for invalid queries, filters, or unavailable indexes."""


_CHIPS = {"esp32-c3", "esp32-s3"}
_DOCUMENT_TYPES = {
    "technical_reference_manual",
    "datasheet",
    "module_datasheet",
    "hardware_design_guidelines",
}


def normalize_query(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def load_aliases(path: Path) -> dict[str, tuple[str, ...]]:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    aliases: dict[str, tuple[str, ...]] = {}
    for group in config.get("groups", []):
        terms = tuple(str(term) for term in group["terms"])
        for term in terms:
            aliases[normalize_query(term).casefold()] = terms
    return aliases


def _quote_fts(term: str) -> str:
    return f'"{term.replace(chr(34), chr(34) * 2)}"'


def _query_terms(query: str, aliases: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    terms = [query]
    folded = query.casefold()
    for alias, group in aliases.items():
        if alias in folded:
            terms.extend(group)
    return tuple(dict.fromkeys(normalize_query(term) for term in terms if normalize_query(term)))


class SearchService:
    def __init__(self, database_path: Path, aliases_path: Path) -> None:
        self.database_path = database_path
        self.aliases = load_aliases(aliases_path)

    def search(
        self,
        query: str,
        *,
        chip: str | None = None,
        document_type: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        normalized = normalize_query(query)
        if not normalized:
            raise RetrievalError("Search query cannot be empty")
        if chip is not None and chip not in _CHIPS:
            raise RetrievalError(f"Unsupported chip filter: {chip}")
        if document_type is not None and document_type not in _DOCUMENT_TYPES:
            raise RetrievalError(f"Unsupported document type filter: {document_type}")
        if not 1 <= limit <= 50:
            raise RetrievalError("Search limit must be between 1 and 50")
        if not self.database_path.is_file():
            raise RetrievalError(f"Search index does not exist: {self.database_path}")

        terms = _query_terms(normalized, self.aliases)
        fts_terms = [term for term in terms if len(term) >= 3]
        filters: list[str] = []
        filter_values: list[object] = []
        if chip is not None:
            filters.append("d.chip = ?")
            filter_values.append(chip)
        if document_type is not None:
            filters.append("d.document_type = ?")
            filter_values.append(document_type)
        filter_sql = "" if not filters else " AND " + " AND ".join(filters)

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            if fts_terms:
                match_expression = " OR ".join(_quote_fts(term) for term in fts_terms)
                rows = connection.execute(
                    f"""
                    SELECT p.id AS page_id, p.document_id, p.pdf_page, p.markdown_path,
                           p.text, p.content_type, p.warnings_json, p.verified,
                           d.chip, d.document_type, d.title, d.version,
                           d.source_path, d.sha256,
                           snippet(pages_fts, 0, '[[', ']]', '...', 32) AS snippet,
                           bm25(pages_fts) AS rank
                    FROM pages_fts
                    JOIN pages p ON p.id = pages_fts.rowid
                    JOIN documents d ON d.document_id = p.document_id
                    WHERE pages_fts MATCH ?{filter_sql}
                    ORDER BY rank, d.document_id, p.pdf_page
                    LIMIT ?
                    """,
                    [match_expression, *filter_values, min(limit * 5, 250)],
                ).fetchall()
            else:
                rows = connection.execute(
                    f"""
                    SELECT p.id AS page_id, p.document_id, p.pdf_page, p.markdown_path,
                           p.text, p.content_type, p.warnings_json, p.verified,
                           d.chip, d.document_type, d.title, d.version,
                           d.source_path, d.sha256, p.text AS snippet, 0.0 AS rank
                    FROM pages p
                    JOIN documents d ON d.document_id = p.document_id
                    WHERE instr(lower(p.text), lower(?)) > 0{filter_sql}
                    ORDER BY d.document_id, p.pdf_page
                    LIMIT ?
                    """,
                    [normalized, *filter_values, limit],
                ).fetchall()

        ranked: list[tuple[int, float, SearchResult]] = []
        for row in rows:
            text = str(row["text"])
            matched_terms = tuple(term for term in terms if term.casefold() in text.casefold())
            warnings = tuple(json.loads(row["warnings_json"]))
            evidence = classify_evidence(
                query=normalized,
                content_type=str(row["content_type"]),
                warnings=warnings,
                version=str(row["version"]),
                verified=bool(row["verified"]),
            )
            exact = int(normalized.casefold() in text.casefold())
            rank = float(row["rank"])
            score = float(exact * 10 + len(matched_terms) - rank)
            result = SearchResult(
                page_id=int(row["page_id"]),
                document_id=str(row["document_id"]),
                chip=str(row["chip"]),
                document_type=str(row["document_type"]),
                title=str(row["title"]),
                version=str(row["version"]),
                source_path=Path(row["source_path"]),
                sha256=str(row["sha256"]),
                pdf_page=int(row["pdf_page"]),
                markdown_path=Path(row["markdown_path"]),
                snippet=str(row["snippet"]),
                content_type=str(row["content_type"]),
                warnings=warnings,
                verified=bool(row["verified"]),
                score=score,
                matched_terms=matched_terms,
                evidence_grade=evidence.grade,
                requires_source_check=evidence.requires_source_check,
                source_check_reasons=evidence.reasons,
            )
            ranked.append((exact, score, result))
        ranked.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                item[2].document_id,
                item[2].pdf_page,
            )
        )
        return [item[2] for item in ranked[:limit]]
