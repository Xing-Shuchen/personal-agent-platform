---
name: weibo-archive
description: Deterministic incremental archive of 卢诗翰 and sven_shi Weibo posts into the Obsidian vault, with a short user report.
---

# Archive Weibo incrementally

This job is deterministic and runs through the manifest's `runner: command`:
there is no model turn and zero model tokens. The declared argv is exactly:

```text
bash scripts/weibo-archive-daily.sh   # execs $HOME/.openclaw/skills/weibo-archive/scripts/daily_run.py
```

PAP executes that argv from the repository root, daily at 06:00 Asia/Shanghai.
The script incrementally syncs 卢诗翰 + sven_shi, publishes their posts to the
Obsidian vault, and prints a short human-readable report delivered to the user.

It requires `opencli` and the OpenCLI Browser Bridge with a signed-in Weibo
session. Logs land in `~/.openclaw/skills/weibo-archive/logs/`.

The script prints `[SILENT]`-free human text, including when nothing new is
archived. Never gate this report as silent or replace it with a silence marker.

This skill file remains as the job's audit trail and is validated before the
command is launched; it is not supplied to a model.
