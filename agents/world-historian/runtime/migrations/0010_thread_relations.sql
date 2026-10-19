-- Undirected, explicitly supplied thread links. Canonical endpoint order
-- prevents reverse duplicates; different types may link the same pair.
CREATE TABLE IF NOT EXISTS thread_relations (
    thread_id_a TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    thread_id_b TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL DEFAULT 'related',
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (thread_id_a < thread_id_b),
    PRIMARY KEY (thread_id_a, thread_id_b, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_thread_relations_b ON thread_relations(thread_id_b);
