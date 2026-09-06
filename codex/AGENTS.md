# Global Codex Instructions

## Context First

Read the closest project `AGENTS.md`, authoritative project documentation, configuration, component
identity, and relevant source before acting. Project-selected identities and versions override
ambient tools and global defaults. Keep machine paths, installed versions, corpus locations, and
commit IDs out of reusable instructions.

## Skill Routing

- For source-grounded semiconductor or electronic-component facts from a datasheet, technical reference
  manual, errata, application note, or design guide, you MUST use
  `hardware-document-research`.
- For ESP32 or ESP-IDF engineering, including firmware, board integration, build, flash, debug, or
  validation, you MUST use `esp32-ai-hardware-engineering`. Also use
  `hardware-document-research` when the task depends on hardware-document facts.
- For PDF reading, extraction, conversion, OCR, tables, figures, or reusable corpora, you MUST use
  `docling-local-document-engineering` and its adaptive document path.
- Also use `pdf:pdf` when original-page rendering, visual inspection, forms, PDF authoring, editing,
  or final layout QA is required.

Apply every route that matches. Each Skill owns its domain decisions; project rules refine them.

## Evidence Invariants

Resolve the exact identity and applicable revision instead of substituting a related target. Verify
critical values, pins, registers, timing, safety behavior, tables, figures, and ambiguous extraction
against the authoritative source locator. Generated text and search results are locators, not final
evidence.
