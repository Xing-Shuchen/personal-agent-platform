CREATE TABLE IF NOT EXISTS digital_source_owners (
  kind TEXT NOT NULL CHECK (kind IN ('koodo', 'weread')),
  source_id TEXT NOT NULL,
  owner_id TEXT NOT NULL,
  PRIMARY KEY (kind, source_id)
);

INSERT OR IGNORE INTO digital_source_owners(kind, source_id, owner_id)
SELECT 'koodo', source_id, MIN(owner_id)
FROM koodo_native_records
GROUP BY source_id
HAVING COUNT(DISTINCT owner_id) = 1;

INSERT OR IGNORE INTO digital_source_owners(kind, source_id, owner_id)
SELECT 'weread', source_id, MIN(owner_id)
FROM weread_native_records
GROUP BY source_id
HAVING COUNT(DISTINCT owner_id) = 1;
