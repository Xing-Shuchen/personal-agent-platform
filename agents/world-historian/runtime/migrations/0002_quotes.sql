-- 0002_quotes.sql: verbatim quotes / full-text originals linked to events
CREATE TABLE IF NOT EXISTS quotes (
    id TEXT PRIMARY KEY,
    event_id TEXT REFERENCES events(id),
    source_id TEXT REFERENCES sources(id),
    speaker TEXT,
    title TEXT,
    quote_text TEXT NOT NULL,
    quote_format TEXT NOT NULL DEFAULT 'text' CHECK (quote_format IN ('text', 'markdown')),
    url TEXT,
    fetched_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quotes_event ON quotes(event_id);
CREATE INDEX IF NOT EXISTS idx_quotes_source ON quotes(source_id);
