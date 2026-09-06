# ESPDocs Repository Instructions

- Treat this repository as the canonical source for `codex/` and `skills/` assets.
- Do not deploy until source Skills validate and destination drift has been checked.
- Keep PDFs, corpus data, indexes, renders, caches, logs, virtual environments, and backups out of Git.
- Preserve schema-v1 CLI fields and the existing runtime until compatibility and golden tests pass.
- Use failing tests first for code, configuration, deployment, or Skill-contract changes.
- Run targeted tests, Ruff, the full test suite, all managed Skill validators, `espdocs doctor --json`, and `espdocs verify --json` before completion.
- Never answer critical hardware facts from generated Markdown alone; verify the hash-matched original source locator.
