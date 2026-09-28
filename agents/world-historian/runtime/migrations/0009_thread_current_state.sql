CREATE TABLE IF NOT EXISTS thread_current_states (
    thread_id TEXT PRIMARY KEY REFERENCES threads(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    provenance TEXT NOT NULL CHECK (provenance IN ('historian_generated', 'manual')),
    source_refs_json TEXT NOT NULL DEFAULT '[]',
    revision TEXT,
    updated_at TEXT NOT NULL
);
