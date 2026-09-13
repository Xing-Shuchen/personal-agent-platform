---
name: historian-period-summary
description: Synthesize exactly one ContextPack into a provenance-bound PeriodSummary JSON document.
---

# Produce a PeriodSummary

Read `../../references/epistemology.md`,
`../../references/historian-terminology.md`, and the period-specific reference
under `references/` before synthesizing.

The invocation input is exactly one validated `historian.context-pack.v1`.
Return exactly one `historian.period-summary.v1` JSON document and no prose.

Use only ContextPack content. Preserve coverage gaps, contradictions, and
distinctions between observation, testimony, Event reconstruction, and prior
summary. Do not invent events, causality, decisions, psychological states, or
continuity. `basis_refs` must refer only to selected ContextPack artifacts. The
period must match the ContextPack exactly.

The Historian owns persistence. Use its `historian summary prepare`,
`historian summary validate`, `historian summary commit`, and
`historian summary render` operations with the configured local Historian
checkout. If readiness is not met, return exactly `NOT_READY`; do not produce
or commit a summary. Never store canonical history only in PAP `var/`.
