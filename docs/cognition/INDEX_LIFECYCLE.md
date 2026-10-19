# Index lifecycle

`pap cognition index` is incremental. It enumerates candidate Markdown, stats before and after read, skips exact-hash matches, replaces only changed document projections in a transaction, tombstones disappeared documents and removes their current FTS visibility. A file changing during read is left on its prior good revision and retried next run.

Each build prunes superseded evidence and document revisions, plus all tombstoned evidence and its text projections, in the same transaction. Current document revisions and retrieval/feedback state are retained. Build output and status report `pruned_units` and `pruned_revisions` for the latest completed generation. Pruning makes freed pages reusable without running `VACUUM`, so row growth is bounded without any scheduled rebuild. No periodic `--full` rebuild is scheduled; a full rebuild is on-demand maintenance only, and on a large vault it does not shrink the file (per-unit embedding vectors dominate the size).

Build and refresh the index out of band with `PAP_VAULT` set and `pap cognition index`, either manually or in a scheduled command job, before enabling cognition agents. Runtime adapters only read the pre-built document/evidence index and record retrieval/feedback state; they never rebuild it within the runtime budget. A missing or empty index yields a clean `not_ready` response with a hint to run the CLI.

`pap cognition status`, `evidence <id>` and `search <query>` expose only bounded data. Evidence excerpts default to 1,200 characters and cap at 5,000; FTS results cap at 20. Full rebuild means deleting only the derived SQLite file after user-directed maintenance, never Vault content.

The first private build is local-only. No Vault text leaves the machine, and status/audit output contains aggregate metadata rather than body text.
