CREATE TABLE IF NOT EXISTS records (
  owner_id TEXT NOT NULL,
  model TEXT NOT NULL,
  id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision >= 1),
  current INTEGER NOT NULL CHECK (current IN (0, 1)),
  body TEXT NOT NULL,
  PRIMARY KEY (owner_id, model, id, revision)
);
CREATE UNIQUE INDEX IF NOT EXISTS records_current
  ON records(owner_id, model, id) WHERE current = 1;
CREATE TRIGGER IF NOT EXISTS evidence_immutable BEFORE UPDATE ON records
WHEN OLD.model IN ('PageCapture', 'PageObservation')
BEGIN SELECT RAISE(ABORT, 'immutable evidence'); END;
CREATE TRIGGER IF NOT EXISTS evidence_undeletable BEFORE DELETE ON records
WHEN OLD.model IN ('PageCapture', 'PageObservation')
BEGIN SELECT RAISE(ABORT, 'immutable evidence'); END;
CREATE TABLE IF NOT EXISTS source_items (
  owner_id TEXT NOT NULL,
  transport TEXT NOT NULL,
  account_id TEXT NOT NULL,
  source_event_id TEXT NOT NULL,
  source_item_id TEXT NOT NULL,
  capture_id TEXT NOT NULL,
  PRIMARY KEY (owner_id, transport, account_id, source_event_id, source_item_id)
);
CREATE TABLE IF NOT EXISTS idempotency (
  owner_id TEXT NOT NULL,
  key TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  receipt TEXT NOT NULL,
  PRIMARY KEY (owner_id, key)
);
CREATE TABLE IF NOT EXISTS outbox (
  event_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  body TEXT NOT NULL,
  delivered_at TEXT
);
CREATE TABLE IF NOT EXISTS extractor_attempts (
  owner_id TEXT NOT NULL,
  capture_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  raw_asset TEXT NOT NULL,
  status TEXT NOT NULL,
  error_code TEXT,
  PRIMARY KEY (owner_id, run_id)
);
CREATE TABLE IF NOT EXISTS extractor_derivatives (
  owner_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  derivative TEXT NOT NULL,
  PRIMARY KEY (owner_id, run_id)
);
CREATE TABLE IF NOT EXISTS trace_index (
  owner_id TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  revision INTEGER NOT NULL,
  printed_text TEXT NOT NULL,
  annotation TEXT NOT NULL,
  work_id TEXT,
  edition_id TEXT,
  book_instance_id TEXT,
  session_id TEXT,
  medium TEXT NOT NULL,
  context_state TEXT NOT NULL,
  trace_types TEXT NOT NULL,
  PRIMARY KEY (owner_id, trace_id)
);
CREATE TABLE IF NOT EXISTS digital_exports (
  owner_id TEXT NOT NULL,
  medium TEXT NOT NULL,
  source_key TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  trace_ids TEXT NOT NULL,
  PRIMARY KEY (owner_id, medium, source_key)
);
CREATE TABLE IF NOT EXISTS session_scope (
  owner_id TEXT NOT NULL,
  transport TEXT NOT NULL,
  account_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  selected INTEGER NOT NULL CHECK (selected IN (0, 1)),
  last_assigned_at TEXT,
  PRIMARY KEY (owner_id, transport, account_id, conversation_id, session_id)
);
CREATE TABLE IF NOT EXISTS capture_context (
  owner_id TEXT NOT NULL,
  capture_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  basis TEXT NOT NULL,
  PRIMARY KEY (owner_id, capture_id)
);
CREATE TABLE IF NOT EXISTS command_receipts (
  owner_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  receipt TEXT NOT NULL,
  PRIMARY KEY (owner_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS consumer_events (
  consumer_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  owner_id TEXT NOT NULL,
  consumed_at TEXT NOT NULL,
  PRIMARY KEY (consumer_id, event_id)
);
