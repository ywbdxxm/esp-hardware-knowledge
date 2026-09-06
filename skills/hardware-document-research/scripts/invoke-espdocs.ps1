[CmdletBinding()]
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$EspdocsArguments = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-EspdocsResolutionError {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Type,
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [string[]]$Candidates = @()
    )

    $detail = [ordered]@{
        type = $Type
        message = $Message
    }
    if ($Candidates.Count -gt 0) {
        $detail.candidates = @($Candidates)
    }
    $payload = [ordered]@{
        schema_version = 1
        error = $detail
    }
    return ($payload | ConvertTo-Json -Depth 4 -Compress)
}

function Test-EspdocsProjectRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }
    try {
        $root = [IO.Path]::GetFullPath($Path)
    }
    catch {
        return $false
    }
    return (
        (Test-Path -LiteralPath (Join-Path $root "pyproject.toml") -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $root "uv.lock") -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $root "src\espdocs") -PathType Container)
    )
}

function Resolve-EspdocsProjectRoot {
    param(
        [AllowNull()]
        [string]$ProcessRoot,
        [AllowNull()]
        [string]$UserRoot,
        [Parameter(Mandatory = $true)]
        [string]$StartDirectory
    )

    foreach ($configured in @($ProcessRoot, $UserRoot)) {
        if ([string]::IsNullOrWhiteSpace($configured)) {
            continue
        }
        $resolved = [IO.Path]::GetFullPath($configured)
        if (-not (Test-EspdocsProjectRoot -Path $resolved)) {
            throw [InvalidOperationException]::new((New-EspdocsResolutionError `
                -Type "IncompleteProjectRoot" `
                -Message "Configured ESPDocs project root is incomplete." `
                -Candidates @($resolved)))
        }
        return $resolved
    }

    $start = [IO.Path]::GetFullPath($StartDirectory)
    if (-not (Test-Path -LiteralPath $start -PathType Container)) {
        throw [InvalidOperationException]::new((New-EspdocsResolutionError `
            -Type "ProjectRootNotFound" `
            -Message "Start directory does not exist."))
    }

    $candidates = [Collections.Generic.List[string]]::new()
    $current = [IO.DirectoryInfo]::new($start)
    while ($null -ne $current) {
        if (Test-EspdocsProjectRoot -Path $current.FullName) {
            $candidates.Add($current.FullName)
        }
        $current = $current.Parent
    }

    if ($candidates.Count -eq 0) {
        throw [InvalidOperationException]::new((New-EspdocsResolutionError `
            -Type "ProjectRootNotFound" `
            -Message "No ESPDocs project root was found in the bounded ancestor search."))
    }
    if ($candidates.Count -gt 1) {
        throw [InvalidOperationException]::new((New-EspdocsResolutionError `
            -Type "AmbiguousProjectRoot" `
            -Message "Multiple ESPDocs project roots were found." `
            -Candidates $candidates.ToArray()))
    }
    return $candidates[0]
}

function Invoke-EspdocsLauncher {
    param(
        [string[]]$Arguments
    )

    try {
        $resolvedRoot = Resolve-EspdocsProjectRoot `
            -ProcessRoot ([Environment]::GetEnvironmentVariable(
                "ESP_HARDWARE_KNOWLEDGE_ROOT", "Process"
            )) `
            -UserRoot ([Environment]::GetEnvironmentVariable(
                "ESP_HARDWARE_KNOWLEDGE_ROOT", "User"
            )) `
            -StartDirectory (Get-Location).Path
    }
    catch {
        [Console]::Error.WriteLine($_.Exception.Message)
        $script:EspdocsExitCode = 3
        return
    }

    if ($null -eq (Get-Command uv -ErrorAction SilentlyContinue)) {
        [Console]::Error.WriteLine((New-EspdocsResolutionError `
            -Type "UvUnavailable" `
            -Message "uv is required to invoke the locked ESPDocs project environment."))
        $script:EspdocsExitCode = 3
        return
    }

    & uv run --locked --project $resolvedRoot espdocs @Arguments
    $script:EspdocsExitCode = $LASTEXITCODE
}

if ($MyInvocation.InvocationName -ne ".") {
    $script:EspdocsExitCode = 0
    Invoke-EspdocsLauncher -Arguments $EspdocsArguments
    exit $script:EspdocsExitCode
}
