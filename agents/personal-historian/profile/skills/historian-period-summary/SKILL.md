---
name: historian-period-summary
description: Synthesize exactly one ContextPack into a provenance-bound PeriodSummary JSON document.
---

# Produce a PeriodSummary

The invocation input is exactly one validated `historian.context-pack.v1`.
Return exactly one `historian.period-summary.v1` JSON document and no prose.

Use only ContextPack content. Preserve coverage gaps, contradictions, and
distinctions between observation, testimony, Event reconstruction, and prior
summary. Do not invent events, causality, decisions, psychological states, or
continuity. `basis_refs` must refer only to selected ContextPack artifacts. The
period must match the ContextPack exactly.
