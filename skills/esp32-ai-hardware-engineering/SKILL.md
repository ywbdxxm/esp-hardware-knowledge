---
name: esp32-ai-hardware-engineering
description: "Use when any task concerns ESP32 or ESP-IDF firmware, hardware, documentation research, datasheets or TRMs, embedded C/C++, FreeRTOS, board or peripheral integration, audio, networking, protocols, OTA, NVS, partitions, Kconfig, CMake, build, flash, debug, or hardware validation."
---

# ESP32 AI Hardware Engineering

## Overview

Treat ESP32 work as a constrained concurrent product system grounded in the exact chip, board,
project-selected ESP-IDF revision, and authoritative source evidence.

## Workflow

1. Read the closest `AGENTS.md`, project documentation, board configuration, and neighboring code.
2. Establish the chip, board identity, `IDF_TARGET`, required ESP-IDF revision,
   memory and partition layout, peripherals, transports, and available physical validation. Mark
   unknowns instead of assuming.
3. Load only the references required by the task:
   - Windows ESP-IDF command execution: read
     [windows-esp-idf-environment.md](references/windows-esp-idf-environment.md).
   - ESP-IDF API, Kconfig, build behavior, migration, or examples: read
     [esp-idf-local-docs.md](references/esp-idf-local-docs.md).
   - Registers, pins, timing, electrical characteristics, or hardware design: use
     `hardware-document-research` and read
     [local-document-retrieval.md](references/local-document-retrieval.md).
   - Boundaries, concurrency, product variants, protocols, ownership, or lifecycle: read
     [architecture-patterns.md](references/architecture-patterns.md).
   - Implementation or final verification: read only the relevant sections of
     [implementation-checklists.md](references/implementation-checklists.md).
4. Map the change to the narrowest owner and state the affected concurrency, compatibility, error,
   and unavailable-behavior invariants.
5. Implement the smallest coherent change while preserving unrelated board identities and variants.
6. Verify separately at the applicable layers: source evidence, host tests and static checks,
   representative builds and transports, and physical hardware behavior.

## Non-Negotiables

- Route device mutations to one main task; callbacks publish bounded events or commands.
- Never leave a realtime queue unbounded or without a full policy.
- Give non-thread-safe drivers one owning task; defer controls and resets to that owner.
- Reject results from old sessions or modes with a generation check when cancellation cannot stop work.
- Treat board identity, NVS keys, protocol messages, partitions, and asset formats as compatibility APIs.
- Validate every transport sharing changed protocol semantics.
- Use the project-selected target, SDK revision, and matching tool environment; treat ambient state
  as evidence rather than authority.
- Stop before build, flash, monitor, or debug when the required SDK, tools, target, and environment
  cannot be made mutually consistent.
- Never use documentation from a different ESP-IDF revision without reporting the mismatch.
- Verify registers, electrical values, pins, timing, security, tables, and diagrams against the
  hash-checked original PDF page. Generated Markdown is a locator, not final authority.
- A successful compile is not hardware validation.

## Common Mistakes

- Answering one chip, module, or board variant from a related target's result.
- Copying a reference implementation without re-deriving timing and memory budgets.
- Adding board-specific branches to core code instead of a capability implementation.
- Holding locks across driver calls, logs, callbacks, or blocking waits.
- Using whichever SDK or toolchain appears first instead of resolving project ownership.
- Testing only one board, transport, display path, or AEC mode.
- Reporting tests as passing when warnings, skipped hardware, or stale generated state remain.
