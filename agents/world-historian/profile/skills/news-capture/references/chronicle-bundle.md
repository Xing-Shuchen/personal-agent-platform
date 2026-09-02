# Chronicle bundle format

Read this reference before calling `runtime/cli.py store-bundle`.

Use the runtime through:

```bash
"$PAP_ROOT/.venv/bin/python" \
  "$PAP_ROOT/agents/world-historian/runtime/cli.py" <command>
```

The input is one JSON object. Top-level keys are optional lists named:

```text
sources, entities, threads, events, claims, questions, watch_queries,
relations, interpretations, personal_links, discovery_candidates, reports,
quotes
```

Every item may have an `id`. If omitted, the runtime generates a stable ID
from its natural key. An item may also have a short `ref`; later items in the
same bundle can use that ref in `*_ref` fields. All writes commit atomically.

Minimum capture example:

```json
{
  "sources": [
    {
      "ref": "official",
      "canonical_url": "https://example.com/announcement",
      "title": "Official announcement",
      "publisher": "Example",
      "source_kind": "primary",
      "published_at": "2026-08-30T09:00:00+08:00",
      "fetched_at": "2026-08-31T12:00:00+08:00"
    }
  ],
  "threads": [
    {
      "ref": "thread",
      "title": "Example transition",
      "status": "active",
      "priority": "normal",
      "seed_type": "user_instruction",
      "seed_text": "记录这件事",
      "questions": ["What changed from the previous state?"],
      "watch_queries": [
        {"query": "Example official follow-up", "kind": "official"}
      ],
      "entity_names": [
        {"name": "Example", "kind": "organization"}
      ]
    }
  ],
  "events": [
    {
      "ref": "event",
      "summary": "Example announced the transition",
      "occurred_at": "2026-08-30",
      "occurred_at_precision": "day",
      "reported_at": "2026-08-30T09:00:00+08:00",
      "observed_at": "2026-08-31T12:00:00+08:00",
      "confidence": 0.95,
      "thread_refs": ["thread"],
      "entity_names": ["Example"]
    }
  ],
  "claims": [
    {
      "event_ref": "event",
      "source_ref": "official",
      "statement": "Example announced the transition.",
      "asserted_at": "2026-08-30T09:00:00+08:00",
      "confidence": 0.98,
      "status": "confirmed"
    }
  ]
}
```

Important fields:

- Events distinguish `occurred_at`, `reported_at`, and `observed_at`.
  `occurred_at_precision` is one of `instant`, `day`, `month`, `year`,
  `range`, or `unknown`.
- Claims require `event_ref`, `source_ref`, `statement`, and `confidence`.
  Status is `active`, `superseded`, `disputed`, or `confirmed`.
- Questions can be created inline on a thread. To answer one later, write a
  top-level question with `thread_ref`, the same `question`, `status: answered`,
  and `answer_event_ref`. Top-level watch queries can similarly toggle `active`.
- Relations require `src_ref`, `dst_ref`, `relation_type`, and `confidence`;
  provide `src_type`, `dst_type`, and `evidence` when relevant.
- Interpretations require `earlier_event_ref`, `later_event_ref`, `statement`,
  `confidence`, and evidence IDs.
- Personal links require `world_event_ref`, `personal_event_id`, an allowed
  `relation_type`, `explanation`, `confidence`, and minimal evidence IDs.
- Discovery candidates require `candidate_type`, `title`, and
  `relation_score`. Candidates remain non-active until explicitly promoted.
- Quotes store verbatim originals (发言原话、公开信全文/节选) attached to an
  event: `event_ref` (and optionally `source_ref`), `speaker`, `title`,
  `quote_text`, `quote_format` (`text` or `markdown`), `url`, `fetched_at`,
  and optional `slug`. With `slug`, the Obsidian render writes the full text
  to `原文素材/<slug>.md` (frontmatter: type/thread_id/event_id/speaker/
  title/url) and the thread file shows only a preview plus an Obsidian link
  `[[原文素材/<slug>|…]]`. Without `slug`, the quote text is inlined in the
  thread file. Refs are bundle-local: cross-bundle references must use
  actual IDs (e.g. `src_...`, `evt_...`, `qte_...`), not earlier refs.
  For X posts (e.g. @justinsuntron) verbatim full text often has no
  publicly indexed reprint — use the user's pasted original when provided,
  or clearly label multi-source-verified excerpts as 节选, never as 全文.
- Reports require `mode`, `window_end`, `body`, and `significance`.
- The store-bundle result includes `touched_threads`: threads this bundle
  created or modified. Bundles that touch no thread (for example pure
  discovery candidates) trigger no Obsidian export.

Use `search <query>` before capture and `thread <id>` before updating an
existing thread. The returned `refs` map from `store-bundle` exposes every
generated ID used within the transaction. Refs are bundle-local: a later
bundle must reference earlier objects by their actual IDs, not by earlier
refs.
