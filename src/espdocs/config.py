"""Application path discovery and runtime directory boundaries."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
    def from_roots(cls, repo_root: Path, local_app_data: Path) -> AppPaths:
        repo = repo_root.resolve()
        data = local_app_data.resolve() / "esp-hardware-knowledge"
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
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA is required to locate espdocs runtime data")
        repo_override = os.environ.get("ESPDOCS_REPO_ROOT")
        repo_root = Path(repo_override) if repo_override else Path(__file__).resolve().parents[2]
        return cls.from_roots(repo_root=repo_root, local_app_data=Path(local_app_data))

    def ensure_runtime_dirs(self) -> None:
        for directory in (
            self.corpus_dir,
            self.index_path.parent,
            self.renders_dir,
            self.cache_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
