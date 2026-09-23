-- Entity names are canonical identifiers.  Legacy non-vocabulary labels are
-- deliberately made unknown so they can be reviewed through reclassification.
PRAGMA foreign_keys = OFF;

CREATE TEMP TABLE entity_merge AS
WITH normalized AS (
    SELECT id, name,
           CASE WHEN kind IN ('company', 'organization', 'person', 'product',
                              'model', 'software', 'benchmark', 'aggregator',
                              'media', 'government', 'place', 'concept', 'unknown')
                THEN kind ELSE 'unknown' END AS kind,
           aliases_json, created_at
    FROM entities
), ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
             PARTITION BY name
             ORDER BY CASE kind WHEN 'unknown' THEN 1 ELSE 0 END,
                      CASE kind
                        WHEN 'company' THEN 0 WHEN 'organization' THEN 1
                        WHEN 'person' THEN 2 WHEN 'product' THEN 3
                        WHEN 'model' THEN 4 WHEN 'software' THEN 5
                        WHEN 'benchmark' THEN 6 WHEN 'aggregator' THEN 7
                        WHEN 'media' THEN 8 WHEN 'government' THEN 9
                        WHEN 'place' THEN 10 WHEN 'concept' THEN 11 ELSE 12 END,
                      id
           ) AS rank_in_name
    FROM normalized
)
SELECT id AS old_id, name,
       FIRST_VALUE(id) OVER (PARTITION BY name ORDER BY rank_in_name) AS survivor_id,
       FIRST_VALUE(kind) OVER (PARTITION BY name ORDER BY rank_in_name) AS survivor_kind,
       aliases_json, created_at
FROM ranked;

CREATE TABLE entities_new (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL DEFAULT 'unknown'
        CHECK (kind IN ('company', 'organization', 'person', 'product', 'model',
                        'software', 'benchmark', 'aggregator', 'media', 'government',
                        'place', 'concept', 'unknown')),
    aliases_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

INSERT INTO entities_new(id, name, kind, aliases_json, created_at)
SELECT survivor_id, name, survivor_kind,
       COALESCE((
         SELECT json_group_array(value) FROM (
           SELECT value, MIN(position) AS first_position FROM (
             SELECT je.value,
                    printf('%s|%s|%08d', m.created_at, m.old_id, je.key) AS position
             FROM entity_merge AS m JOIN json_each(m.aliases_json) AS je
               WHERE m.name = winners.name
           ) GROUP BY value ORDER BY first_position
         )
       ), '[]'),
       MIN(created_at)
FROM entity_merge AS winners
WHERE old_id = survivor_id
GROUP BY survivor_id, name, survivor_kind;

INSERT OR IGNORE INTO event_entities(event_id, entity_id, role)
SELECT ee.event_id, m.survivor_id, ee.role
FROM event_entities AS ee JOIN entity_merge AS m ON m.old_id = ee.entity_id;
DELETE FROM event_entities
WHERE entity_id IN (SELECT old_id FROM entity_merge WHERE old_id != survivor_id);

INSERT OR IGNORE INTO thread_entities(thread_id, entity_id)
SELECT te.thread_id, m.survivor_id
FROM thread_entities AS te JOIN entity_merge AS m ON m.old_id = te.entity_id;
DELETE FROM thread_entities
WHERE entity_id IN (SELECT old_id FROM entity_merge WHERE old_id != survivor_id);

DROP TABLE entities;
ALTER TABLE entities_new RENAME TO entities;
DROP TABLE entity_merge;
PRAGMA foreign_keys = ON;
