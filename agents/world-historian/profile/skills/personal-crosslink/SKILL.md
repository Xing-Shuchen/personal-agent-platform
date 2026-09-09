---
name: personal-crosslink
description: Link public Chronicle events to read-only personal history using a fixed local contract.
---

# Cross-link world history to personal history

This is a bounded local-linking job. Never explore the filesystem, discover
alternate paths/databases, inspect source code, or call web tools.

Read only these fixed references first:

```text
/home/xingzeng/personal-agent-platform/agents/world-historian/profile/skills/personal-crosslink/references/privacy-boundary.md
/home/xingzeng/personal-agent-platform/agents/world-historian/profile/skills/personal-crosslink/references/personal-link-bundle.md
```

## Fixed local contract

Use these exact paths; never list, search, probe, or infer alternatives:

```text
PYTHON=/home/xingzeng/personal-agent-platform/.venv/bin/python
CLI=/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py
CHRONICLE_DB=/home/xingzeng/personal-agent-platform/var/world-historian/chronicle.sqlite
PERSONAL_TODAY=/home/xingzeng/personal-historian-handoff/examples/live-run/personal/today/observations.json
PERSONAL_PREHISTORY=/home/xingzeng/personal-historian-handoff/examples/live-run/personal/prehistory/observations.json
PERSONAL_PLATFORM=/home/xingzeng/personal-historian-handoff/examples/live-run/personal/platform-history/observations.json
BUNDLE_DIR=/home/xingzeng/personal-agent-platform/var/world-historian
```

The only personal inputs are the three `PERSONAL_*` files. Never open diaries,
Obsidian, messages, calendars, browser databases, legacy aggregate files, or
other personal sources.

The fixed Chronicle schema is:

```sql
events(id TEXT PRIMARY KEY, summary TEXT NOT NULL, occurred_at TEXT,
       occurred_at_precision TEXT, reported_at TEXT, observed_at TEXT NOT NULL,
       confidence REAL NOT NULL, status TEXT NOT NULL)
personal_links(id TEXT PRIMARY KEY, world_event_id TEXT NOT NULL,
       personal_event_id TEXT NOT NULL, relation_type TEXT NOT NULL,
       explanation TEXT NOT NULL, confidence REAL NOT NULL,
       evidence_json TEXT NOT NULL, created_at TEXT NOT NULL,
       updated_at TEXT NOT NULL,
       UNIQUE(world_event_id, personal_event_id, relation_type))
```

`events` is read-only. Write `personal_links` only through `store-bundle`;
never write SQLite directly or inspect schema/migrations/source.

## Personal lookup boundary

The approved local lookup adapter is:

```text
/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/personal_lookup.py
```

It reads exactly the three `PERSONAL_*` files and the local Chronicle, then
returns only `observation_id`, `kind`, `domain`, a coarse time bucket, public
topic terms, a minimal descriptor, and record-ID evidence. Do not replace it,
pass it alternative paths, or inspect the personal files directly.

The model may receive only `observation_id`, `kind`, `domain`, a coarse time
bucket, and a minimal redacted descriptor. Raw `statement`, `facts`,
`source_evidence`, and `normalization` must never enter model context.

## Scheduled procedure

1. Read the two fixed references.
2. Obtain at most 10 privacy-redacted local candidates with this exact command:

```bash
"/home/xingzeng/personal-agent-platform/.venv/bin/python" \
  "/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/personal_lookup.py" \
  --limit 10
```

3. Inspect at most 10 redacted candidates and create at most five
   evidence-backed links. Treat the adapter result as a candidate, not proof:
   persist only when its public topic terms and the public Chronicle event make
   the proposed relation plausible. Never use private wording as a query.
   Never call web tools.
4. Check duplicates only with this exact query, replacing the placeholders:

```bash
sqlite3 "file:/home/xingzeng/personal-agent-platform/var/world-historian/chronicle.sqlite?mode=ro" \
  "SELECT 1 FROM personal_links
    WHERE world_event_id = 'WORLD_EVENT_ID'
      AND personal_event_id = 'PERSONAL_EVENT_ID'
    LIMIT 1;"
```

5. Write a nonempty bundle only to:

```text
/home/xingzeng/personal-agent-platform/var/world-historian/personal-link-bundle-YYYYMMDD.json
```

It must have a top-level `personal_links` list with
`world_event_ref`, `personal_event_id`, an allowed relation type,
`explanation`, `confidence`, and record-ID evidence only.

6. Persist only a nonempty bundle with exactly:

```bash
"/home/xingzeng/personal-agent-platform/.venv/bin/python" \
  "/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" \
  --db "/home/xingzeng/personal-agent-platform/var/world-historian/chronicle.sqlite" \
  store-bundle --json \
  "/home/xingzeng/personal-agent-platform/var/world-historian/personal-link-bundle-YYYYMMDD.json"
```

7. Finish with exactly `NO_REPLY`, whether or not a link was created.

## Hard stops

Never run `ls`, `find`, `rg`, `grep`, `git`, `--help`, schema inspection,
path probing, automation/session inspection, workspace-memory reads, broad
repository searches, runtime-source reads, or historical-bundle reads. If a
fixed path, schema, or adapter contract fails, stop with `NO_REPLY`.
