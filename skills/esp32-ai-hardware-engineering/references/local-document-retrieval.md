# Local ESP32 Document Retrieval

Use the local ESPDocs corpus to locate source evidence before relying on memory or web search.

## Project Discovery and Invocation

`espdocs` is a project console script, not a globally installed command. `Get-Command espdocs` may
therefore return nothing even when the local tool is healthy. Do not treat that PATH result as a
failure and do not install a second global copy.

Resolve the project root in this order:

1. Use the `ESP_HARDWARE_KNOWLEDGE_ROOT` process variable when it is set. If the current host was
   started before the user variable was configured, read the user-level value with
   `[Environment]::GetEnvironmentVariable('ESP_HARDWARE_KNOWLEDGE_ROOT', 'User')`.
2. Search only bounded workspace roots and parent directories for a directory containing `pyproject.toml`,
   `uv.lock`, and `src\espdocs`.
3. If no unique root is found, stop and report the missing local tool; do not silently use another
   Python environment or a different repository.

Validate that the selected root contains the `espdocs` project script and its lock file, then run the
same canonical command from any working directory:

```powershell
$espdocsRoot = $env:ESP_HARDWARE_KNOWLEDGE_ROOT
if ([string]::IsNullOrWhiteSpace($espdocsRoot)) {
    $espdocsRoot = [Environment]::GetEnvironmentVariable('ESP_HARDWARE_KNOWLEDGE_ROOT', 'User')
}
if (-not (Test-Path -LiteralPath (Join-Path $espdocsRoot 'pyproject.toml')) -or
    -not (Test-Path -LiteralPath (Join-Path $espdocsRoot 'uv.lock')) -or
    -not (Test-Path -LiteralPath (Join-Path $espdocsRoot 'src\espdocs'))) {
    throw "ESPDocs project root is incomplete: $espdocsRoot"
}

uv run --locked --project $espdocsRoot espdocs doctor --json
uv run --locked --project $espdocsRoot espdocs verify --json
```

Do not replace `--project` with the current directory unless the current directory is the validated
ESPDocs root. Do not use the default Python, an ESP-IDF venv, or `uv run espdocs` from an unrelated
directory.

## Readiness

From the validated `esp-hardware-knowledge` repository, using the canonical invocation above:

```powershell
uv run --locked --project $espdocsRoot espdocs doctor --json
uv run --locked --project $espdocsRoot espdocs verify --json
```

Proceed only when `doctor.healthy` and `verify.passed` are true. A successful command with a false
JSON readiness field is a failure. An explicit `ESPDOCS_DATA_ROOT` overrides automatic discovery;
keep machine-specific data paths out of this Skill.

## Evidence Flow

Always filter the exact chip. Add `--type` when the required document class is known.

```powershell
uv run --locked --project $espdocsRoot espdocs search "GPIO_STRAP_REG" --chip esp32-c3 --type technical_reference_manual --limit 5 --json
uv run --locked --project $espdocsRoot espdocs show <page_id> --json
uv run --locked --project $espdocsRoot espdocs source <page_id> --json
```

1. Use `search` only to find candidate pages.
2. Use `show` to inspect the complete indexed page and traceability fields.
3. Use `source` to recompute the source hash and render the authoritative original PDF page.
4. Inspect adjacent pages when a table, diagram, register block, or section crosses a page boundary.

The `page_id` passed to `show` and `source` comes from search results; it is not the PDF page number.

## Mandatory Original PDF Checks

Use the original PDF for registers, addresses, bit fields, reset values, pins, boot straps, eFuse,
security, flashing, voltages, currents, power, timing, frequency, RF, tables, diagrams, OCR
warnings, unknown document versions, or any discrepancy. Record the chip, filename, document
version, physical PDF page, and whether adjacent pages were checked.

If the validated project root is missing, the locked project command fails, or readiness is unhealthy,
say which check failed and inspect the source PDF directly. Do not downgrade merely because bare
`espdocs` is absent from `PATH`; do not silently answer from another chip, an unverified extraction,
or a general web result.
