# Output contract

Return exactly one bare `historian.period-summary.v1` JSON object, with no prose
and no Markdown around it. The schema is strict and rejects unknown fields, so
send exactly the fields below.

## Identity and period

| field | value |
|---|---|
| `schema_version` | `"1.0.0"` |
| `artifact_type` | `"historian.period-summary.v1"` |
| `summary_id` | the id supplied to you — echo it verbatim |
| `revision` | the revision supplied to you — echo it verbatim |
| `domain` | the domain supplied in the ContextPack |
| `created_at` | ISO-8601 timestamp with an offset |
| `period` | the ContextPack's `period` object, copied exactly |
| `status` | `complete`, `partial` or `insufficient_evidence` |

`complete` means the period is fully accounted for. Use `partial` when coverage
gaps or unresolved contradictions remain, and `insufficient_evidence` when the
material does not support a synthesis at all.

## Content

| field | shape |
|---|---|
| `headline` | one line naming the period |
| `overview` | the period's account |
| `historical_claims` | `{statement, basis_refs[, qualification]}`; at least one basis ref each |
| `threads` | artifact refs to the ThreadCards this period bears on |
| `landmark_events` | artifact refs to the events that define the period |
| `decisions` | list of strings |
| `state_changes` | list of strings |
| `cognitive_changes` | list of strings |
| `subjective_patterns` | list of strings |
| `open_threads` | artifact refs |
| `contradictions` | list of strings — preserve them, never resolve them away |
| `evidence_gaps` | list of strings |
| `next_level_digest` | see below |
| `basis_refs` | artifact refs; at least one |
| `provenance` | object; the Historian replaces it with runtime-owned values |
| `content_hash` | the Historian recomputes this — emit the field, do not hand-compute it |

An artifact ref is `{"artifact_id": "...", "revision": N, "content_hash": "..."}`
taken from the ContextPack. Never invent an id: `basis_refs`, `threads`,
`landmark_events` and `open_threads` may name only artifacts the ContextPack
actually offered.

## `next_level_digest`

This is not a shorter `overview`. It is the compact representation the **parent**
level reads instead of this summary, so it must carry forward, compressed:

- major state transitions
- major decisions
- thread lifecycle changes
- inflection points
- important unresolved issues

Drop incidental narrative detail; never drop one of those five to make room for
it. The period-specific reference for your level gives the approximate length —
a soft target, so prefer a slightly short digest that keeps all five over a long
one that keeps none.
