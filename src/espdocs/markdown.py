"""Portable local image references in generated Markdown."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_EXTERNAL_PREFIXES = ("http://", "https://", "data:", "#")


@dataclass(frozen=True)
class ImageReferenceError:
    reason: str
    reference: str


def _target_token(reference: str) -> str:
    cleaned = reference.strip()
    if cleaned.startswith("<") and ">" in cleaned:
        return cleaned[1 : cleaned.index(">")]
    return cleaned.strip("\"'").split(maxsplit=1)[0]


def _local_target(markdown_path: Path, reference: str) -> tuple[str, Path] | None:
    token = _target_token(reference)
    if token.casefold().startswith(_EXTERNAL_PREFIXES):
        return None
    path = Path(token)
    target = path if path.is_absolute() else markdown_path.parent / path
    return token, target.resolve()


def normalize_local_image_references(markdown_path: Path, document_root: Path) -> None:
    """Rewrite in-document absolute image targets to relocation-safe relative paths."""
    text = markdown_path.read_text(encoding="utf-8")
    root = document_root.resolve()

    def replace(match: re.Match[str]) -> str:
        reference = match.group(1)
        resolved = _local_target(markdown_path, reference)
        if resolved is None:
            return match.group(0)
        token, target = resolved
        if not target.is_relative_to(root):
            raise ValueError(f"image reference escapes document directory: {reference}")
        if not target.is_file():
            raise ValueError(f"image reference target does not exist: {reference}")
        relative = os.path.relpath(target, markdown_path.parent).replace(os.sep, "/")
        return match.group(0).replace(token, relative, 1)

    normalized = _IMAGE_PATTERN.sub(replace, text)
    if normalized != text:
        markdown_path.write_text(normalized, encoding="utf-8")


def local_image_reference_errors(
    markdown_path: Path,
    document_root: Path,
) -> list[ImageReferenceError]:
    """Return missing or escaping local image targets without mutating Markdown."""
    text = markdown_path.read_text(encoding="utf-8")
    root = document_root.resolve()
    errors: list[ImageReferenceError] = []
    for raw_reference in _IMAGE_PATTERN.findall(text):
        resolved = _local_target(markdown_path, raw_reference)
        if resolved is None:
            continue
        token, target = resolved
        if not target.is_relative_to(root):
            errors.append(ImageReferenceError("escaping", token))
        elif not target.is_file():
            errors.append(ImageReferenceError("missing", token))
    return errors
