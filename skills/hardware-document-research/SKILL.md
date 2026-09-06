---
name: hardware-document-research
description: "Use when answering source-grounded questions about semiconductor or electronic-component datasheets, reference manuals, errata, application notes, design guides, pins, electrical limits, timing, registers, packages, or hardware integration. Do not use for generic software work or PDF authoring."
---

# Hardware Document Research

Use a context-driven evidence contract for any vendor or component family:

1. Resolve the project context and exact part or component identity. Mark unknown fields instead of
   substituting a related device.
2. Discover the available corpus, query capabilities, and valid identity filters; do not assume a
   particular machine, library, or indexed part.
3. Query within the narrowest verified identity and document scope. Treat an exact-scope miss as a
   gap, not permission to broaden silently.
4. Verify critical claims against the authoritative source locator. Generated text is a locator,
   not final evidence.

Read [project-context.md](references/project-context.md) when identity, project ownership, or
cross-machine discovery matters. Read [evidence-workflow.md](references/evidence-workflow.md) for
local lookup, source grading, no-match handling, and authoritative fallback.
