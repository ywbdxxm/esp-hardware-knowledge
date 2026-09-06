# ESP32 Document Research Adapter

Use `hardware-document-research` for the common exact-part, query-readiness, search, evidence, and
official-vendor fallback workflow. This reference adds only ESP32-specific target and source rules.

## Establish the Exact Target

Before searching, resolve the project `IDF_TARGET`, SoC, module or orderable part, board revision,
and project-selected ESP-IDF revision. A module such as `esp32-c3-wroom-02` is not interchangeable
with the bare `esp32-c3` chip for package, pin, antenna, flash, PSRAM, or module electrical facts.
Do not answer a C3 question from an S3 result or infer a module from the family name.

## Select the Source Owner

- ESP-IDF API, Kconfig, build behavior, examples, and component headers belong to the
  project-selected ESP-IDF revision; use `esp-idf-local-docs.md` and matching local source.
- SoC registers, pins, straps, eFuse, electrical values, timing, and package behavior belong to the
  exact chip PDF, errata, or design guide.
- Module pinout, antenna keepout, flash or PSRAM population, dimensions, and module ratings belong to
  the exact module datasheet.

When a claim crosses these owners, verify both sources and report any revision mismatch.

## Invoke the Shared Research Contract

Use the launcher maintained by `hardware-document-research`:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$runner = Join-Path $codexHome "skills/hardware-document-research/scripts/invoke-espdocs.ps1"
& $runner doctor --json
& $runner search "GPIO_STRAP_REG" --vendor espressif --part esp32-c3 `
  --type technical_reference_manual --limit 5 --compact --json
& $runner show <page_id> --json
& $runner source <page_id> --json
```

Use the exact module `--part` for module facts. Legacy `--chip` remains compatible, but new research
should prefer vendor plus exact part. Follow the shared evidence workflow for `inventory`, no-match,
source verification, and maintenance `verify` decisions rather than duplicating those rules here.

Critical ESP32 facts still require the hash-matched original PDF page. Record the target, document
revision, physical page, and whether adjacent pages were checked.
