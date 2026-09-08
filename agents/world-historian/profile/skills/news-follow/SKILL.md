---
name: news-follow
description: Follow active World Historian threads for material new evidence, corrections, consequences, and answers to open questions.
---

# Follow active threads

Use the requested priority as the work-set filter.

## Local increments first

RSS sources are ingested hourly into the Chronicle by the `news-feeds` job.
Before any web search, check what is already local:

```bash
"/home/xingzeng/personal-agent-platform/.venv/bin/python" \
  "/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" \
  --db "/home/xingzeng/personal-agent-platform/var/world-historian/chronicle.sqlite" \
  feeds recent --hours 24 --limit 80
```

The `--db` path above is mandatory. Do not inspect or probe other Chronicle
paths, run database discovery, or read CLI help during a scheduled run. If the
command fails, report the single failure and stop. Keep the feed output to
titles, timestamps, URLs, and short summaries; do not dump full article bodies.

## Execution budget

This is an incremental collection job, not an open-ended research session.
Use at most one local feed query, one due-thread list query, and one detail
query per candidate thread. Process at most ten due threads per run and at
most five web searches total; stop searching as soon as the configured
expansion budget is satisfied. Never inspect OpenClaw automations, sessions,
home directories, or unrelated logs while running this skill. If a required
field or thread cannot be found with the commands in this skill, stop with a
brief error rather than exploring alternate paths.

Match those entries against each due thread's title, entities, watch queries,
and open questions. Only if the local window does not answer a lane, go to the
web. This keeps follow work cheap, reproducible, and independent of search
engine variance.

## Preferred outlets and search order

First read `config.yaml` from this profile directory and note the `sources`
list. These are the user's preferred outlets (远川研究所矩阵、腾讯科技、新潮
沉思录、36氪、量子位、机器之心、智能涌现、凤凰网) plus vetted RSS feeds.
Check them before generic web search, in this order:

1. `kind: rss` — entries are already ingested locally (see above); fetch the
   feed directly only if fresher data is needed.
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
only genuine deltas through `/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py store-bundle`. Supersede or
dispute claims explicitly; never overwrite their historical state. Update each
thread's last-check state even when no event is added.

## Math in stored text

Stored text is projected verbatim into Obsidian, which renders `$...$` (inline)
and `$$...$$` (display) as LaTeX. Write real LaTeX inside `$...$` for any
formula (`$G(T) \gg \log T\,\log_2 T/\log_4 T$`, `$\pi_1(X)$`), never Unicode
math notation (`≫`, `log₂T`, `π₁`). Narrative prose stays plain — only actual
formulas/expressions get `$` delimiters.

This is a user-facing search-and-aggregation job. Every run must produce a
concise Chinese report; never return `NO_REPLY` or any other silent marker.
When there is no material change, say so explicitly (for example:
「本轮检索暂无重要更新。」) and include the number of threads and search
lanes checked. If a change merits proactive interruption, pass it through
`"/home/xingzeng/personal-agent-platform/.venv/bin/pap" gate --agent world-historian` with a stable
stable event/thread key before returning the report; the gate may control
whether an item is marked interruption-worthy, but it must not suppress the
run report.

Use this final-response shape:

```text
世界新闻跟踪｜YYYY-MM-DD HH:mm

- 本轮检查：<threads/lanes checked>；<new events or「暂无重要更新」>。
- <有更新时列出每条更新及来源；没有更新时保留上一行即可>
```
