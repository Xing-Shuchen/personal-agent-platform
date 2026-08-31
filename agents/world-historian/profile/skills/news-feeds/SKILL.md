---
name: news-feeds
description: Deterministic RSS/Atom ingestion into the Chronicle sources table; runs on a schedule before follow work.
---

# Ingest configured RSS feeds

This job is deterministic: it runs the runtime fetcher and reports counts. It
does not reason about the news, does not search the web, and produces no
user-facing digest.

1. Run the ingestion (all `kind: rss` sources from this profile's
   `config.yaml` are fetched; failures are isolated per feed):

   ```bash
   "$PAP_ROOT/.venv/bin/python" \
     "$PAP_ROOT/agents/world-historian/runtime/cli.py" feeds update
   ```

2. Note `entries_added` and any per-feed `errors`. Feed failures are normal
   (site outages, anti-scraping); they are recorded in the output and must
   not be retried in this run.
3. Optionally verify with:

   ```bash
   "$PAP_ROOT/.venv/bin/python" \
     "$PAP_ROOT/agents/world-historian/runtime/cli.py" feeds recent --hours 24
   ```

4. Finish with exactly `[SILENT]`. Ingestion itself is never
   interruption-worthy; `news-follow` decides what matters.
