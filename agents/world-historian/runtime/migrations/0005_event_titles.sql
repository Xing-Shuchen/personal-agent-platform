-- Event headings and event bodies have distinct jobs in the Obsidian projection.
-- Existing rows remain valid and receive a deterministic renderer fallback.
ALTER TABLE events ADD COLUMN title TEXT;
