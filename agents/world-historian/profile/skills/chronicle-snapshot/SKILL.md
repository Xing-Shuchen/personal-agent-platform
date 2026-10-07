---
name: chronicle-snapshot
description: Create a consistent local backup of the World Historian Chronicle database.
---

# Chronicle snapshot

The `world-chronicle-snapshot` command job runs `scripts/sync_chronicle_snapshot.sh` from the repository root. It creates a consistent SQLite backup of `var/world-historian/chronicle.sqlite` at `var/world-historian/chronicle-snapshot.sqlite`.

Set `PAP_CHRONICLE_DB` and `PAP_CHRONICLE_SNAPSHOT` in the local environment to use other locations. Both paths contain private data and are ignored by Git when under `var/`. External syncing is a separate, user-configured step.
