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
