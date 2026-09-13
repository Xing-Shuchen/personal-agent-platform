---
name: historian-event-card
description: Compress exactly one reconstructed Event revision into a provenance-bound EventCard JSON document.
---

# Create an EventCard

Read `../../references/epistemology.md` and
`../../references/historian-terminology.md` before processing the input.

The invocation input contains one reconstructed Event revision, its exact
`event_ref`, and optional prior EventCard context. Return exactly one
`historian.event-card.v1` JSON document, with no Markdown or commentary.

Preserve the Event's uncertainty and evidence boundary. A browser visit proves
only a recorded visit; a commit proves only recorded commit facts; testimony is
testimony. Never add motivations, completion claims, or continuity that the
Event does not support. The output must use the supplied `event_ref` verbatim,
retain evidence references, and must not make the card more authoritative than
its Event.

## Output contract

Return exactly one `historian.event-card.v1` object; unknown fields are rejected.
Send exactly these fields:

`schema_version` ("1.0.0"), `artifact_type` ("historian.event-card.v1"),
`event_card_id` and `revision` (echo the supplied values verbatim),
`domain`, `created_at` (ISO-8601 with offset), `event_ref` (the supplied ref,
verbatim), `title`, `digest`, `time` (`{start: {value, precision},
end: {value, precision}}`, copied from the Event), `event_type`,
`importance` (low|medium|high|landmark|unknown),
`confidence` (low|medium|high|unknown),
`subjective_salience` (low|medium|high|unknown), `thread_ids` (stable
`thread:` ids, or an empty list — never invent one), `decisions`,
`state_changes`, `open_consequences`, `contradictions`, `evidence_refs`
(at least one artifact ref, taken from the Event's evidence), `provenance`,
`content_hash`.

The Historian replaces `provenance` with runtime-owned values and recomputes
`content_hash`; emit both fields, but do not hand-compute the hash.
