---
name: news-follow
description: Follow active World Historian threads for material new evidence, corrections, consequences, and answers to open questions.
---

# Follow active threads

Use the requested priority as the work-set filter.

## Local increments first

RSS sources are ingested during the configured low-cost windows into the
Chronicle by the `news-feeds` job.
Before any web search, check what is already local:

```bash
"/home/xingzeng/personal-agent-platform/.venv/bin/python" \
  "/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" \
  --db "/home/xingzeng/personal-agent-platform/var/world-historian/chronicle.sqlite" \
  feeds recent --hours 24 --limit 80
```

The `--db` path above is mandatory. Do not inspect or probe other Chronicle
paths, run database discovery, or read CLI help during a scheduled run. If the
command fails, stop and return exactly `NO_REPLY`. Keep the feed output to
titles, timestamps, URLs, and short summaries; do not dump full article bodies.

## Execution budget

This is an incremental collection job, not an open-ended research session.
Use at most one local feed query, one due-thread list query, one thread-roster
query (see Delivery contract), and one detail query per candidate thread. Process at most ten due threads per run and at
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

For each due thread, query across six lanes: exact follow-up, entities, open
questions, downstream consequences, official-source checks, and commentary
(substantive expert analysis, insider accounts, informed criticism, or notable
public reaction to the thread's subject). Cluster
coverage into underlying events before writing anything.

For every candidate, evaluate entity overlap, causal strength, temporal
proximity, semantic relation, user interest, novelty, and relevant public
commentary (how directly it bears on the thread — not how loud it is). Respect
the configured expansion budget: at most five new events per run and two new
threads per day.
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

## Thread roster (read-only, delivery set)

To list the threads a follow update delivers, run exactly this read-only query
(do not probe any other Chronicle path). The delivered set is `high` and
`normal` only; `low` and `background` threads stay tracked in the Chronicle but
must never appear in a follow update.

```bash
"/home/xingzeng/personal-agent-platform/.venv/bin/python" - <<'PY'
import sqlite3
db = sqlite3.connect("file:/home/xingzeng/personal-agent-platform/var/world-historian/chronicle.sqlite?mode=ro", uri=True)
for title, pri in db.execute(
    "SELECT title, priority FROM threads WHERE status='active' "
    "AND priority IN ('high','normal') "
    "ORDER BY CASE priority WHEN 'high' THEN 0 ELSE 1 END, title"
):
    print(f"- {title}（{pri}）")
PY
```

## Priority lifecycle (background demotion, then close)

Applied by the `world-follow-background` job before it selects its work set
(and safe to apply in any follow run when a stale thread is noticed):

- No new event for over 14 days: demote to `priority: background`. The thread
  stays `active` and tracked, just on the biweekly cadence. Genuinely new
  evidence promotes it back through the normal bundle path.
- No new event for over 60 days (two months): set `status: closed`. A closed
  thread is not followed at all and must not appear in the tracked roster.

Find candidates with exactly this read-only query:

```bash
"/home/xingzeng/personal-agent-platform/.venv/bin/python" - <<'PY'
import sqlite3, datetime
db = sqlite3.connect("file:/home/xingzeng/personal-agent-platform/var/world-historian/chronicle.sqlite?mode=ro", uri=True)
def parse(s):
    if not s: return None
    for f in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            d = datetime.datetime.strptime(s.strip(), f)
            return d.replace(tzinfo=None) if d.tzinfo else d
        except Exception: pass
    return None
agg = {}
for tid, title, pri, occ, obs, rep in db.execute("""SELECT t.id,t.title,t.priority,e.occurred_at,e.observed_at,e.reported_at
FROM threads t LEFT JOIN thread_events te ON te.thread_id=t.id LEFT JOIN events e ON e.id=te.event_id
WHERE t.status='active'"""):
    last = max([d for d in (parse(occ), parse(obs), parse(rep)) if d], default=None)
    cur = agg.setdefault(tid, {"title": title, "pri": pri, "last": None})
    if last and (cur["last"] is None or last > cur["last"]): cur["last"] = last
now = datetime.datetime.now()
for tid, v in agg.items():
    if v["last"] is None or v["last"] < now - datetime.timedelta(days=60):
        print(f"CLOSE\t{tid}\t{v['title']}")
    elif v["pri"] != "background" and v["last"] < now - datetime.timedelta(days=14):
        print(f"DEMOTE\t{tid}\t{v['title']}")
PY
```

Persist each change through `store-bundle`: `DEMOTE` → the thread's `id`,
`title`, `status: "active"`, `priority: "background"`; `CLOSE` → `id`, `title`,
`status: "closed"`. A lifecycle-only change is not a user-facing update; do
not deliver it unless the same run also persisted a material event or claim
correction for a tracked thread.

## Delivery contract

This is a collection job. Only `high` and `normal` priority threads are ever
delivered. `low` and `background` threads stay tracked in the Chronicle: record
their events/claims as usual, but keep them out of the message entirely.

- No `high`/`normal` thread gained a material event or claim correction — the
ENTIRE final response must be exactly the single marker `NO_REPLY`. This
includes runs whose only changes touch `low`/`background` threads: they are
persisted but never delivered. No work summary, no rejection notes, no
Chinese「无变化」prose, nothing before or after. Any surrounding text makes it a
normal delivery and spams the user (observed 2026-09-01: a work-summary +
`[SILENT]` response leaked to Feishu; OpenClaw only suppresses the exact token
`NO_REPLY` — any other marker, including the legacy Hermes `[SILENT]`, is
delivered as literal text, observed 2026-09-08 13:05).
- At least one `high`/`normal` thread gained a material event or claim
correction — return one Chinese update, written as Feishu Markdown (the Feishu
channel renders it), with exactly this shape and nothing else:

```markdown
**🛰️ 世界线追踪 · M月D日** ｜ <N> 条进展

**进展**
- **<线程标题>** — <新增/修正了什么事件，一句话>（[来源](<url>)）

**追踪中**
- 🟥 **<线程标题>**（high）
- 🟦 **<线程标题>**（normal）
```

Formatting rules:
1. 进展 — 每个有新进展的 `high`/`normal` thread 一条：加粗线程标题、一句话说明新增或修正的事件、有来源就附行内链接。不写检索过程、不写被排除的候选；`low`/`background` 绝不出现。
2. 追踪中 — 用上面 delivery-set roster 查询的输出，High 在前、Normal 在后，每行 `- <emoji> **<标题>**（<优先级>）`；只列 `high`/`normal`。
3. 保持紧凑：每个 thread 一行。Feishu 卡片渲染加粗、列表、链接、表情和空行——不要用表格，分节标签用加粗（`**进展**`）而不是 `#` 标题。
