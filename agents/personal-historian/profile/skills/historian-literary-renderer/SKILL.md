---
name: historian-literary-renderer
description: Turn one validated PeriodSummary into a concise human-facing narrative Markdown view without adding facts.
---

# Render a PeriodSummary for a human reader

Read `../../references/epistemology.md` and `references/weekly.md` before
writing. The invocation supplies one canonical, validated PeriodSummary. It is
the complete factual boundary for this task.

Return one Markdown document with YAML Properties followed by the narrative.
Do not return JSON, commentary, citations, artifact IDs,
coverage tables, schema fields, or an audit inventory. Do not run commands or
write files; the runtime owns the projection into PAP state and Obsidian.

Find the period's human-scale shape: one main thread, then only the secondary
thread or background condition needed to understand it. Prefer concrete scenes,
chronology, decisions, relationships, reversals, and felt experience that the
canonical summary actually supports. Activity volume is not a story.

You may reorganize and compress canonical claims, but MUST NOT introduce a new
fact, causal link, motive, emotional state, quotation, outcome, or thread state.
Keep testimony as testimony when its truth is not independently established.
Carry a material uncertainty or contradiction into natural prose when omitting
it would change the reader's understanding; do not dump boilerplate caveats.

The result is a replaceable view, never canonical history.
