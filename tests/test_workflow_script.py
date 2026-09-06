import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "scripts" / "check-research-workflow.ps1"
SCENARIOS = REPO_ROOT / "evaluation" / "codex-scenarios.md"


def write_fake_launcher(path: Path) -> None:
    path.write_text(
        r'''
[CmdletBinding()]
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$EspdocsArguments = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Content -LiteralPath $env:ESPDOCS_WORKFLOW_CALL_LOG `
    -Value ($EspdocsArguments -join " ") -Encoding UTF8

$command = $EspdocsArguments[0]
switch ($command) {
    "doctor" {
        $verifyRecommended = $false
        if ($env:ESPDOCS_WORKFLOW_VERIFY_RECOMMENDED) {
            $verifyRecommended = [bool]::Parse(
                $env:ESPDOCS_WORKFLOW_VERIFY_RECOMMENDED
            )
        }
        $payload = @{
            schema_version = 1
            readiness = @{
                query = $true
                source = $true
                ingest = $false
                verify_recommended = $verifyRecommended
                reasons = @("cuda_unavailable")
            }
        }
    }
    "verify" {
        $payload = @{
            schema_version = 1
            passed = $true
        }
    }
    "search" {
        $query = $EspdocsArguments[1]
        if ($query -eq "GPIO_STRAP_REG") {
            $payload = @{
                schema_version = 1
                results = @(@{
                    page_id = 101
                    source_ref = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                    vendor = "espressif"
                    family = "esp32"
                    parts = @("esp32-c3")
                    document_type = "technical_reference_manual"
                    document_revision = "1.4"
                    locator = @{ source_format = "pdf"; kind = "pdf_page"; physical_page = 168; anchor = $null }
                    snippet = "GPIO_STRAP_REG"
                    evidence_grade = "C"
                    requires_source_check = $true
                    source_check_reasons = @("register")
                })
            }
        }
        else {
            $payload = @{
                schema_version = 1
                results = @(@{
                    page_id = 202
                    source_ref = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                    vendor = "texas-instruments"
                    family = "bq2407x"
                    parts = @("bq24072", "bq24073", "bq24074", "bq24075", "bq24079")
                    document_type = "datasheet"
                    document_revision = "ZHCSIF0N"
                    locator = @{ source_format = "pdf"; kind = "pdf_page"; physical_page = 25; anchor = $null }
                    snippet = "charge current translator"
                    evidence_grade = "C"
                    requires_source_check = $true
                    source_check_reasons = @("formula")
                })
            }
        }
    }
    "show" {
        $payload = @{
            schema_version = 1
            page = @{
                page_id = 202
                source_ref = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                locator = @{ source_format = "pdf"; kind = "pdf_page"; physical_page = 25; anchor = $null }
                text = "charge current translator"
            }
        }
    }
    "source" {
        $payload = @{
            schema_version = 1
            source = @{
                source_ref = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                verified_sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                evidence_grade = "A"
                locator = @{ source_format = "pdf"; kind = "pdf_page"; physical_page = 25; anchor = $null }
            }
        }
    }
    default {
        throw "Unexpected command: $command"
    }
}

$payload | ConvertTo-Json -Depth 8 -Compress
'''.strip()
        + "\n",
        encoding="utf-8",
    )


def test_read_only_workflow_reports_all_acceptance_checks(tmp_path: Path) -> None:
    launcher = tmp_path / "fake-launcher.ps1"
    call_log = tmp_path / "calls.log"
    outside = tmp_path / "outside"
    outside.mkdir()
    write_fake_launcher(launcher)
    environment = os.environ.copy()
    environment["ESPDOCS_WORKFLOW_CALL_LOG"] = str(call_log)

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WORKFLOW),
            "-Launcher",
            str(launcher),
        ],
        cwd=outside,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "schema_version": 1,
        "passed": True,
        "checks": {
            "query_ready": True,
            "esp32_exact_scope": True,
            "bq2407x_exact_scope": True,
            "source_hash_verified": True,
            "compact_output": True,
        },
    }
    commands = call_log.read_text(encoding="utf-8-sig").splitlines()
    assert [command.split()[0] for command in commands] == [
        "doctor",
        "search",
        "search",
        "show",
        "source",
    ]
    assert all(not command.startswith("verify") for command in commands)


def test_workflow_runs_verify_only_when_doctor_recommends_it(tmp_path: Path) -> None:
    launcher = tmp_path / "fake-launcher.ps1"
    call_log = tmp_path / "calls.log"
    outside = tmp_path / "outside"
    outside.mkdir()
    write_fake_launcher(launcher)
    environment = os.environ.copy()
    environment["ESPDOCS_WORKFLOW_CALL_LOG"] = str(call_log)
    environment["ESPDOCS_WORKFLOW_VERIFY_RECOMMENDED"] = "true"

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WORKFLOW),
            "-Launcher",
            str(launcher),
        ],
        cwd=outside,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["passed"] is True
    commands = call_log.read_text(encoding="utf-8-sig").splitlines()
    assert [command.split()[0] for command in commands] == [
        "doctor",
        "verify",
        "search",
        "search",
        "show",
        "source",
    ]
    assert all(not command.startswith("ingest") for command in commands)


def test_codex_scenarios_define_all_observable_acceptance_cases() -> None:
    text = SCENARIOS.read_text(encoding="utf-8")
    prompts = (
        "ESP32-C3 的 GPIO_STRAP_REG 在哪里定义，回答前核对原始手册。",
        "这个项目使用 ESP-IDF 的哪个版本？用对应版本说明这个 API。",
        "BQ24075 的 ISET 电阻如何决定充电电流？核对原始数据手册。",
        "我只有一个模糊丝印 ABC123，能直接按相似芯片给出绝对最大额定值吗？",
        "CUDA 当前不可用，已有手册索引还能不能查？",
        "数据手册文件被替换后，旧索引中的电气参数还能直接引用吗？",
        "解释这张数据手册表格，并检查原始页面与脚注。",
    )

    assert all(prompt in text for prompt in prompts)
    for field in (
        "预期 Skill 路由",
        "最多正常调用序列",
        "身份与来源证据",
        "禁止的回退",
        "通过/失败观察",
    ):
        assert text.count(field) == 7


def test_readme_documents_everyday_acceptance_and_recovery_paths() -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "日常只读检索" in text
    assert "check-research-workflow.ps1" in text
    assert "--compact" in text
    assert "维护门禁" in text
    assert "新增手册" in text
    assert "源文件发生变化" in text
