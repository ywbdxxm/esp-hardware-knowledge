from pathlib import Path

from espdocs.config import AppPaths


def test_runtime_data_stays_outside_repository(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    local = tmp_path / "LocalAppData"

    paths = AppPaths.from_roots(repo_root=repo, local_app_data=local)

    assert paths.data_root == local / "esp-hardware-knowledge"
    assert paths.corpus_dir == paths.data_root / "corpus"
    assert paths.index_path == paths.data_root / "index" / "espdocs.sqlite3"
    assert repo not in paths.data_root.parents


def test_discover_uses_local_app_data(monkeypatch, tmp_path: Path) -> None:
    local = tmp_path / "LocalAppData"
    repo = tmp_path / "repo"
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("ESPDOCS_REPO_ROOT", str(repo))

    paths = AppPaths.discover()

    assert paths.repo_root == repo.resolve()
    assert paths.data_root == local.resolve() / "esp-hardware-knowledge"


def test_ensure_runtime_dirs_creates_only_runtime_tree(tmp_path: Path) -> None:
    paths = AppPaths.from_roots(
        repo_root=tmp_path / "repo",
        local_app_data=tmp_path / "LocalAppData",
    )

    paths.ensure_runtime_dirs()

    assert paths.corpus_dir.is_dir()
    assert paths.index_path.parent.is_dir()
    assert paths.renders_dir.is_dir()
    assert paths.cache_dir.is_dir()
    assert paths.logs_dir.is_dir()
    assert not paths.repo_root.exists()
