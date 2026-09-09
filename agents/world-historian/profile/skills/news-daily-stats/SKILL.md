---
name: news-daily-stats
description: End-of-day World Historian ledger — summarize the day's agent actions, ingest events, thread updates and delivery status from the Chronicle and run log.
---

# Daily World Historian stats (当日台账)

Produce a compact Chinese end-of-day ledger for World Historian covering the
just-finished local calendar day. This job runs at 00:00, so it must report
yesterday (00:00–24:00 local), never the nearly empty new day. This is a statistics/summary job, not
a news brief — do not call the gate; the user asked for this daily summary.

1. Gather the day's run activity from the pap run log (parse the JSONL):

   ```bash
   "/home/xingzeng/personal-agent-platform/.venv/bin/python" - <<'PY'
   import collections, json
   from datetime import datetime, timedelta

   day = (datetime.now().astimezone().date() - timedelta(days=1)).isoformat()
   completed, deliveries = {}, {}
   path = "/home/xingzeng/personal-agent-platform/var/state/runs.jsonl"
   with open(path, encoding="utf-8") as f:
       for line in f:
           record = json.loads(line)
           if record.get("event") == "run.completed" and record.get("completed_at", "").startswith(day):
               completed[record["run_id"]] = record
           elif record.get("event") == "run.delivery":
               deliveries[record["run_id"]] = record.get("delivery", "not-attempted")
   by_job = collections.defaultdict(lambda: collections.Counter())
   for run_id, record in completed.items():
       if record.get("agent_id") != "world-historian":
           continue
       job = record.get("trigger", {}).get("job_id", "unknown")
       by_job[job][record.get("status", "unknown")] += 1
       by_job[job]["delivery:" + deliveries.get(run_id, "not-attempted")] += 1
   print(day)
   for job, counts in sorted(by_job.items()):
       print(job, dict(counts))
   EOF
   ```

   Report per job: run count, success/failed/timeout, and delivery status
   (sent/silent/failed/not-attempted). Only include world-historian jobs
   unless something else is notable.

2. Chronicle ingest for the day:

   ```bash
   "/home/xingzeng/personal-agent-platform/.venv/bin/python" - <<'PY'
   import sqlite3
   from datetime import datetime, timedelta

   day = (datetime.now().astimezone().date() - timedelta(days=1)).isoformat()
   db = sqlite3.connect(
       "file:/home/xingzeng/personal-agent-platform/var/world-historian/chronicle.sqlite?mode=ro",
       uri=True,
   )
   for table in ("threads", "events", "claims"):
       print(table, db.execute(
           f"SELECT COUNT(*) FROM {table} WHERE substr(created_at, 1, 10) = ?", (day,)
       ).fetchone()[0])
   for row in db.execute(
       "SELECT id, title, priority, status FROM threads WHERE substr(updated_at, 1, 10) = ? ORDER BY updated_at",
       (day,),
   ):
       print("updated-thread", *row)
   PY
   ```

   and note what changed today: new threads (search for threads created today,
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
