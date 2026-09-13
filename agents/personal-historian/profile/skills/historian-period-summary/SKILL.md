---
name: historian-period-summary
description: Synthesize exactly one ContextPack into a provenance-bound PeriodSummary JSON document.
---

# Produce a PeriodSummary

Read `../../references/epistemology.md`,
`../../references/historian-terminology.md`, and the period-specific reference
under `references/` before synthesizing.

The invocation input is exactly one validated `historian.context-pack.v1`. It has
already been prepared and sealed. Your reply **is** the artifact: return exactly
one `historian.period-summary.v1` JSON document as your final message, and
nothing else.

Use only ContextPack content. Preserve coverage gaps, contradictions, and
distinctions between observation, testimony, Event reconstruction, and prior
summary. Do not invent events, causality, decisions, psychological states, or
continuity. `basis_refs` must refer only to selected ContextPack artifacts. The
period must match the ContextPack exactly. `summary_id` and `revision` are fixed
by the invocation input: copy them verbatim.

Your reply is the only thing you produce. Do not run commands, do not invoke
`historian summary prepare/validate/commit/render`, do not write or edit any
file, and do not modify, commit to, or push any repository. The runtime
validates your reply, seals its provenance, allocates the revision, commits it
as the canonical artifact, and renders the Markdown view — a document you commit
yourself bypasses all of that and its provenance would be a claim no runtime can
substantiate. If the invocation input says readiness is not met, return exactly
`NOT_READY`. Never store canonical history only in PAP `var/`.
