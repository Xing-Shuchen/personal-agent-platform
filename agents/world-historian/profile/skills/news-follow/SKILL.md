---
name: news-follow
description: Follow active World Historian threads for material new evidence, corrections, consequences, and answers to open questions.
---

# Follow active threads

At the start of every follow run, apply the priority lifecycle below before
selecting the requested-priority work set.

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
Use one local lifecycle-candidate query, at most one local feed query, one
due-thread list query, one thread-roster query (see Delivery contract), and one
detail query per candidate thread. Process at most ten due threads per run and at
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

Every entity written in a follow bundle must be an object with `name` and a
closed-vocabulary `kind` (plus `role` for an event entity), never a bare name.
Use [entity-kinds.md](/home/xingzeng/personal-agent-platform/agents/world-historian/profile/references/entity-kinds.md)
and fix any proposed `kind: "unknown"` before persisting.

Every new event must include a concise `title` (maximum 60 characters) for
the timeline heading. Put the full account in `summary` as Markdown body text:
separate distinct developments into paragraphs or bullets, and never use the
summary itself as a heading.

## Math in stored text

Stored text is projected verbatim into Obsidian, which renders `$...$` (inline)
and `$$...$$` (display) as LaTeX. Write real LaTeX inside `$...$` for any
formula (`$G(T) \gg \log T\,\log_2 T/\log_4 T$`, `$\pi_1(X)$`), never Unicode
math notation (`≫`, `log₂T`, `π₁`). Narrative prose stays plain — only actual
formulas/expressions get `$` delimiters.

When adding a verbatim full-text quote, always give it a `slug` and a concise
editorial `summary`. The full text belongs in `原文素材/<slug>.md`; the thread
projection shows only the `[[原文素材/…|…]]` link and `**摘要**`, never the
full text or an opening-line preview.

## Vault completion

If this run wrote or changed any vault file, finish the vault SOP before
returning; skip it only when no vault file changed. Steps:
[references/vault-completion-sop.md](references/vault-completion-sop.md).

The SOP is silent bookkeeping: never mention it, the git push, or the COS verification in the run's user-facing message. A run that did vault work still returns exactly the Delivery-contract shape, or exactly `NO_REPLY` when nothing is deliverable — never a status or work-summary line about the SOP.

## Thread roster (read-only, delivery set)

To list the threads a follow update delivers, run this read-only command
(do not probe any other Chronicle path). The delivered set is `high`, `normal`,
and `low`; `background` threads stay tracked in the Chronicle but never appear
in a follow update.

```bash
"/home/xingzeng/personal-agent-platform/.venv/bin/python" \
  agents/world-historian/runtime/cli.py roster
```

## Priority lifecycle (tiered stepdown, then close)

Every `news-follow` run, for all four priorities, must find and persist
lifecycle candidates before selecting its work set. This is required even for
non-background follow runs because the first two thresholds are shorter than
the background job cadence. The stepdown is determined only by a thread's
current priority and newest event:

| Current priority | Newest event older than | New priority |
| --- | ---: | --- |
| `high` | 3 days | `normal` |
| `normal` | 7 days | `low` |
| `low` | 14 days | `background` |
| `background` | — | never demote further |

Demote at most one tier per run: even a `high` thread idle for 30 days becomes
`normal` in that run, and a later run may step it down again. A genuinely new
event promotes a thread only through the normal bundle path. No new event for
over 60 days (two months) instead sets `status: closed`; this close decision
takes precedence over demotion. Threads with no events also close. A closed
thread is not followed at all and must not appear in the tracked roster.

Find candidates with this read-only command (use the defaults unless testing a
different lifecycle window):

```bash
"/home/xingzeng/personal-agent-platform/.venv/bin/python" \
  "/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" \
  lifecycle-candidates
```

Persist each change through `store-bundle`: `DEMOTE` → the thread's `id`,
`title`, `status: "active"`, and the target priority in the fourth tab-separated
column of its `DEMOTE` line; `CLOSE` → `id`, `title`, `status: "closed"`. For
either lifecycle-only bundle, carry the existing `last_checked_at`,
`next_check_at`, and `quiet_count` values through verbatim: never reset or zero
those raw fields.

## Lifecycle notices (level lowered)

A lowering is user-facing: every `DEMOTE` and `CLOSE` this run persists must be
reported in this run's message, even when the thread gained no new event.

Record each persisted lowering as one appended JSON line in
`/home/xingzeng/personal-agent-platform/var/world-historian/lifecycle-notices.jsonl`:
`{"ts": "<local ISO>", "id": "<thr_…>", "title": "<verbatim title>", "from":
"<old priority>", "to": "<normal|low|background|closed>", "reason": "<N> 天无新事件"}`.
Append through one small `python3 - <<'PY'` heredoc; never rewrite the file.

Then consume pending notices at the end of the run, before composing the
response:

```bash
NOTICES=/home/xingzeng/personal-agent-platform/var/world-historian/lifecycle-notices.jsonl
if [ -s "$NOTICES" ]; then
  cat "$NOTICES"
  mv "$NOTICES" "/home/xingzeng/personal-agent-platform/var/world-historian/lifecycle-notices-delivered-$(date +%Y%m%d-%H%M).jsonl"
fi
```

Its printed lines are the notices to report; the `mv` clears them so later runs
do not repeat them. Report a lowering in the very run that persists it, at any
hour — no holding, no quiet-hours suppression. Empty output means nothing is
pending. A run that dies after appending leaves the line pending, so a lowering
is never lost.

Report only the notices whose lines were printed; never state that no notices were pending.

## Delivery contract

This is a collection job. Only `high` and `normal` priority material changes
trigger a delivery. `low` and `background` threads stay tracked in the
Chronicle: record their events/claims as usual. `low` threads appear in the
roster, while `background` threads never appear in the message.

- No `high`/`normal` thread gained a material event or claim correction and no
lifecycle notice was consumed — the ENTIRE final response must be exactly the
single marker `NO_REPLY`. This includes runs whose only changes touch
`low`/`background` threads: they are persisted but a `low`-only change still
returns exactly `NO_REPLY`. A consumed lifecycle notice is the one exception
that makes such a run user-facing (see「Lifecycle notices」). No work
summary, no rejection notes, no Chinese「无变化」prose, nothing before or after.
Any surrounding text makes it a normal delivery and spams the user (observed
2026-09-01: a work-summary +
`[SILENT]` response leaked to Feishu; OpenClaw only suppresses the exact token
`NO_REPLY` — any other marker, including the legacy Hermes `[SILENT]`, is
delivered as literal text, observed 2026-09-08 13:05).
- At least one `high`/`normal` thread gained a material event or claim
correction, or a lifecycle notice was consumed — return one Chinese update,
written as Feishu Markdown (the Feishu channel renders it), with exactly this
shape and nothing else:

```markdown
**🛰️ 世界线追踪 · M月D日** ｜ Level: <High|Normal|Low|Background> ｜ <N> 条进展

**进展**
- **<线程标题>** — <新增/修正了什么事件，一句话>（[来源](<url>)）

**降级**
- **<线程标题>** — <旧档位> → <新档位|closed>（<原因>）

**追踪中**
<`roster` command stdout, pasted verbatim>
```

Formatting rules:
1. 进展 — 每个有新进展的 `high`/`normal` thread 一条：加粗线程标题、一句话说明新增或修正的事件、有来源就附行内链接。不写检索过程、不写被排除的候选；`low`/`background` 绝不出现。标题里的 `<N> 条进展` 只数这些进展条，不含降级；没有进展时省略 `**进展**` 一节、计数写 `0 条进展`。
2. 降级 — 每个被消费的 lifecycle 通知一条：加粗线程标题、`<旧档位> → <新档位|closed>`、括号里写原因（如 `3 天无新事件`）。降级只写在这里，绝不写进 `进展`，也不要有单独的降级前言。
3. 追踪中 — 将上面 `roster` command 的 stdout 原样粘贴：不得由模型选择 emoji、不得重新加粗、不得重排、不得添加或删除行。三档 emoji 映射为 `🟥` high / `🟦` normal / `⬜` low。
4. 保持紧凑：每个 thread 一行。Feishu 卡片渲染加粗、列表、链接、表情和空行——不要用表格，分节标签用加粗（`**进展**`）而不是 `#` 标题。
5. 来源档位只写 `Level: <优先级>`：优先级取 invocation 结构化参数 `priority`，首字母大写（`Level: High` / `Level: Normal`；`low`/`background` 不会投递，若出现写 `Level: Low` / `Level: Background`）。不写 job 名、不译成中文、不加其他词。
6. 绝不在消息前后加状态行或工作摘要：不要报告 vault SOP、git push、COS 校验、lifecycle 检查及其结果，也不要写「无待处理通知」这类否定报告。消息只能是上面的结构，或在无可投递内容时恰好 `NO_REPLY`。
