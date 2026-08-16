"""Application path discovery and runtime directory boundaries."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_SOURCE_LIBRARY_DIRS = (Path("docs/ESP32-C3"), Path("docs/ESP32-S3"))


def _source_library_data_root(repo_root: Path) -> Path | None:
    repo = repo_root.resolve()
    for candidate in (repo, *repo.parents):
        if all((candidate / relative).is_dir() for relative in _SOURCE_LIBRARY_DIRS):
            return (candidate / "docs" / "esp-hardware-knowledge-data").resolve()
    return None


@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    data_root: Path
    corpus_dir: Path
    index_path: Path
    renders_dir: Path
    cache_dir: Path
    logs_dir: Path

    @classmethod
    def from_roots(
        cls,
        repo_root: Path,
        local_app_data: Path | None,
        *,
        data_root: Path | None = None,
    ) -> AppPaths:
        repo = repo_root.resolve()
        if data_root is not None:
            data = data_root.resolve()
        elif local_app_data is not None:
            data = local_app_data.resolve() / "esp-hardware-knowledge"
        else:
            raise RuntimeError("LOCALAPPDATA or ESPDOCS_DATA_ROOT is required")
        return cls(
            repo_root=repo,
            data_root=data,
            corpus_dir=data / "corpus",
            index_path=data / "index" / "espdocs.sqlite3",
            renders_dir=data / "renders",
            cache_dir=data / "cache",
            logs_dir=data / "logs",
        )

    @classmethod
    def discover(cls) -> AppPaths:
        repo_override = os.environ.get("ESPDOCS_REPO_ROOT")
        repo_root = Path(repo_override) if repo_override else Path(__file__).resolve().parents[2]
        explicit_data_root = os.environ.get("ESPDOCS_DATA_ROOT")
        library_data_root = _source_library_data_root(repo_root)
        local_app_data = os.environ.get("LOCALAPPDATA")
        return cls.from_roots(
            repo_root=repo_root,
            local_app_data=Path(local_app_data) if local_app_data else None,
            data_root=Path(explicit_data_root) if explicit_data_root else library_data_root,
        )

    def ensure_runtime_dirs(self) -> None:
        for directory in (
            self.corpus_dir,
            self.index_path.parent,
            self.renders_dir,
            self.cache_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
