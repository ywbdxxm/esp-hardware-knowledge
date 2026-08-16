# Codex Data Root and ESP32 Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the complete local ESPDocs runtime under the source documentation tree, make the path portable, deploy a Codex-only ESP32 workflow, then merge and publish the repository.

**Architecture:** `AppPaths.discover` resolves an explicit `ESPDOCS_DATA_ROOT`, then a detected `docs` library, then the existing LocalAppData fallback. Canonical Codex assets live in Git and are copied to the global Codex directory after deterministic tests and skill validation.

**Tech Stack:** Python 3.13, uv, pytest, Ruff, PowerShell 7, Codex Skills, Git, GitHub CLI over SSH.

---

### Task 1: Resolve the Documentation Data Root

**Files:**
- Modify: `tests/test_config.py`
- Modify: `src/espdocs/config.py`
- Modify: `README.md`

- [ ] Add tests proving `ESPDOCS_DATA_ROOT` wins and an ancestor containing both configured ESP32 source directories selects `docs/esp-hardware-knowledge-data`.
- [ ] Run `uv run pytest tests/test_config.py -v` and confirm the new tests fail against the LocalAppData-only implementation.
- [ ] Add `data_root` support to `AppPaths.from_roots` and the ordered explicit/library/fallback resolution to `AppPaths.discover`.
- [ ] Run the focused tests and update README paths, migration behavior, and environment-variable precedence.

### Task 2: Add Canonical Codex Assets

**Files:**
- Create: `tests/test_codex_assets.py`
- Create: `codex/AGENTS.md`
- Create: `skills/esp32-ai-hardware-engineering/SKILL.md`
- Create: `skills/esp32-ai-hardware-engineering/agents/openai.yaml`
- Copy and modify: `skills/esp32-ai-hardware-engineering/references/*.md`
- Create: `skills/esp32-ai-hardware-engineering/references/local-document-retrieval.md`

- [ ] Add failing tests that require the global trigger rule, Codex implicit invocation metadata, local `espdocs` workflow, chip filtering, and original-PDF evidence policy.
- [ ] Run `uv run pytest tests/test_codex_assets.py -v` and confirm missing canonical assets fail.
- [ ] Copy the existing skill into the repository, broaden only its ESP32 trigger and local evidence workflow, and add the Codex AGENTS template.
- [ ] Run the focused test plus `quick_validate.py skills/esp32-ai-hardware-engineering`.

### Task 3: Deploy and Migrate Local State

**Files outside Git:**
- Update: `%USERPROFILE%/.codex/AGENTS.md`
- Update: `%USERPROFILE%/.codex/skills/esp32-ai-hardware-engineering/`
- Move: `%LOCALAPPDATA%/esp-hardware-knowledge/`
- To: `%USERPROFILE%/Desktop/AI-HRADWARE/docs/esp-hardware-knowledge-data/`

- [ ] Verify the resolved source and destination are exact, the destination is absent, and the source contains 10 documents and a healthy index.
- [ ] Move the runtime with one PowerShell `Move-Item -LiteralPath` operation and set the user-level `ESPDOCS_DATA_ROOT`.
- [ ] Deploy canonical Codex files with file-for-file copies, then compare hashes with the repository versions.
- [ ] Run `espdocs doctor --json` and `espdocs verify --json` against the migrated location.

### Task 4: Verify, Merge, and Publish

**Files:**
- Commit all intended repository changes only.

- [ ] Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q`, `espdocs doctor`, `espdocs verify`, `git diff --check`, and tracked-file hygiene checks.
- [ ] Commit the feature branch, merge it into `main`, sync the main uv environment, and rerun the full verification from main.
- [ ] Remove the owned feature worktree and merged branch only after the main verification passes.
- [ ] Create public `ywbdxxm/esp-hardware-knowledge`, configure SSH `origin`, push `main`, and verify visibility, remote HEAD, and clean status.
