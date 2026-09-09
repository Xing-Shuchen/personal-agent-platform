# One-way personal-history privacy boundary

The allowed flow is:

```text
public Chronicle event
        -> local personal-history lookup
        -> PersonalLink
```

The forbidden flow is:

```text
private diary, message, calendar, or personal observation
        -> internet search query, external LLM prompt, or public log
```

Hard rules:

- Start every lookup from a public Chronicle event already stored locally.
- Never turn private wording, names, projects, employers, health information,
  locations, or relationships into a web query.
- Personal-history access is read-only. Never revise personal records from this
  skill.
- The approved adapter must perform retrieval locally and return only record
  IDs plus minimal redacted relation descriptors. Do not open raw diary,
  message, calendar, health, or personal-history text in the OpenClaw model
  context. If that adapter is unavailable, create no link and finish silently.
- Persist personal record IDs and a minimal explanation, not copied diary text.
- If relevance can only be tested by exposing private text externally, do not
  test it; leave the link unresolved.
- Mark inference and confidence explicitly. Lexical overlap alone is not a
  PersonalLink.

Supported relation types are: `experienced`, `affected_by`, `worked_on`,
`discussed`, `read_about`, `anticipated`, `intellectual_context`,
`career_context`, `location_context`, `social_context`, and `later_recalled`.
