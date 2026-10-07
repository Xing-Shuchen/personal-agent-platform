---
name: event-format-backfill
description: Backfill concise timeline titles and readable Markdown bodies for existing World Historian events in exactly one thread.
---

# Backfill one Thread's event formatting

The input is exactly one existing Chronicle Thread ID. Operate on that Thread
only. This is a presentation-only enrichment: do not research the web, change
claims, alter event times/status/confidence, edit relations/questions/queries,
or create/delete events.

Read its full current state:

```bash
"$PAP_ROOT/.venv/bin/python" \
  "$PAP_ROOT/agents/world-historian/runtime/cli.py" \
  thread <thread_id>
```

For every returned event, create a replacement event object containing its
existing `id`, `occurred_at`, `occurred_at_precision`, `reported_at`,
`observed_at`, `confidence`, and `status`, plus the rewritten `title` and
`summary`. Persist all replacements in one bundle with `store-bundle --json`.
Use the existing event ID exactly; omit `thread_refs`. The runtime's event
upsert overwrites those metadata fields, so they must be carried through
verbatim even though this is a presentation-only change.

## Editorial contract

- `title`: a specific, compact Chinese timeline label, maximum 60 characters.
  It names the development, not its source list, evidence chain, qualifications,
  or a compressed version of the whole body.
- `summary`: readable Markdown body beneath the title. Preserve every material
  fact, date, quantity, uncertainty, attribution, caveat, and distinction from
  the old summary. Split independent developments into short paragraphs; use a
  numbered or bulleted list for several distinct findings. Do not use Markdown
  headings in the body and never introduce information not in the old summary.
- Never turn a reported claim into a fact. Keep terms such as "据报", "称",
  "未证实", "官方口径", "第三方", and source attributions when they occur.
- Do not modify a summary that is already clearly structured unless it still
  lacks a title; preservation beats stylistic churn.

After the bundle commits successfully, re-render this Thread only:

```bash
"$PAP_ROOT/.venv/bin/python" \
  "$PAP_ROOT/agents/world-historian/runtime/cli.py" \
  sync --thread <thread_id>
```

Return a compact report containing the Thread ID, number of events updated,
and the sync result. If any event cannot be rewritten without losing meaning,
leave it untouched and state its ID rather than guessing.
