-- Track when an event was most recently attached to each thread. Existing
-- threads are backfilled from the immutable thread-event membership rows.
ALTER TABLE threads ADD COLUMN last_event_ingested_at TEXT;

UPDATE threads
SET last_event_ingested_at = (
    SELECT MAX(thread_events.created_at)
    FROM thread_events
    WHERE thread_events.thread_id = threads.id
);
