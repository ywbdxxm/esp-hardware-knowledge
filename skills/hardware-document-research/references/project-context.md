# Project Context and Discovery

## Resolve Component Identity

Read the closest project `AGENTS.md`, schematic or BOM data, board configuration, and relevant source
before selecting document filters. Distinguish the chip from a module or board and capture:

- vendor, family, and exact orderable part;
- package or module variant and silicon revision when they affect behavior;
- document type, language, revision, and publication date;
- the project function and connected signals that constrain interpretation.

Treat an incomplete marking, family name, filename, or nearby component as insufficient proof of an
exact part. Report unknown or conflicting identity instead of choosing the closest indexed device.

## Cross-Machine Launcher

The installed `scripts/invoke-espdocs.ps1` launcher resolves the repository root in this order:

1. process-level `ESP_HARDWARE_KNOWLEDGE_ROOT`;
2. user-level `ESP_HARDWARE_KNOWLEDGE_ROOT`;
3. one unambiguous current-directory or ancestor project containing `pyproject.toml`, `uv.lock`, and
   `src/espdocs`.

It invokes `uv run --locked --project <resolved-root> espdocs`; a missing bare `espdocs` command is
normal. Do not install a global copy or use an unrelated Python environment when discovery fails.

`ESP_HARDWARE_KNOWLEDGE_ROOT` identifies the Git repository. `ESPDOCS_SOURCE_BASE` identifies the
original document library, and `ESPDOCS_DATA_ROOT` identifies generated corpus, index, render, cache,
and log data. Keep these responsibilities separate and configure machine-specific absolute paths as
Windows user variables rather than embedding them in Skills or project files.

When the launcher reports a missing, incomplete, or ambiguous repository root, fix discovery or use
an authoritative official-vendor source with the limitation disclosed. Never select one ambiguous
candidate silently.
