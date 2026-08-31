PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    publisher TEXT,
    source_kind TEXT NOT NULL DEFAULT 'unknown',
    published_at TEXT,
    updated_at TEXT,
    fetched_at TEXT NOT NULL,
    content_hash TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(canonical_url);
CREATE INDEX IF NOT EXISTS idx_sources_published ON sources(published_at);

CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'candidate', 'dormant', 'closed')),
    priority TEXT NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('high', 'normal', 'low')),
    seed_type TEXT NOT NULL DEFAULT 'user_instruction',
    seed_text TEXT,
    last_checked_at TEXT,
    next_check_at TEXT,
    quiet_count INTEGER NOT NULL DEFAULT 0 CHECK (quiet_count >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_threads_state ON threads(status, priority);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    occurred_at TEXT,
    occurred_at_precision TEXT NOT NULL DEFAULT 'unknown'
        CHECK (occurred_at_precision IN ('instant', 'day', 'month', 'year', 'range', 'unknown')),
    reported_at TEXT,
    observed_at TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'superseded', 'disputed', 'confirmed', 'merged', 'split')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_occurred ON events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_observed ON events(observed_at);

CREATE TABLE IF NOT EXISTS thread_events (
    thread_id TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    membership_confidence REAL NOT NULL DEFAULT 1.0
        CHECK (membership_confidence >= 0 AND membership_confidence <= 1),
    created_at TEXT NOT NULL,
    PRIMARY KEY (thread_id, event_id)
);

CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    statement TEXT NOT NULL,
    asserted_at TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'superseded', 'disputed', 'confirmed')),
    superseded_by TEXT REFERENCES claims(id) DEFERRABLE INITIALLY DEFERRED,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claims_event ON claims(event_id);
CREATE INDEX IF NOT EXISTS idx_claims_source ON claims(source_id);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'unknown',
    aliases_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    UNIQUE (name, kind)
);

CREATE TABLE IF NOT EXISTS event_entities (
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'mentioned',
    PRIMARY KEY (event_id, entity_id, role)
);

CREATE TABLE IF NOT EXISTS thread_entities (
    thread_id TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    PRIMARY KEY (thread_id, entity_id)
);

CREATE TABLE IF NOT EXISTS open_questions (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'answered', 'abandoned')),
    answer_event_id TEXT REFERENCES events(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_questions_thread ON open_questions(thread_id, status);

CREATE TABLE IF NOT EXISTS watch_queries (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    query_kind TEXT NOT NULL DEFAULT 'exact',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL,
    UNIQUE (thread_id, query, query_kind)
);

CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,
    src_type TEXT NOT NULL,
    src_id TEXT NOT NULL,
    dst_type TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    evidence_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'candidate', 'rejected', 'superseded')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_relations_src ON relations(src_type, src_id);
CREATE INDEX IF NOT EXISTS idx_relations_dst ON relations(dst_type, dst_id);

CREATE TABLE IF NOT EXISTS interpretations (
    id TEXT PRIMARY KEY,
    earlier_event_id TEXT NOT NULL REFERENCES events(id),
    later_event_id TEXT NOT NULL REFERENCES events(id),
    statement TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    evidence_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'disputed', 'superseded')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS personal_links (
    id TEXT PRIMARY KEY,
    world_event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    personal_event_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    explanation TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    evidence_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (world_event_id, personal_event_id, relation_type)
);

CREATE TABLE IF NOT EXISTS discovery_candidates (
    id TEXT PRIMARY KEY,
    candidate_type TEXT NOT NULL,
    title TEXT NOT NULL,
    relation_score REAL NOT NULL CHECK (relation_score >= 0 AND relation_score <= 1),
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (status IN ('candidate', 'promoted', 'rejected', 'expired')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    window_start TEXT,
    window_end TEXT NOT NULL,
    body TEXT NOT NULL,
    significance REAL NOT NULL CHECK (significance >= 0 AND significance <= 1),
    created_at TEXT NOT NULL
);
