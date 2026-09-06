import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "install-codex-assets.ps1"
MANAGED_SKILLS = (
    "hardware-document-research",
    "esp32-ai-hardware-engineering",
    "docling-local-document-engineering",
)


@dataclass(frozen=True)
class DeploymentFixture:
    repository: Path
    installer: Path
    codex_home: Path
    validator: Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_fixture(tmp_path: Path) -> DeploymentFixture:
    repository = tmp_path / "repository"
    scripts = repository / "scripts"
    scripts.mkdir(parents=True)
    installer = scripts / INSTALLER.name
    shutil.copy2(INSTALLER, installer)
    (repository / "codex").mkdir()
    (repository / "codex" / "AGENTS.md").write_text("global-v1\n", encoding="utf-8")
    for name in MANAGED_SKILLS:
        skill = repository / "skills" / name
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"{name}-v1\n", encoding="utf-8")
        (skill / "references" / "detail.md").write_text(f"{name}-detail\n", encoding="utf-8")
    validator = tmp_path / "validator.py"
    validator.write_text("raise SystemExit(0)\n", encoding="utf-8")
    return DeploymentFixture(
        repository=repository,
        installer=installer,
        codex_home=tmp_path / "codex-home",
        validator=validator,
    )


def run_installer(
    fixture: DeploymentFixture,
    *switches: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(fixture.installer),
            "-CodexHome",
            str(fixture.codex_home),
            "-ValidatorPath",
            str(fixture.validator),
            *switches,
        ],
        cwd=fixture.repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_check_is_read_only_when_managed_assets_are_absent(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)

    result = run_installer(fixture, "-Check")

    assert result.returncode != 0
    assert not fixture.codex_home.exists()


def test_first_install_deploys_complete_managed_set_and_manifest(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    unmanaged = fixture.codex_home / "skills" / "user-owned" / "SKILL.md"
    unmanaged.parent.mkdir(parents=True)
    unmanaged.write_bytes(b"user-owned\x00content")
    unmanaged_digest = sha256(unmanaged)

    install = run_installer(fixture)
    check = run_installer(fixture, "-Check")

    assert install.returncode == 0, install.stderr
    assert check.returncode == 0, check.stderr
    assert (fixture.codex_home / "AGENTS.md").read_text(encoding="utf-8") == "global-v1\n"
    for name in MANAGED_SKILLS:
        assert (fixture.codex_home / "skills" / name / "SKILL.md").is_file()
        assert (fixture.codex_home / "skills" / name / "references" / "detail.md").is_file()
    manifest_path = (
        fixture.codex_home / "managed" / "esp-hardware-knowledge-assets.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert list(manifest["files"]) == sorted(manifest["files"])
    assert "AGENTS.md" in manifest["files"]
    assert "skills/hardware-document-research/SKILL.md" in manifest["files"]
    assert sha256(unmanaged) == unmanaged_digest


def test_safe_update_uses_last_manifest_and_preserves_unmanaged_skill(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    assert run_installer(fixture).returncode == 0
    unmanaged = fixture.codex_home / "skills" / "user-owned" / "SKILL.md"
    unmanaged.parent.mkdir(parents=True)
    unmanaged.write_bytes(b"keep-me")
    unmanaged_digest = sha256(unmanaged)
    canonical = fixture.repository / "skills" / MANAGED_SKILLS[0] / "SKILL.md"
    canonical.write_text(f"{MANAGED_SKILLS[0]}-v2\n", encoding="utf-8")

    update = run_installer(fixture)

    assert update.returncode == 0, update.stderr
    assert (
        fixture.codex_home / "skills" / MANAGED_SKILLS[0] / "SKILL.md"
    ).read_text(encoding="utf-8") == f"{MANAGED_SKILLS[0]}-v2\n"
    assert sha256(unmanaged) == unmanaged_digest


def test_destination_drift_blocks_update_until_force(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    assert run_installer(fixture).returncode == 0
    deployed = fixture.codex_home / "skills" / MANAGED_SKILLS[0] / "SKILL.md"
    deployed.write_text("local-user-edit\n", encoding="utf-8")

    rejected = run_installer(fixture)

    assert rejected.returncode != 0
    assert deployed.read_text(encoding="utf-8") == "local-user-edit\n"
    assert "skills/hardware-document-research/SKILL.md" in rejected.stderr

    forced = run_installer(fixture, "-Force")

    assert forced.returncode == 0, forced.stderr
    assert deployed.read_text(encoding="utf-8") == f"{MANAGED_SKILLS[0]}-v1\n"
    assert "skills/hardware-document-research/SKILL.md" in forced.stdout


def test_staging_failure_preserves_previous_assets_and_manifest(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    assert run_installer(fixture).returncode == 0
    agents = fixture.codex_home / "AGENTS.md"
    manifest = fixture.codex_home / "managed" / "esp-hardware-knowledge-assets.json"
    before_agents = agents.read_bytes()
    before_manifest = manifest.read_bytes()
    deployed_hashes = {
        name: sha256(fixture.codex_home / "skills" / name / "SKILL.md")
        for name in MANAGED_SKILLS
    }
    (fixture.repository / "codex" / "AGENTS.md").write_text("global-v2\n", encoding="utf-8")
    fixture.validator.write_text(
        """
import os
from pathlib import Path
import sys

counter = Path(os.environ["DEPLOY_VALIDATOR_COUNTER"])
count = int(counter.read_text() if counter.exists() else "0") + 1
counter.write_text(str(count))
if count == 3:
    Path(os.environ["DEPLOY_BREAK_SOURCE"]).unlink()
raise SystemExit(0)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    counter = tmp_path / "validator-count.txt"
    broken_source = (
        fixture.repository
        / "skills"
        / "hardware-document-research"
        / "references"
        / "detail.md"
    )
    environment = {"DEPLOY_VALIDATOR_COUNTER": str(counter), "DEPLOY_BREAK_SOURCE": str(broken_source)}

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(fixture.installer),
            "-CodexHome",
            str(fixture.codex_home),
            "-ValidatorPath",
            str(fixture.validator),
        ],
        cwd=fixture.repository,
        env={**__import__("os").environ, **environment},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode != 0
    assert agents.read_bytes() == before_agents
    assert manifest.read_bytes() == before_manifest
    assert {
        name: sha256(fixture.codex_home / "skills" / name / "SKILL.md")
        for name in MANAGED_SKILLS
    } == deployed_hashes


def test_check_and_force_are_mutually_exclusive(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)

    result = run_installer(fixture, "-Check", "-Force")

    assert result.returncode != 0
    assert not fixture.codex_home.exists()
