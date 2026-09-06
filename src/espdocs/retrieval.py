"""Filtered deterministic retrieval over schema-v1 and schema-v2 indexes."""

from __future__ import annotations

import json
import re
import sqlite3
import tomllib
import unicodedata
from contextlib import closing
from pathlib import Path

from espdocs.evidence import classify_evidence
from espdocs.models import (
    DocumentIdentity,
    DocumentInventory,
    IndexedPage,
    SearchResult,
    SourceLocator,
)


class RetrievalError(RuntimeError):
    """Raised for invalid queries, filters, or unavailable indexes."""


class InvalidFilterValue(RetrievalError):
    """Raised when a filter cannot be normalized into a safe identity value."""


_FILTER_PATTERN = re.compile(r"[a-z0-9][a-z0-9._+-]*", re.IGNORECASE)


def normalize_query(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _normalize_filter(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    if not _FILTER_PATTERN.fullmatch(normalized):
        raise InvalidFilterValue(f"Invalid {name} filter: {value}")
    return normalized


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


def _has_identity_schema(connection: sqlite3.Connection) -> bool:
    columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(documents)")}
    return {
        "vendor",
        "family",
        "parts_json",
        "document_revision",
        "source_ref",
    } <= columns


def _identity_projection(schema_v2: bool) -> str:
    if schema_v2:
        return """
            d.vendor, d.family, d.parts_json, d.variant, d.language,
            d.document_revision, d.source_format, d.source_ref,
            p.locator_kind, p.physical_page, p.anchor
        """
    return """
        NULL AS vendor, NULL AS family, NULL AS parts_json, NULL AS variant,
        NULL AS language, NULL AS document_revision, NULL AS source_format,
        NULL AS source_ref, NULL AS locator_kind, NULL AS physical_page,
        NULL AS anchor
    """


def _identity_from_row(row: sqlite3.Row) -> DocumentIdentity:
    parts_json = row["parts_json"]
    parts = tuple(json.loads(parts_json)) if parts_json else (str(row["chip"]),)
    return DocumentIdentity(
        vendor=str(row["vendor"] or "espressif"),
        family=str(row["family"] or "esp32"),
        parts=parts,
        variant=str(row["variant"]) if row["variant"] is not None else None,
        document_type=str(row["document_type"]),
        language=str(row["language"] or "unknown"),
        document_revision=str(row["document_revision"] or row["version"]),
    )


def _locator_from_row(row: sqlite3.Row) -> SourceLocator:
    physical_page = row["physical_page"]
    return SourceLocator(
        source_format=str(row["source_format"] or "pdf"),
        kind=str(row["locator_kind"] or "pdf_page"),
        physical_page=int(physical_page) if physical_page is not None else int(row["pdf_page"]),
        anchor=str(row["anchor"]) if row["anchor"] is not None else None,
    )


def _source_ref_from_row(row: sqlite3.Row) -> str:
    return str(row["source_ref"] or f"sha256:{row['sha256']}")


class SearchService:
    def __init__(self, database_path: Path, aliases_path: Path) -> None:
        self.database_path = database_path
        self.aliases = load_aliases(aliases_path)

    def _require_index(self) -> None:
        if not self.database_path.is_file():
            raise RetrievalError(f"Search index does not exist: {self.database_path}")

    def inventory(self) -> DocumentInventory:
        self._require_index()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            schema_v2 = _has_identity_schema(connection)
            if schema_v2:
                rows = connection.execute(
                    """
                    SELECT chip, document_type, version, vendor, family, parts_json,
                           variant, language, document_revision
                    FROM documents
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT chip, document_type, version FROM documents"
                ).fetchall()

        vendors: set[str] = set()
        families: set[str] = set()
        parts: set[str] = set()
        variants: set[str] = set()
        document_types: set[str] = set()
        languages: set[str] = set()
        revisions: set[str] = set()
        for row in rows:
            vendors.add(str(row["vendor"]) if schema_v2 else "espressif")
            families.add(str(row["family"]) if schema_v2 else "esp32")
            parts.update(
                json.loads(row["parts_json"]) if schema_v2 else [str(row["chip"])]
            )
            if schema_v2 and row["variant"] is not None:
                variants.add(str(row["variant"]))
            document_types.add(str(row["document_type"]))
            languages.add(str(row["language"]) if schema_v2 else "unknown")
            revisions.add(str(row["document_revision"]) if schema_v2 else str(row["version"]))
        sort_values = lambda values: tuple(sorted(values, key=str.casefold))
        return DocumentInventory(
            vendors=sort_values(vendors),
            families=sort_values(families),
            parts=sort_values(parts),
            variants=sort_values(variants),
            document_types=sort_values(document_types),
            languages=sort_values(languages),
            revisions=sort_values(revisions),
            document_count=len(rows),
        )

    def search(
        self,
        query: str,
        *,
        chip: str | None = None,
        vendor: str | None = None,
        family: str | None = None,
        part: str | None = None,
        variant: str | None = None,
        document_type: str | None = None,
        language: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        normalized = normalize_query(query)
        if not normalized:
            raise RetrievalError("Search query cannot be empty")
        normalized_filters = {
            "chip": _normalize_filter("chip", chip),
            "vendor": _normalize_filter("vendor", vendor),
            "family": _normalize_filter("family", family),
            "part": _normalize_filter("part", part),
            "variant": _normalize_filter("variant", variant),
            "document_type": _normalize_filter("document type", document_type),
            "language": _normalize_filter("language", language),
        }
        if (
            normalized_filters["chip"] is not None
            and normalized_filters["part"] is not None
            and normalized_filters["chip"] != normalized_filters["part"]
        ):
            raise InvalidFilterValue("Contradictory chip and part filters")
        if not 1 <= limit <= 50:
            raise RetrievalError("Search limit must be between 1 and 50")
        self._require_index()

        terms = _query_terms(normalized, self.aliases)
        fts_terms = [term for term in terms if len(term) >= 3]
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            schema_v2 = _has_identity_schema(connection)
            if not schema_v2:
                if normalized_filters["vendor"] not in {None, "espressif"}:
                    return []
                if normalized_filters["family"] not in {None, "esp32"}:
                    return []
                if normalized_filters["variant"] is not None:
                    return []
                if normalized_filters["language"] not in {None, "unknown"}:
                    return []

            filters: list[str] = []
            filter_values: list[object] = []
            column_filters = {
                "chip": "d.chip = ?",
                "vendor": "d.vendor = ?",
                "family": "d.family = ?",
                "variant": "d.variant = ?",
                "document_type": "d.document_type = ?",
                "language": "d.language = ?",
            }
            for name, expression in column_filters.items():
                value = normalized_filters[name]
                if value is not None and (schema_v2 or name in {"chip", "document_type"}):
                    filters.append(expression)
                    filter_values.append(value)
            part_filter = normalized_filters["part"]
            if part_filter is not None:
                filters.append(
                    "EXISTS (SELECT 1 FROM json_each(d.parts_json) WHERE value = ?)"
                    if schema_v2
                    else "d.chip = ?"
                )
                filter_values.append(part_filter)
            filter_sql = "" if not filters else " AND " + " AND ".join(filters)
            projection = _identity_projection(schema_v2)

            if fts_terms:
                match_expression = " OR ".join(_quote_fts(term) for term in fts_terms)
                rows = connection.execute(
                    f"""
                    SELECT p.id AS page_id, p.document_id, p.pdf_page, p.markdown_path,
                           p.text, p.content_type, p.warnings_json, p.verified,
                           d.chip, d.document_type, d.title, d.version,
                           d.source_path, d.sha256, {projection},
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
                           d.source_path, d.sha256, {projection},
                           p.text AS snippet, 0.0 AS rank
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
            identity = _identity_from_row(row)
            evidence = classify_evidence(
                query=normalized,
                content_type=str(row["content_type"]),
                warnings=warnings,
                version=identity.document_revision,
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
                identity=identity,
                source_ref=_source_ref_from_row(row),
                locator=_locator_from_row(row),
            )
            ranked.append((exact, score, result))
        ranked.sort(
            key=lambda item: (-item[0], -item[1], item[2].document_id, item[2].pdf_page)
        )
        return [item[2] for item in ranked[:limit]]


def get_indexed_page(database_path: Path, page_id: int) -> IndexedPage:
    if not database_path.is_file():
        raise RetrievalError(f"Search index does not exist: {database_path}")
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        projection = _identity_projection(_has_identity_schema(connection))
        row = connection.execute(
            f"""
            SELECT p.id AS page_id, p.document_id, p.pdf_page, p.markdown_path,
                   p.text, p.content_type, p.warnings_json, p.verified,
                   d.chip, d.document_type, d.title, d.version, d.source_path, d.sha256,
                   {projection}
            FROM pages p
            JOIN documents d ON d.document_id = p.document_id
            WHERE p.id = ?
            """,
            (page_id,),
        ).fetchone()
    if row is None:
        raise RetrievalError(f"Indexed page ID does not exist: {page_id}")
    return IndexedPage(
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
        text=str(row["text"]),
        content_type=str(row["content_type"]),
        warnings=tuple(json.loads(row["warnings_json"])),
        verified=bool(row["verified"]),
        identity=_identity_from_row(row),
        source_ref=_source_ref_from_row(row),
        locator=_locator_from_row(row),
    )
