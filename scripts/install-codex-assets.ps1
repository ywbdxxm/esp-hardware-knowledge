[CmdletBinding()]
param(
    [string]$CodexHome = $(
        if ($env:CODEX_HOME) {
            $env:CODEX_HOME
        }
        else {
            Join-Path $env:USERPROFILE ".codex"
        }
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$sourceAgents = Join-Path $repoRoot "codex\AGENTS.md"
$sourceSkillsRoot = Join-Path $repoRoot "skills"
$managedSkills = @(
    "esp32-ai-hardware-engineering",
    "docling-local-document-engineering"
)

if (-not (Test-Path -LiteralPath $sourceAgents -PathType Leaf)) {
    throw "Canonical AGENTS.md not found: $sourceAgents"
}

foreach ($skillName in $managedSkills) {
    $source = Join-Path $sourceSkillsRoot $skillName
    if (-not (Test-Path -LiteralPath (Join-Path $source "SKILL.md") -PathType Leaf)) {
        throw "Canonical Skill not found: $source"
    }
}

$CodexHome = [IO.Path]::GetFullPath($CodexHome)
$targetSkillsRoot = Join-Path $CodexHome "skills"
New-Item -ItemType Directory -Force -Path $targetSkillsRoot | Out-Null

Copy-Item -LiteralPath $sourceAgents -Destination (Join-Path $CodexHome "AGENTS.md") -Force
Write-Output "Deployed: $(Join-Path $CodexHome 'AGENTS.md')"

foreach ($skillName in $managedSkills) {
    $source = Join-Path $sourceSkillsRoot $skillName
    $target = Join-Path $targetSkillsRoot $skillName
    $stage = Join-Path $targetSkillsRoot ".$skillName.deploy-$PID"
    $backup = Join-Path $targetSkillsRoot ".$skillName.backup-$PID"

    if ((Test-Path -LiteralPath $stage) -or (Test-Path -LiteralPath $backup)) {
        throw "Deployment staging path already exists for $skillName"
    }

    Copy-Item -LiteralPath $source -Destination $stage -Recurse

    try {
        if (Test-Path -LiteralPath $target) {
            Move-Item -LiteralPath $target -Destination $backup
        }
        Move-Item -LiteralPath $stage -Destination $target
        if (Test-Path -LiteralPath $backup) {
            Remove-Item -LiteralPath $backup -Recurse -Force
        }
    }
    catch {
        if ((-not (Test-Path -LiteralPath $target)) -and (Test-Path -LiteralPath $backup)) {
            Move-Item -LiteralPath $backup -Destination $target
        }
        throw
    }

    Write-Output "Deployed: $target"
}
