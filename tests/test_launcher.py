import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = (
    REPO_ROOT
    / "skills"
    / "hardware-document-research"
    / "scripts"
    / "invoke-espdocs.ps1"
)


def make_repository(path: Path) -> Path:
    (path / "src" / "espdocs").mkdir(parents=True)
    (path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    return path.resolve()


def powershell(
    arguments: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def resolver_command(
    *,
    process_root: Path | None,
    user_root: Path | None,
    start_directory: Path,
) -> str:
    def literal(path: Path | None) -> str:
        if path is None:
            return "$null"
        return "'" + str(path).replace("'", "''") + "'"

    launcher = str(LAUNCHER).replace("'", "''")
    return (
        f"$ErrorActionPreference='Stop'; . '{launcher}'; "
        "try { "
        "Resolve-EspdocsProjectRoot "
        f"-ProcessRoot {literal(process_root)} "
        f"-UserRoot {literal(user_root)} "
        f"-StartDirectory {literal(start_directory)} | ConvertTo-Json -Compress "
        "} catch { [Console]::Error.WriteLine($_.Exception.Message); exit 3 }"
    )


@pytest.mark.parametrize("invocation", ["file", "call"])
def test_launcher_invokes_locked_project_from_unrelated_directory(
    tmp_path: Path, invocation: str
) -> None:
    repository = make_repository(tmp_path / "knowledge repo")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    record = tmp_path / "arguments.json"
    (fake_bin / "uv.cmd").write_text(
        """
@echo off
> "%ESPDOCS_TEST_RECORD%" echo %~1
>> "%ESPDOCS_TEST_RECORD%" echo %~2
>> "%ESPDOCS_TEST_RECORD%" echo %~3
>> "%ESPDOCS_TEST_RECORD%" echo %~4
>> "%ESPDOCS_TEST_RECORD%" echo %~5
>> "%ESPDOCS_TEST_RECORD%" echo %~6
>> "%ESPDOCS_TEST_RECORD%" echo %~7
echo {"invoked":true}
exit /b 0
""".strip(),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["ESP_HARDWARE_KNOWLEDGE_ROOT"] = str(repository)
    env["ESPDOCS_TEST_RECORD"] = str(record)

    if invocation == "file":
        arguments = ["-File", str(LAUNCHER), "doctor", "--json"]
    else:
        launcher = str(LAUNCHER).replace("'", "''")
        arguments = ["-Command", f"& '{launcher}' doctor --json"]
    result = powershell(arguments, cwd=unrelated, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == '{"invoked":true}'
    assert record.read_text(encoding="utf-8-sig").splitlines() == [
        "run",
        "--locked",
        "--project",
        str(repository),
        "espdocs",
        "doctor",
        "--json",
    ]


def test_resolver_prefers_process_root_over_user_root(tmp_path: Path) -> None:
    process_root = make_repository(tmp_path / "process")
    user_root = make_repository(tmp_path / "user")

    result = powershell(
        [
            "-Command",
            resolver_command(
                process_root=process_root,
                user_root=user_root,
                start_directory=tmp_path,
            ),
        ],
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert Path(json.loads(result.stdout)).resolve() == process_root


def test_resolver_rejects_incomplete_explicit_root(tmp_path: Path) -> None:
    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()

    result = powershell(
        [
            "-Command",
            resolver_command(
                process_root=incomplete,
                user_root=None,
                start_directory=tmp_path,
            ),
        ],
        cwd=tmp_path,
    )

    assert result.returncode == 3
    assert json.loads(result.stderr)["error"]["type"] == "IncompleteProjectRoot"


def test_resolver_rejects_missing_bounded_candidate(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    result = powershell(
        [
            "-Command",
            resolver_command(
                process_root=None,
                user_root=None,
                start_directory=empty,
            ),
        ],
        cwd=empty,
    )

    assert result.returncode == 3
    assert json.loads(result.stderr)["error"]["type"] == "ProjectRootNotFound"


def test_resolver_rejects_multiple_bounded_candidates(tmp_path: Path) -> None:
    outer = make_repository(tmp_path / "outer")
    inner = make_repository(outer / "nested")
    start = inner / "project"
    start.mkdir()

    result = powershell(
        [
            "-Command",
            resolver_command(
                process_root=None,
                user_root=None,
                start_directory=start,
            ),
        ],
        cwd=start,
    )

    assert result.returncode == 3
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "AmbiguousProjectRoot"
    assert {Path(path).resolve() for path in payload["error"]["candidates"]} == {
        outer,
        inner,
    }
