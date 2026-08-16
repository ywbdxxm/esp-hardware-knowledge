# Local ESP-IDF Documentation

Use documentation and source from the same ESP-IDF revision as the project. Establish both the
version and `IDF_TARGET` before applying target-conditional content.

## Resolve the IDF Root

Resolve in this order:

1. The IDF root confirmed by the project environment, build files, or build output.
2. `$env:IDF_PATH` when it matches the project version.
3. This machine's known fallback `C:\esp\v6.0.2\esp-idf`, only for ESP-IDF v6.0.2.

Record the git describe result and commit for the selected root:

```powershell
$idfRoot = $env:IDF_PATH
git -C $idfRoot describe --tags --always --dirty
git -C $idfRoot rev-parse HEAD
```

The known fallback is tag `v6.0.2`, commit
`7101770dc6db2667b3c477cc31365dd1acd6db4e`. If the project uses another revision, report the
version mismatch and locate matching local or official Espressif documentation. Never silently
answer from v6.0.2.

## Search the Source Documentation

The `docs` directory contains Sphinx/RST source, not fully rendered pages. Search both languages,
prefer English when translations disagree, and follow adjacent sections and included files:

```powershell
rg -n --glob '*.rst' --glob '*.inc' '<API-or-topic>' "$idfRoot\docs\en"
rg -n --glob '*.rst' --glob '*.inc' '<API-or-topic>' "$idfRoot\docs\zh_CN"
```

Interpret `only::` conditions using the exact `IDF_TARGET` and SoC capability macros. Resolve
chip-specific `.inc` substitutions such as `{IDF_TARGET_PATH_NAME}`. An `include-build-file`
directive points to generated Doxygen material that may not exist in the source tree.

For a generated declaration, verify the matching component header and implementation from the same
IDF root:

```powershell
rg -n --glob '*.h' --glob '*.c' '<symbol>' "$idfRoot\components"
rg -n --glob 'Kconfig*' '<CONFIG_SYMBOL>' "$idfRoot"
```

For Kconfig behavior, also inspect the project's `sdkconfig`, `sdkconfig.defaults*`, and resolved
build configuration. Examples demonstrate usage but are not a substitute for the API contract.

## Source Ownership

Use version-matched ESP-IDF docs and source for APIs, component behavior, Kconfig, build rules,
migration notes, and examples. Use the exact-chip datasheet, TRM, hardware design guidelines, and
errata for registers, bit fields, pins, straps, electrical limits, timing, RF, and hardware safety.
Verify those hardware claims against the hash-matched original PDF page through the local ESPDocs
workflow. Report discrepancies instead of combining incompatible claims.
