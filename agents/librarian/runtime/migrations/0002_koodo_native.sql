CREATE TABLE IF NOT EXISTS koodo_native_records (
  owner_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  note_key TEXT NOT NULL,
  book_key TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  accepted_sha256 TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('active', 'pending', 'deleted')),
  pending_sha256 TEXT,
  pending_asset TEXT,
  PRIMARY KEY (owner_id, source_id, note_key)
);
