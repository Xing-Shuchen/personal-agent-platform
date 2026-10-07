---
name: news-feeds
description: Deterministic RSS/Atom ingestion into the Chronicle sources table; runs on a schedule before follow work.
---

# Ingest configured RSS feeds

This job is deterministic and runs through the manifest's `runner: command`:
there is no model turn and zero model tokens. The declared argv is exactly:

```text
$PAP_ROOT/.venv/bin/python agents/world-historian/runtime/cli.py feeds update
```

PAP executes that argv from the repository root. It fetches all `kind: rss`
sources from this profile's `config.yaml`; per-feed failures are reported by
the command and do not cause an in-run retry. Its JSON stdout stays local, so
ingestion is never interruption-worthy; `news-follow` decides what matters.

This skill file remains as the job's audit trail and is validated before the
command is launched; it is not supplied to a model.
