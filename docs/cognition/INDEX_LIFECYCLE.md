# Index lifecycle

`pap cognition index` is incremental. It enumerates candidate Markdown, stats before and after read, skips exact-hash matches, replaces only changed document projections in a transaction, tombstones disappeared documents and removes their current FTS visibility. A file changing during read is left on its prior good revision and retried next run.

`pap cognition status`, `evidence <id>` and `search <query>` expose only bounded data. Evidence excerpts default to 1,200 characters and cap at 5,000; FTS results cap at 20. Full rebuild means deleting only the derived SQLite file after user-directed maintenance, never Vault content.

The first private build is local-only. No Vault text leaves the machine, and status/audit output contains aggregate metadata rather than body text.
