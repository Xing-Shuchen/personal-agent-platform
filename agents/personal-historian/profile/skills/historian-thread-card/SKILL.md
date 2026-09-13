---
name: historian-thread-card
description: Update an existing, immutable historical thread from EventCards and summaries.
---

# Update a ThreadCard

Read `../../references/epistemology.md` and
`../../references/historian-terminology.md` before processing the input.

The input provides a registered ThreadCard identity plus selected EventCards,
period summaries, and evidence references. Return exactly one
`historian.thread-card.v1` JSON document.

Keep `thread_id` unchanged. Do not create a thread merely because labels are
similar. Temporary silence does not establish abandonment. State `completed`,
`abandoned`, or `superseded` only when the supplied evidence supports it.
Return JSON only; cite supplied artifacts in provenance and evidence refs.

## Output contract

Return exactly one `historian.thread-card.v1` object; unknown fields are
rejected. Send exactly these fields:

`schema_version` ("1.0.0"), `artifact_type` ("historian.thread-card.v1"),
`thread_id` and `thread_card_id` (echo the supplied identity verbatim — it is
immutable), `revision` (echo the supplied value verbatim), `domain`,
`created_at` (ISO-8601 with offset), `canonical_name`, `aliases` (`[]` for a new
thread, or the names already registered to it), `status` (emerging|active|
accelerating|stable|declining|dormant|completed|abandoned|superseded|unknown),
`digest`, `trajectory`, `current_state`, `milestones`, `evidence_refs` (at least
one artifact ref to a supplied EventCard), `provenance`, `content_hash`.

When asked to propose a **new** thread, supply `canonical_name`; the Historian
derives `thread_id` and `thread_card_id` from it and overwrites whatever you
send, so the same process cannot acquire two identities. Cite at least two
distinct EventCards, and reply exactly `NO_NEW_THREAD` instead if they do not
evidence a persistent process.

The Historian replaces `provenance` with runtime-owned values and recomputes
`content_hash`; emit both fields, but do not hand-compute the hash.

Your reply is the only thing you produce. Do not run commands, do not write or
edit any file, and do not modify, commit to, or push any repository: the runtime
validates your reply, seals its provenance, allocates the revision, commits it as
the canonical artifact and renders the Markdown view (`historian summary` is the
runtime's interface, not yours).
