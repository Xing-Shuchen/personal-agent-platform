---
name: news-follow
description: Follow active World Historian threads for material new evidence, corrections, consequences, and answers to open questions.
---

# Follow active threads

Use the requested priority as the work-set filter.

For each due thread, query across five lanes: exact follow-up, entities, open
questions, downstream consequences, and official-source checks. Cluster
coverage into underlying events before writing anything.

For every candidate, evaluate entity overlap, causal strength, temporal
proximity, semantic relation, user interest, and novelty. Respect the configured
expansion budget: at most five new events per run and two new threads per day.
Weak expansions remain discovery candidates; they do not become active merely
because they share keywords.

Before writing, read
[the follow bundle fields](references/follow-bundle.md). Persist
only genuine deltas through `runtime/cli.py store-bundle`. Supersede or
dispute claims explicitly; never overwrite their historical state. Update each
thread's last-check state even when no event is added.

This is a collection job. End with `[SILENT]` when there is no
interruption-worthy change. If a change merits proactive interruption, pass it
through `"$PAP_ROOT/.venv/bin/pap" gate --agent world-historian` with a stable event/thread key before
returning one concise Chinese update.
