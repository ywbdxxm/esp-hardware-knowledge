# Codex Data Root and ESP32 Skill Design

## Goal

Keep the complete ESPDocs runtime beside the local source library under
`docs/esp-hardware-knowledge-data`, while publishing only code, configuration, tests,
documentation, and Codex workflow assets to a public GitHub repository.

## Data Boundary

`ESPDOCS_DATA_ROOT` is the explicit override. Without it, ESPDocs searches the repository and
its ancestors for both `docs/ESP32-C3` and `docs/ESP32-S3`; when found, it uses the sibling
`docs/esp-hardware-knowledge-data`. `%LOCALAPPDATA%/esp-hardware-knowledge` remains the fallback
for clones without the local source-library layout.

The whole runtime moves as one unit so corpus Markdown, image assets, SQLite paths, rendered
source pages, and backups remain consistent. Generated data and PDFs stay excluded from Git.

## Codex Boundary

The repository owns canonical Codex assets under `codex/` and `skills/`. Deployment copies them
to `%USERPROFILE%/.codex/AGENTS.md` and `%USERPROFILE%/.codex/skills/` on this machine. No Claude,
OpenCode, or Hermes adapter is added in this phase.

The global AGENTS rule forces the ESP32 skill for firmware, documentation research, hardware
questions, build, flash, debug, and validation. The skill uses `espdocs` as the preferred local
locator and requires hash-verified original-PDF pages for registers, electrical values, pins,
security, timing, tables, and diagrams.

## GitHub Delivery

Merge `feature/espdocs-phase-one` into `main`, create the public repository
`ywbdxxm/esp-hardware-knowledge`, configure its SSH remote, and push only the verified main
branch. Verify the remote visibility and tracked-file hygiene after pushing.

## Verification

- Unit tests cover data-root precedence and required Codex asset contents.
- Skill metadata passes the Codex skill validator.
- Ruff and the full pytest suite pass.
- `espdocs doctor --json` and `espdocs verify --json` pass after the physical data move.
- Git tracks no PDF, corpus, render, backup, model, or SQLite artifact.
