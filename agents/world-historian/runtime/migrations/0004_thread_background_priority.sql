-- Add the background lifecycle tier used by world-follow-background.
-- Keep child foreign-key declarations pointing at the replacement `threads`
-- table while rebuilding the CHECK constraint.
PRAGMA foreign_keys = OFF;
PRAGMA legacy_alter_table = ON;

BEGIN;
DROP INDEX IF EXISTS idx_threads_state;
ALTER TABLE threads RENAME TO threads_legacy;

CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'candidate', 'dormant', 'closed')),
    priority TEXT NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('high', 'normal', 'low', 'background')),
    seed_type TEXT NOT NULL DEFAULT 'user_instruction',
    seed_text TEXT,
    last_checked_at TEXT,
    next_check_at TEXT,
    quiet_count INTEGER NOT NULL DEFAULT 0 CHECK (quiet_count >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

INSERT INTO threads (
    id, title, status, priority, seed_type, seed_text, last_checked_at,
    next_check_at, quiet_count, created_at, updated_at
)
SELECT
    id, title, status, priority, seed_type, seed_text, last_checked_at,
    next_check_at, quiet_count, created_at, updated_at
FROM threads_legacy;

DROP TABLE threads_legacy;
CREATE INDEX idx_threads_state ON threads(status, priority);
COMMIT;

PRAGMA legacy_alter_table = OFF;
PRAGMA foreign_keys = ON;
