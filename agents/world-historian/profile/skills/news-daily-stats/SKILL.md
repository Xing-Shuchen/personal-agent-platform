---
name: news-daily-stats
description: End-of-day World Historian ledger — summarize the day's agent actions, ingest events, thread updates and delivery status from the Chronicle and run log.
---

# Daily World Historian stats (当日台账)

Produce a compact Chinese end-of-day ledger for World Historian covering the
just-finished local calendar day. This job runs at 00:00, so it must report
yesterday (00:00–24:00 local), never the nearly empty new day. This is a statistics/summary job, not
a news brief — do not call the gate; the user asked for this daily summary.

1. Gather the day's run activity and Chronicle ingest with this deterministic
   read-only command:

   ```bash
   "/home/xingzeng/personal-agent-platform/.venv/bin/python" \
     "/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" \
     daily-stats
   ```

   Report per job: run count, success/failed/timeout, and delivery status
   (sent/silent/failed/not-attempted). Only include world-historian jobs
   unless something else is notable.

2. Note what changed that day: new threads (search for threads created today,
   e.g. `search` / `thread` output `created_at`), new events, new claims,
   updated threads (touched_threads from store-bundle runs).

3. Compose the ledger:

   - 当日 job 运行：job → N 次（成功/失败/超时），投递情况
   - 当日入库：新增 thread N、事件 N、主张 N（引用具体 id/标题）
   - 线程状态：活跃追踪 N、当日更新 N、休眠 N
   - 投递：今日推送 sent N / silent N / failed N
   - 异常：任何失败/超时/投递失败，一行说明

4. Keep it compact — a few short sections, no more than ~15 lines. Always
   deliver the ledger even on quiet days (a 2-line "昨日无动作" is fine). Never
   return `NO_REPLY` for this user-facing daily report.
