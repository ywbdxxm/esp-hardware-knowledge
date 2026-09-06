[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Launcher,
    [string]$EspPart = "esp32-c3",
    [string]$BqPart = "bq24075"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-EspdocsJson {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass `
        -File $script:ResolvedLauncher @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
    if ($exitCode -ne 0) {
        throw "ESPDocs command failed ($exitCode): $($Arguments -join ' ')`n$text"
    }
    try {
        return $text | ConvertFrom-Json
    }
    catch {
        throw "ESPDocs command returned invalid JSON: $($Arguments -join ' ')"
    }
}

function Test-ExactHit {
    param(
        [Parameter(Mandatory = $true)]$Hit,
        [Parameter(Mandatory = $true)][string]$Vendor,
        [Parameter(Mandatory = $true)][string]$Family,
        [Parameter(Mandatory = $true)][string]$Part,
        [Parameter(Mandatory = $true)][string]$DocumentType
    )

    $parts = @($Hit.parts | ForEach-Object { $_.ToString() })
    return (
        $Hit.vendor -eq $Vendor -and
        $Hit.family -eq $Family -and
        $parts -contains $Part -and
        $Hit.document_type -eq $DocumentType
    )
}

function Test-CompactHit {
    param([Parameter(Mandatory = $true)]$Hit)

    $required = @(
        "page_id",
        "source_ref",
        "vendor",
        "family",
        "parts",
        "document_type",
        "document_revision",
        "locator",
        "snippet",
        "evidence_grade",
        "requires_source_check",
        "source_check_reasons"
    )
    $prohibited = @("source_path", "markdown_path", "sha256", "score", "matched_terms")
    $names = @($Hit.PSObject.Properties.Name)
    return (
        @($required | Where-Object { $_ -notin $names }).Count -eq 0 -and
        @($prohibited | Where-Object { $_ -in $names }).Count -eq 0
    )
}

function Get-FirstHit {
    param(
        [Parameter(Mandatory = $true)]$Payload,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $hits = @($Payload.results)
    if ($hits.Count -eq 0 -or $null -eq $hits[0]) {
        throw "$Label exact search returned no results"
    }
    return $hits[0]
}

$checks = [ordered]@{
    query_ready = $false
    esp32_exact_scope = $false
    bq2407x_exact_scope = $false
    source_hash_verified = $false
    compact_output = $false
}
$failures = [Collections.Generic.List[string]]::new()

try {
    if (-not (Test-Path -LiteralPath $Launcher -PathType Leaf)) {
        throw "Launcher does not exist: $Launcher"
    }
    $script:ResolvedLauncher = (Resolve-Path -LiteralPath $Launcher).Path

    $doctor = Invoke-EspdocsJson -Arguments @("doctor", "--json")
    $checks.query_ready = $doctor.readiness.query -eq $true
    if (-not $checks.query_ready) {
        throw "Existing index is not query-ready"
    }
    if ($doctor.readiness.verify_recommended -eq $true) {
        $verification = Invoke-EspdocsJson -Arguments @("verify", "--json")
        if ($verification.passed -ne $true) {
            throw "ESPDocs verification was recommended but did not pass"
        }
    }

    $espSearch = Invoke-EspdocsJson -Arguments @(
        "search", "GPIO_STRAP_REG",
        "--vendor", "espressif",
        "--family", "esp32",
        "--part", $EspPart,
        "--type", "technical_reference_manual",
        "--limit", "5",
        "--compact",
        "--json"
    )
    $espHit = Get-FirstHit -Payload $espSearch -Label "ESP32"
    $checks.esp32_exact_scope = Test-ExactHit -Hit $espHit `
        -Vendor "espressif" -Family "esp32" -Part $EspPart `
        -DocumentType "technical_reference_manual"

    $bqSearch = Invoke-EspdocsJson -Arguments @(
        "search", "charge current translator",
        "--vendor", "texas-instruments",
        "--family", "bq2407x",
        "--part", $BqPart,
        "--type", "datasheet",
        "--limit", "5",
        "--compact",
        "--json"
    )
    $bqHit = Get-FirstHit -Payload $bqSearch -Label "BQ2407x"
    $checks.bq2407x_exact_scope = Test-ExactHit -Hit $bqHit `
        -Vendor "texas-instruments" -Family "bq2407x" -Part $BqPart `
        -DocumentType "datasheet"
    $checks.compact_output = (
        (Test-CompactHit -Hit $espHit) -and (Test-CompactHit -Hit $bqHit)
    )

    $page = Invoke-EspdocsJson -Arguments @("show", $bqHit.page_id.ToString(), "--json")
    $source = Invoke-EspdocsJson -Arguments @("source", $bqHit.page_id.ToString(), "--json")
    $expectedHash = $bqHit.source_ref -replace "^sha256:", ""
    $checks.source_hash_verified = (
        $bqHit.source_ref -match "^sha256:[0-9a-fA-F]{64}$" -and
        $page.page.page_id -eq $bqHit.page_id -and
        $page.page.source_ref -eq $bqHit.source_ref -and
        $page.page.locator.physical_page -eq $bqHit.locator.physical_page -and
        $source.source.source_ref -eq $bqHit.source_ref -and
        $source.source.verified_sha256 -eq $expectedHash -and
        $source.source.locator.physical_page -eq $bqHit.locator.physical_page -and
        $source.source.evidence_grade -eq "A"
    )

    foreach ($entry in $checks.GetEnumerator()) {
        if ($entry.Value -ne $true) {
            $failures.Add("Check failed: $($entry.Key)")
        }
    }
}
catch {
    $failures.Add($_.Exception.Message)
}

$passed = $failures.Count -eq 0 -and @(
    $checks.Values | Where-Object { $_ -ne $true }
).Count -eq 0
$summary = [ordered]@{
    schema_version = 1
    passed = $passed
    checks = $checks
}
if ($failures.Count -gt 0) {
    $summary.failures = @($failures)
}

$json = ($summary | ConvertTo-Json -Depth 8 -Compress) + [Environment]::NewLine
[Console]::Out.Write($json)
if (-not $passed) {
    exit 1
}
