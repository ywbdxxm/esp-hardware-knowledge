# Global Codex Instructions

## Project Context First

Read the closest project `AGENTS.md`, authoritative project documentation, board configuration,
component identity, and relevant source before making changes or selecting documentation. Project
rules refine these global routes. Keep machine-specific SDK paths, release numbers, document-library
paths, and commit IDs out of reusable global instructions.

## Hardware Document Research

For source-grounded facts about semiconductors or electronic components, you MUST use the global
Skill `hardware-document-research`. This includes datasheets, technical reference manuals, errata,
application notes, design guides, pins, packages, registers, electrical limits, timing, power, RF,
and hardware integration.

Resolve the exact part and revision rather than silently substituting a related device. For critical
values, pins, registers, timing, safety behavior, tables, figures, and ambiguous extraction, inspect
the hash-matched authoritative source locator. Generated Markdown and search snippets are locators,
not final evidence.

## ESP32 Engineering

For any ESP32 or ESP-IDF task, you MUST use the global Skill
`esp32-ai-hardware-engineering` before analyzing, planning, implementing, debugging, reviewing, or
answering technical questions. This covers firmware, embedded C/C++, FreeRTOS, board and peripheral
integration, audio, networking, protocols, OTA, NVS, partitions, CMake, Kconfig, build, flash, debug,
hardware validation, and ESP32 documentation research.

Use the project-selected ESP-IDF revision and exact `IDF_TARGET`; ambient shell state, a global SDK
selection, and the newest installed SDK are fallback evidence only. For ESP32 hardware-document
facts, use both `esp32-ai-hardware-engineering` and `hardware-document-research`.

Do not trigger the ESP32 Skill for unrelated desktop, web, data, or generic C++ work without ESP32
or embedded-hardware context.

## Document Format Processing

For PDF reading, analysis, extraction, conversion, OCR, tables, figures, or reusable local document
corpora, you MUST use `docling-local-document-engineering`. It chooses an adaptive native-text,
layout, or OCR path and preserves physical-page traceability.

Also use `pdf:pdf` for original-page rendering and visual inspection, forms, PDF creation or editing,
and final layout QA. Do not trigger Docling for creation- or forms-only work that does not read PDF
source content. For hardware research, Docling owns document processing while
`hardware-document-research` owns part identity, source selection, and evidence decisions.
