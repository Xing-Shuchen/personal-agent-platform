---
name: historian-thread-card
description: Update an existing, immutable historical thread from EventCards and summaries.
---

# Update a ThreadCard

The input provides a registered ThreadCard identity plus selected EventCards,
period summaries, and evidence references. Return exactly one
`historian.thread-card.v1` JSON document.

Keep `thread_id` unchanged. Do not create a thread merely because labels are
similar. Temporary silence does not establish abandonment. State `completed`,
`abandoned`, or `superseded` only when the supplied evidence supports it.
Return JSON only; cite supplied artifacts in provenance and evidence refs.
