#!/usr/bin/env bash
# Create a local, consistent Chronicle backup. Export/sync destinations are configured locally.
set -euo pipefail
PAP_ROOT="${PAP_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SOURCE="${PAP_CHRONICLE_DB:-$PAP_ROOT/var/world-historian/chronicle.sqlite}"
DEST="${PAP_CHRONICLE_SNAPSHOT:-$PAP_ROOT/var/world-historian/chronicle-snapshot.sqlite}"
if [[ ! -f "$SOURCE" ]]; then
  printf 'Chronicle database not found: %s\n' "$SOURCE" >&2
  exit 1
fi
mkdir -p "$(dirname "$DEST")"
python3 - "$SOURCE" "$DEST" <<'PY'
import sqlite3
import sys
from pathlib import Path
source, destination = map(Path, sys.argv[1:])
with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as read_db:
    with sqlite3.connect(destination) as backup_db:
        read_db.backup(backup_db)
print(destination)
PY
