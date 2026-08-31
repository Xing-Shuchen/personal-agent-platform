---
name: news-capture
description: Capture a user-named external development or URL into the World Historian as sourced claims, an event, and a continuing thread.
---

# Capture an external event

Treat the input as a seed for an ongoing thread, not as an article title.

1. Read `config.yaml` from this profile directory for the preferred `sources`
   list. When the seed maps to one of those outlets (远川研究所矩阵、腾讯科技、
   新潮沉思录、36氪、量子位、机器之心、智能涌现、凤凰网, or a vetted RSS
   feed), start from it: `kind: rss` feeds fetch directly, `kind: site` outlets
   are browsed, `kind: wechat` outlets are searched via `site:mp.weixin.qq.com`.
2. Search for the current state of the event and locate at least one primary or
   authoritative source when one exists. Keep secondary reporting only when it
   adds a distinct claim or records how understanding evolved.
3. Search the Chronicle for an existing matching thread before creating one.
4. Separate source observations, claims, event facts, and open questions.
   Preserve `occurred_at`, `reported_at`, and `observed_at` separately; use
   `null` and an explicit precision when the occurrence time is unknown.
5. Create a small initial source set, the event, its claims, thread entities,
   open questions, and watch queries. Do not assert motivations as facts.
6. Read [the Chronicle bundle format](references/chronicle-bundle.md),
   then persist one validated JSON bundle with:

   `"$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/world-historian/runtime/cli.py" store-bundle --json <path>`

   The runtime assigns deterministic IDs and commits the bundle atomically.
6. Return a compact Chinese intake report: what was captured, the best primary
   evidence, unresolved questions, uncertainty, and whether an existing thread
   was reused.

Initialize or inspect storage with `runtime/cli.py init`, `search`, `thread`,
and `stats`. Never place the SQLite database or raw snapshots under `profile/`.
