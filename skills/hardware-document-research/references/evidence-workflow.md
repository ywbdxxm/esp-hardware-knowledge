# Hardware Evidence Workflow

## Local Query Path

Locate the installed launcher from Codex Home and use its JSON boundary:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$runner = Join-Path $codexHome "skills/hardware-document-research/scripts/invoke-espdocs.ps1"
& $runner doctor --json
& $runner inventory --json
$search = & $runner search "charge current translator" `
  --vendor texas-instruments --family bq2407x --part bq24075 `
  --type datasheet --limit 5 --compact --json | ConvertFrom-Json
$pageId = $search.results[0].page_id
& $runner show $pageId --json
& $runner source $pageId --json
```

Use `doctor.readiness.query`, not legacy `healthy`, to decide whether an existing index is
searchable. Missing ingestion acceleration does not make a healthy index unavailable. Skip
`inventory` when the exact indexed vendor, family, part, variant, and document type are already
known; otherwise use it to discover valid filters instead of guessing them.

Search with the narrowest exact identity available. A valid filter with no results is an exact-scope
miss. Refine the query within that identity or report the gap; never remove the part or family filter
to obtain a plausible result from another device. Use `show` to read the complete evidence unit.

Call `source` when `requires_source_check` is true, identity or context is ambiguous, or the claim
depends on an electrical value, limit, pin, package, register, reset value, timing, table, diagram,
plot, formula, footnote, safety behavior, or irreversible operation. Check adjacent locators when a
section crosses a page boundary. Record the exact part, document title and revision, source hash,
and physical page or other authoritative locator.

Run full `verify` after ingestion, configuration or index migration, suspected corruption, a source
change, or `doctor.readiness.verify_recommended=true`. It is a maintenance gate, not part of every
read-only query.

## Authoritative Fallback

When local query readiness is false or exact evidence is absent, use only an official vendor source
for the exact part and disclose that the local corpus was unavailable or incomplete. Preserve the
official URL or downloaded-source hash and its revision and locator. Do not silently substitute a
related family member, translated copy, distributor summary, search snippet, or generated Markdown.

If the original source cannot be verified, state the evidence limitation and do not present a
critical specification as authoritative.
