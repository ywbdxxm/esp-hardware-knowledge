---
name: esp32-ai-hardware-engineering
description: "Use when any task concerns ESP32 or ESP-IDF firmware, hardware, documentation research, datasheets or TRMs, embedded C/C++, FreeRTOS, board or peripheral integration, audio, networking, protocols, OTA, NVS, partitions, Kconfig, CMake, build, flash, debug, or hardware validation."
---

# ESP32 AI Hardware Engineering

## Overview

Treat ESP32 work as a constrained concurrent product system grounded in the exact chip, board,
ESP-IDF version, and authoritative source evidence.

## Workflow

1. Read the closest `AGENTS.md`, project documentation, board configuration, and neighboring code.
2. Establish the chip, board identity, `IDF_TARGET`, ESP-IDF version, flash/PSRAM/partition layout,
   peripherals, transport, and available physical validation. Mark unknowns instead of assuming.
3. For ESP-IDF APIs, Kconfig, build behavior, migration, or examples, read
   [esp-idf-local-docs.md](references/esp-idf-local-docs.md) and use documentation and source from
   the project's exact ESP-IDF version.
4. For documentation research, registers, pins, timing, electrical characteristics, or hardware
   design, read [local-document-retrieval.md](references/local-document-retrieval.md) and locate
   evidence before deciding or coding.
5. Map a change to the narrowest owner: application state, board capability, audio pipeline,
   protocol semantics, transport, MCP tool, persistence, assets, or build metadata.
6. State invariants: single writer, legal transitions, task/driver owner, queue capacity and full
   policy, cancellation or stale-result rule, persistent compatibility, and unavailable behavior.
7. Read [architecture-patterns.md](references/architecture-patterns.md) for boundaries,
   concurrency, product-line, protocol, ownership, or lifecycle decisions.
8. Read the relevant sections of
   [implementation-checklists.md](references/implementation-checklists.md) before implementation
   and again before completion.
9. Implement the smallest coherent change. Preserve board identities and unrelated variants; keep
   core modules independent of concrete board configuration.
10. Verify in layers: source evidence, host tests and static checks, representative builds and
   transports, then physical hardware behavior. Report each layer separately.

## Quick Reference

| Change | First question | Required reference |
| --- | --- | --- |
| ESP-IDF API, Kconfig, build, or migration | Which IDF version and `IDF_TARGET`? | Local ESP-IDF docs |
| Documentation or hardware fact | Which chip, document version, and original PDF page? | Local document retrieval |
| State or concurrency | Who is the sole writer or driver owner? | Architecture patterns 2, 3, 7, 8 |
| Board or peripheral | Is this a new identity or optional capability? | Architecture patterns 4, 5 |
| Audio | What is each queue's time budget and full policy? | Architecture pattern 6 + Audio checklist |
| Protocol or MCP | Which semantics are shared across transports? | Architecture patterns 9, 10 |
| OTA, NVS, or assets | Which compatibility API or lifecycle changes? | Architecture pattern 11 |

## Non-Negotiables

- Route device mutations to one main task; callbacks publish bounded events or commands.
- Never leave a realtime queue unbounded or without a full policy.
- Give non-thread-safe drivers one owning task; defer controls and resets to that owner.
- Reject results from old sessions or modes with a generation check when cancellation cannot stop work.
- Treat board identity, NVS keys, protocol messages, partitions, and asset formats as compatibility APIs.
- Validate every transport sharing changed protocol semantics.
- Never use documentation from a different ESP-IDF version without reporting the mismatch.
- Verify registers, electrical values, pins, timing, security, tables, and diagrams against the
  hash-checked original PDF page. Generated Markdown is a locator, not final authority.
- A successful compile is not hardware validation.

## Common Mistakes

- Answering a C3 question from an S3 result or omitting the exact chip filter.
- Copying a reference implementation without re-deriving timing and memory budgets.
- Adding board-specific branches to core code instead of a capability implementation.
- Holding locks across driver calls, logs, callbacks, or blocking waits.
- Testing only one board, transport, display path, or AEC mode.
- Reporting tests as passing when warnings, skipped hardware, or stale generated state remain.
