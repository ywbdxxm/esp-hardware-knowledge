[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$CodexHome = $(
        if ($env:CODEX_HOME) {
            $env:CODEX_HOME
        }
        else {
            Join-Path $env:USERPROFILE ".codex"
        }
    ),
    [string]$ValidatorPath = $(
        Join-Path $(
            if ($env:CODEX_HOME) {
                $env:CODEX_HOME
            }
            else {
                Join-Path $env:USERPROFILE ".codex"
            }
        ) "skills/.system/skill-creator/scripts/quick_validate.py"
    ),
    [switch]$Check,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$sourceAgents = Join-Path $repoRoot "codex\AGENTS.md"
$sourceSkillsRoot = Join-Path $repoRoot "skills"
$managedSkills = @(
    "hardware-document-research",
    "esp32-ai-hardware-engineering",
    "docling-local-document-engineering"
)
$manifestRelativePath = "managed/esp-hardware-knowledge-assets.json"

function ConvertTo-ManagedPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    return $Path.Replace("\", "/").TrimStart("/")
}

function Get-FileDigest {
    param([Parameter(Mandatory = $true)][string]$Path)

    $stream = [IO.File]::OpenRead($Path)
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $hasher.ComputeHash($stream)
        return ([BitConverter]::ToString($bytes)).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $hasher.Dispose()
        $stream.Dispose()
    }
}

function Test-IgnoredSourceFile {
    param([Parameter(Mandatory = $true)][IO.FileInfo]$File)

    return $File.Extension -eq ".pyc" -or $File.FullName -match "[\\/]__pycache__[\\/]"
}

function Get-CanonicalFiles {
    $files = [Collections.Generic.SortedDictionary[string, string]]::new(
        [StringComparer]::Ordinal
    )
    if (-not (Test-Path -LiteralPath $sourceAgents -PathType Leaf)) {
        throw "Canonical AGENTS.md not found: $sourceAgents"
    }
    $files.Add("AGENTS.md", $sourceAgents)
    foreach ($skillName in $managedSkills) {
        $source = Join-Path $sourceSkillsRoot $skillName
        if (-not (Test-Path -LiteralPath (Join-Path $source "SKILL.md") -PathType Leaf)) {
            throw "Canonical Skill not found: $source"
        }
        foreach ($file in Get-ChildItem -File -Recurse -LiteralPath $source) {
            if (Test-IgnoredSourceFile -File $file) {
                continue
            }
            $relative = $file.FullName.Substring($source.Length).TrimStart("\", "/")
            $managedPath = ConvertTo-ManagedPath -Path "skills/$skillName/$relative"
            $files.Add($managedPath, $file.FullName)
        }
    }
    return $files
}

function Get-CanonicalDigests {
    param(
        [Parameter(Mandatory = $true)]
        [Collections.Generic.SortedDictionary[string, string]]$Files
    )

    $digests = [Collections.Generic.SortedDictionary[string, string]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($entry in $Files.GetEnumerator()) {
        $digests.Add($entry.Key, (Get-FileDigest -Path $entry.Value))
    }
    return $digests
}

function Test-DigestMapsEqual {
    param(
        [Parameter(Mandatory = $true)]$Left,
        [Parameter(Mandatory = $true)]$Right
    )

    if ($Left.Count -ne $Right.Count) {
        return $false
    }
    foreach ($entry in $Left.GetEnumerator()) {
        if (-not $Right.ContainsKey($entry.Key) -or $Right[$entry.Key] -ne $entry.Value) {
            return $false
        }
    }
    return $true
}

function Invoke-SkillValidators {
    if (-not (Test-Path -LiteralPath $ValidatorPath -PathType Leaf)) {
        throw "Skill validator not found: $ValidatorPath"
    }
    if ($null -eq (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv is required to validate managed Skills"
    }
    foreach ($skillName in $managedSkills) {
        $source = Join-Path $sourceSkillsRoot $skillName
        if ((Test-Path -LiteralPath (Join-Path $repoRoot "pyproject.toml") -PathType Leaf) -and
            (Test-Path -LiteralPath (Join-Path $repoRoot "uv.lock") -PathType Leaf)) {
            & uv run --locked --project $repoRoot python $ValidatorPath $source
        }
        else {
            & uv run --no-project python $ValidatorPath $source
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Skill validation failed: $skillName"
        }
    }
}

function Get-ManifestFiles {
    param([Parameter(Mandatory = $true)][string]$ManifestPath)

    $files = @{}
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
        return $files
    }
    try {
        $manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json
        if ($manifest.schema_version -ne 1 -or $null -eq $manifest.files) {
            throw "unsupported manifest schema"
        }
        foreach ($property in $manifest.files.PSObject.Properties) {
            $files[$property.Name] = [string]$property.Value
        }
    }
    catch {
        throw "Invalid deployment manifest: $ManifestPath ($($_.Exception.Message))"
    }
    return $files
}

function Get-DeployedFiles {
    param([Parameter(Mandatory = $true)][string]$CodexRoot)

    $files = @{}
    $agents = Join-Path $CodexRoot "AGENTS.md"
    if (Test-Path -LiteralPath $agents -PathType Leaf) {
        $files["AGENTS.md"] = $agents
    }
    foreach ($skillName in $managedSkills) {
        $target = Join-Path $CodexRoot "skills\$skillName"
        if (-not (Test-Path -LiteralPath $target -PathType Container)) {
            continue
        }
        foreach ($file in Get-ChildItem -File -Recurse -LiteralPath $target) {
            $relative = $file.FullName.Substring($target.Length).TrimStart("\", "/")
            $managedPath = ConvertTo-ManagedPath -Path "skills/$skillName/$relative"
            $files[$managedPath] = $file.FullName
        }
    }
    return $files
}

function Get-DeploymentDifferences {
    param(
        [Parameter(Mandatory = $true)]$Canonical,
        [Parameter(Mandatory = $true)]$Deployed,
        [Parameter(Mandatory = $true)]$LastDeployed,
        [switch]$RequireParity
    )

    $differences = [Collections.Generic.List[object]]::new()
    $paths = @($Canonical.Keys + $Deployed.Keys | Sort-Object -Unique)
    foreach ($relative in $paths) {
        $canonicalHash = if ($Canonical.ContainsKey($relative)) {
            $Canonical[$relative]
        }
        else {
            $null
        }
        $deployedHash = if ($Deployed.ContainsKey($relative)) {
            Get-FileDigest -Path $Deployed[$relative]
        }
        else {
            $null
        }
        $lastHash = if ($LastDeployed.ContainsKey($relative)) {
            $LastDeployed[$relative]
        }
        else {
            $null
        }

        if ($RequireParity) {
            if ($canonicalHash -ne $deployedHash -or $canonicalHash -ne $lastHash) {
                $differences.Add([pscustomobject]@{
                    path = $relative
                    reason = "parity_mismatch"
                })
            }
            continue
        }

        if ($null -eq $deployedHash) {
            continue
        }
        if ($deployedHash -eq $canonicalHash -or $deployedHash -eq $lastHash) {
            continue
        }
        $differences.Add([pscustomobject]@{
            path = $relative
            reason = "destination_drift"
        })
    }
    return $differences
}

function Assert-SafeCodexHome {
    param([Parameter(Mandatory = $true)][string]$CodexRoot)

    $full = [IO.Path]::GetFullPath($CodexRoot).TrimEnd("\", "/")
    $root = [IO.Path]::GetPathRoot($full).TrimEnd("\", "/")
    if ([string]::IsNullOrWhiteSpace($full) -or $full -eq $root) {
        throw "CodexHome must not be a filesystem root: $CodexRoot"
    }
    return $full
}

function Assert-WithinCodexHome {
    param(
        [Parameter(Mandatory = $true)][string]$CodexRoot,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $root = [IO.Path]::GetFullPath($CodexRoot).TrimEnd("\", "/") +
        [IO.Path]::DirectorySeparatorChar
    $target = [IO.Path]::GetFullPath($Path)
    if (-not $target.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Managed path escapes CodexHome: $target"
    }
}

function New-DeploymentManifest {
    param([Parameter(Mandatory = $true)]$Canonical)

    $orderedFiles = [ordered]@{}
    foreach ($entry in $Canonical.GetEnumerator()) {
        $orderedFiles[$entry.Key] = $entry.Value
    }
    $commit = "unknown"
    if ((Test-Path -LiteralPath (Join-Path $repoRoot ".git")) -and
        $null -ne (Get-Command git -ErrorAction SilentlyContinue)) {
        $candidate = (& git -C $repoRoot rev-parse HEAD 2>$null)
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($candidate)) {
            $commit = $candidate.Trim()
        }
    }
    return [ordered]@{
        schema_version = 1
        repository_commit = $commit
        deployed_at = [DateTimeOffset]::Now.ToString("o")
        files = $orderedFiles
    }
}

if ($Check -and $Force) {
    throw "-Check and -Force cannot be used together"
}

$CodexHome = Assert-SafeCodexHome -CodexRoot $CodexHome
$canonicalFilesBefore = Get-CanonicalFiles
$canonicalBefore = Get-CanonicalDigests -Files $canonicalFilesBefore
Invoke-SkillValidators
$canonicalFiles = Get-CanonicalFiles
$canonical = Get-CanonicalDigests -Files $canonicalFiles
if (-not (Test-DigestMapsEqual -Left $canonicalBefore -Right $canonical)) {
    throw "Canonical managed assets changed during validation"
}

$manifestPath = Join-Path $CodexHome ($manifestRelativePath.Replace("/", "\"))
$lastDeployed = Get-ManifestFiles -ManifestPath $manifestPath
$deployed = Get-DeployedFiles -CodexRoot $CodexHome

if ($Check) {
    $differences = @(Get-DeploymentDifferences -Canonical $canonical -Deployed $deployed `
        -LastDeployed $lastDeployed -RequireParity)
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        $differences += [pscustomobject]@{
            path = $manifestRelativePath
            reason = "missing_manifest"
        }
    }
    if ($differences.Count -gt 0) {
        foreach ($difference in $differences) {
            [Console]::Error.WriteLine("$($difference.reason): $($difference.path)")
        }
        exit 1
    }
    Write-Output "Managed Codex assets match canonical source and deployment manifest."
    exit 0
}

$drift = @(Get-DeploymentDifferences -Canonical $canonical -Deployed $deployed `
    -LastDeployed $lastDeployed)
if ($drift.Count -gt 0 -and -not $Force) {
    foreach ($difference in $drift) {
        [Console]::Error.WriteLine("Destination drift: $($difference.path)")
    }
    exit 2
}
if ($Force) {
    foreach ($difference in $drift) {
        Write-Output "Force replacing drift: $($difference.path)"
    }
}

if (-not $PSCmdlet.ShouldProcess($CodexHome, "Deploy managed Codex assets")) {
    exit 0
}

New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null
$transactionId = [Guid]::NewGuid().ToString("N")
$stageRoot = Join-Path $CodexHome ".esp-hardware-knowledge-stage-$transactionId"
$backupRoot = Join-Path $CodexHome ".esp-hardware-knowledge-backup-$transactionId"
Assert-WithinCodexHome -CodexRoot $CodexHome -Path $stageRoot
Assert-WithinCodexHome -CodexRoot $CodexHome -Path $backupRoot
$backedUp = [Collections.Generic.List[object]]::new()
$promoted = [Collections.Generic.List[object]]::new()

try {
    New-Item -ItemType Directory -Path $stageRoot | Out-Null
    foreach ($entry in $canonicalFiles.GetEnumerator()) {
        $stagePath = Join-Path $stageRoot ($entry.Key.Replace("/", "\"))
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $stagePath) | Out-Null
        Copy-Item -LiteralPath $entry.Value -Destination $stagePath
    }
    $stageManifest = Join-Path $stageRoot ($manifestRelativePath.Replace("/", "\"))
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $stageManifest) | Out-Null
    $manifest = New-DeploymentManifest -Canonical $canonical
    $manifestJson = ($manifest | ConvertTo-Json -Depth 6) + [Environment]::NewLine
    [IO.File]::WriteAllText($stageManifest, $manifestJson, [Text.UTF8Encoding]::new($false))

    foreach ($entry in $canonical.GetEnumerator()) {
        $stagePath = Join-Path $stageRoot ($entry.Key.Replace("/", "\"))
        if ((Get-FileDigest -Path $stagePath) -ne $entry.Value) {
            throw "Staged asset hash mismatch: $($entry.Key)"
        }
    }

    $targets = @(
        [pscustomobject]@{ relative = "AGENTS.md"; directory = $false }
    )
    foreach ($skillName in $managedSkills) {
        $targets += [pscustomobject]@{
            relative = "skills/$skillName"
            directory = $true
        }
    }
    $targets += [pscustomobject]@{
        relative = $manifestRelativePath
        directory = $false
    }

    foreach ($target in $targets) {
        $destination = Join-Path $CodexHome ($target.relative.Replace("/", "\"))
        $backup = Join-Path $backupRoot ($target.relative.Replace("/", "\"))
        Assert-WithinCodexHome -CodexRoot $CodexHome -Path $destination
        if (Test-Path -LiteralPath $destination) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
            Move-Item -LiteralPath $destination -Destination $backup
            $backedUp.Add([pscustomobject]@{
                destination = $destination
                backup = $backup
            })
        }
    }

    foreach ($target in $targets) {
        $source = Join-Path $stageRoot ($target.relative.Replace("/", "\"))
        $destination = Join-Path $CodexHome ($target.relative.Replace("/", "\"))
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
        Move-Item -LiteralPath $source -Destination $destination
        $promoted.Add([pscustomobject]@{
            destination = $destination
            directory = $target.directory
        })
    }

    $published = Get-DeployedFiles -CodexRoot $CodexHome
    $publishedManifest = Get-ManifestFiles -ManifestPath $manifestPath
    $parity = @(Get-DeploymentDifferences -Canonical $canonical -Deployed $published `
        -LastDeployed $publishedManifest -RequireParity)
    if ($parity.Count -gt 0) {
        throw "Published managed assets failed parity verification"
    }

    if (Test-Path -LiteralPath $backupRoot) {
        Remove-Item -LiteralPath $backupRoot -Recurse -Force
    }
    if (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}
catch {
    $failure = $_.Exception.Message
    foreach ($item in $promoted) {
        if (Test-Path -LiteralPath $item.destination) {
            Remove-Item -LiteralPath $item.destination -Recurse -Force
        }
    }
    foreach ($item in $backedUp) {
        if (Test-Path -LiteralPath $item.destination) {
            Remove-Item -LiteralPath $item.destination -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $item.destination) |
            Out-Null
        Move-Item -LiteralPath $item.backup -Destination $item.destination
    }
    throw "$failure Deployment rolled back. Staging retained at: $stageRoot"
}

Write-Output "Deployed managed Codex assets to: $CodexHome"
