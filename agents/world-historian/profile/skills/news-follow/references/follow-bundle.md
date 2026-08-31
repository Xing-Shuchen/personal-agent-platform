# Follow bundle fields

Persist with:

```bash
"$PAP_ROOT/.venv/bin/python" \
  "$PAP_ROOT/agents/world-historian/runtime/cli.py" store-bundle --json <path>
```

Use `search` and `thread` first, then identify existing objects by ID. A follow
bundle normally contains `sources`, `events`, and `claims`; an event attaches to
one or more existing threads through `thread_refs`.

To revise a report, upsert the old claim ID with `status: superseded` or
`disputed` and, when known, `superseded_by`; insert the new claim separately.
Never replace the old statement. To close an investigation question, include a
top-level `questions` item with `thread_ref`, the same `question`,
`status: answered`, and `answer_event_ref`.

Potential expansions belong in `discovery_candidates` with `candidate_type`,
`title`, `relation_score`, `payload`, and `status: candidate`. Promote them to
threads only within the expansion budget.
