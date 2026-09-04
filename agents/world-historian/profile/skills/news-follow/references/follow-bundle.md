# Follow bundle fields

Persist with:

```bash
"/home/xingzeng/personal-agent-platform/.venv/bin/python" \
  "/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" store-bundle --json <path>
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

When a committed bundle modifies an existing thread (attached events, claim
changes, answered questions, watch queries), the runtime automatically
re-renders that thread's Obsidian file — no extra step is needed. Bundles
that touch no thread write nothing.
