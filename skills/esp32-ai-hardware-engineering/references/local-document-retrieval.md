# Local ESP32 Document Retrieval

Use the local ESPDocs corpus to locate source evidence before relying on memory or web search.

## Readiness

From the `esp-hardware-knowledge` repository:

```powershell
uv run espdocs doctor --json
uv run espdocs verify --json
```

Proceed only when `doctor.healthy` and `verify.passed` are true. The configured local data root is
`%USERPROFILE%\Desktop\AI-HRADWARE\docs\esp-hardware-knowledge-data`; an explicit
`ESPDOCS_DATA_ROOT` overrides automatic discovery.

## Evidence Flow

Always filter the exact chip. Add `--type` when the required document class is known.

```powershell
uv run espdocs search "GPIO_STRAP_REG" --chip esp32-c3 --type technical_reference_manual --limit 5 --json
uv run espdocs show <page_id> --json
uv run espdocs source <page_id> --json
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

If `espdocs` is unavailable or unhealthy, say so and inspect the source PDF directly. Do not
silently answer from another chip, an unverified extraction, or a general web result.
