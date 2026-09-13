---
name: historian-event-card
description: Compress exactly one reconstructed Event revision into a provenance-bound EventCard JSON document.
---

# Create an EventCard

Read `../../references/epistemology.md` and
`../../references/historian-terminology.md` before processing the input.

The invocation input contains one or more reconstructed Event revisions, each
with its exact `event_ref`, `event_card_id` and `revision`, plus optional prior
EventCard context. Return one `historian.event-card.v1` document **per event**,
wrapped as `{"event_cards": [ ... ]}` with no Markdown or commentary: one card per
offered event, no extras, and none omitted. Cards are validated individually, so a
bad card is rejected and reported while the rest of the batch is committed — but a
batch in which nothing validates fails the run.

Preserve the Event's uncertainty and evidence boundary. A browser visit proves
only a recorded visit; a commit proves only recorded commit facts; testimony is
testimony. Never add motivations, completion claims, or continuity that the
Event does not support. Each output must use that event's supplied `event_ref`,
`event_card_id` and `revision` verbatim, retain evidence references, and must not
make the card more authoritative than its Event.

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
