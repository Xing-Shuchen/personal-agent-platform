---
name: news-follow
description: Follow active World Historian threads for material new evidence, corrections, consequences, and answers to open questions.
---

# Follow active threads

Use the requested priority as the work-set filter.

First read `config.yaml` from this profile directory and note the `sources`
list. These are the user's preferred outlets (远川研究所矩阵、腾讯科技、新潮
沉思录、36氪、量子位、机器之心、智能涌现、凤凰网) plus vetted RSS feeds.
Check them before generic web search, in this order:

1. `kind: rss` — fetch the feed URL directly for the newest items.
2. `kind: site` — browse or search the site for the thread's keywords.
3. `kind: wechat` — 公众号 has no public RSS: search
   `site:mp.weixin.qq.com <keywords>` or rely on reposts by aggregators.
   Never fetch WeChat article content that requires subscription/login.

Prefer these sources when they cover a story: they are the user's stated
authoritative set. Keep using general search for discovery beyond them.

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
