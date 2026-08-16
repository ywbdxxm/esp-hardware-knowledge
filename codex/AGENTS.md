# Global Codex Instructions

## Required Skill for ESP32 Work

For any task whose subject is ESP32 or ESP-IDF, you MUST use the global Skill
`esp32-ai-hardware-engineering` before analyzing, planning, implementing, debugging, reviewing,
or answering technical questions.

This includes firmware and embedded C/C++, FreeRTOS, board/BSP integration, peripherals, audio,
displays, cameras, power, networking, protocols, OTA/NVS/partitions, CMake/Kconfig, build, flash, debug,
hardware validation, and documentation research involving datasheets, technical reference manuals,
design guidelines, registers, pins, timing, or electrical characteristics.

Load the Skill from `%USERPROFILE%\.codex\skills\esp32-ai-hardware-engineering\SKILL.md`. Read the
Skill reference matching the subsystem. For documentation or hardware facts, read
`references/local-document-retrieval.md` and use the local `espdocs` workflow when healthy.

Also read the closest project `AGENTS.md`, authoritative project documentation, board
configuration, and relevant source before making changes. Project rules refine this global rule.

If the Skill or local knowledge CLI is unavailable, state that explicitly. For safety-critical or
version-sensitive facts, inspect the authoritative original PDF rather than relying on memory,
search snippets, or generated Markdown alone.

Do not trigger this Skill for unrelated desktop, web, data, or generic C++ work without ESP32 or
embedded-hardware context.

## Required Skill for PDF Research

For PDF reading, analysis, extraction, conversion, OCR, tables, figures, or reusable local document
corpora, you MUST use the global Skill `docling-local-document-engineering`. It applies an adaptive
route: trustworthy native text may use direct extraction, while scans, complex layout, or long
documents use local Docling processing.

Load the Skill from
`%USERPROFILE%\.codex\skills\docling-local-document-engineering\SKILL.md`. Keep the original file and
physical-page traceability. Critical facts, tables, figures, and ambiguous OCR must be checked against
the hash-matched original PDF page.

Also use `pdf:pdf` for original-page rendering and visual inspection, forms, PDF creation or editing,
and final layout QA. The Docling Skill complements rather than replaces that capability. Do not
trigger Docling for a creation- or forms-only task that does not require reading source PDF content.
