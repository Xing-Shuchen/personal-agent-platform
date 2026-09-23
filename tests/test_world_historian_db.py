"""Deeper invariants of the World Historian Chronicle runtime.

Complements ``test_world_historian_runtime.py`` (black-box CLI tests) with
direct checks on migrations, the three event timestamps, dedupe guarantees,
claim supersession, and foreign-key enforcement.
"""

import sqlite3
import subprocess
from pathlib import Path

from conftest import load_runtime_db

REPO = Path(__file__).resolve().parents[1]


def fresh_conn(tmp_path: Path):
    db_mod = load_runtime_db()
    conn = db_mod.connect(tmp_path / "chronicle.sqlite")
    db_mod.migrate(conn)
    return conn, db_mod


def base_bundle() -> dict:
    return {
        "sources": [{"ref": "s1", "canonical_url": "https://example.test/a",
                     "title": "Report A", "source_kind": "primary"}],
        "threads": [{"ref": "t1", "title": "Example transition"}],
        "events": [{"ref": "e1", "title": "Example changed", "summary": "Example changed",
                    "occurred_at": "2026-08-30", "occurred_at_precision": "day",
                    "reported_at": "2026-08-30T09:00:00+08:00",
                    "observed_at": "2026-08-31T12:00:00+08:00",
                    "thread_refs": ["t1"]}],
        "claims": [{"ref": "c1", "event_ref": "e1", "source_ref": "s1",
                    "statement": "Example changed.", "confidence": 0.9}],
    }


def test_migrations_recorded_and_idempotent(tmp_path):
    conn, db = fresh_conn(tmp_path)
    applied = [row[0] for row in conn.execute("SELECT version FROM schema_migrations")]
    assert applied[0] == "0001_initial"
    assert len(applied) == len(set(applied))  # migrations apply exactly once, in order
    # Re-running must be a no-op, never a destructive regeneration.
    assert db.migrate(conn) == []
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    for expected in ("sources", "claims", "events", "threads", "thread_events",
                     "entities", "event_entities", "relations", "watch_queries",
                     "open_questions", "discovery_candidates", "personal_links",
                     "reports", "schema_migrations"):
        assert expected in tables


def test_entity_name_unique_migration_merges_links_and_metadata(tmp_path):
    """0006 retains one deterministic entity and rewrites both link tables."""
    db = load_runtime_db()
    conn = db.connect(tmp_path / "legacy.sqlite")
    migrations = Path(db.__file__).with_name("migrations")
    conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    for path in sorted(migrations.glob("000[1-5]_*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations VALUES (?, 'test')", (path.stem,))
    conn.execute("INSERT INTO entities VALUES ('unknown', 'OpenAI', 'unknown', '[\"OA\"]', '2026-02-01')")
    conn.execute("INSERT INTO entities VALUES ('company', 'OpenAI', 'company', '[\"OpenAI Inc\", \"OA\"]', '2026-01-01')")
    conn.execute("INSERT INTO threads VALUES ('thread', 'Thread', 'active', 'normal', 'x', NULL, NULL, NULL, 0, '2026', '2026')")
    conn.execute("INSERT INTO events(id, summary, observed_at, created_at, updated_at) VALUES ('one', 'one', '2026', '2026', '2026'), ('two', 'two', '2026', '2026', '2026')")
    conn.execute("INSERT INTO event_entities VALUES ('one', 'unknown', 'mentioned'), ('two', 'company', 'mentioned')")
    conn.execute("INSERT INTO thread_entities VALUES ('thread', 'unknown'), ('thread', 'company')")
    conn.commit()

    assert db.migrate(conn) == ["0006_entity_name_unique"]
    assert [tuple(row) for row in conn.execute("SELECT id, name, kind, aliases_json, created_at FROM entities")] == [
        ("company", "OpenAI", "company", '["OpenAI Inc","OA"]', "2026-01-01")]
    assert [tuple(row) for row in conn.execute("SELECT event_id, entity_id, role FROM event_entities ORDER BY event_id")] == [
        ("one", "company", "mentioned"), ("two", "company", "mentioned")]
    assert [tuple(row) for row in conn.execute("SELECT thread_id, entity_id FROM thread_entities")] == [("thread", "company")]
    assert db.migrate(conn) == []


def test_entity_kind_upgrade_preserves_identity_and_known_classification(tmp_path):
    conn, db = fresh_conn(tmp_path)
    db.store_bundle(conn, {"entities": [{"name": "Example", "kind": "unknown"}]})
    first_id = conn.execute("SELECT id FROM entities WHERE name = 'Example'").fetchone()[0]
    db.store_bundle(conn, {"entities": [{"name": "Example", "kind": "company"}]})
    db.store_bundle(conn, {"entities": [{"name": "Example", "kind": "unknown"}]})
    db.store_bundle(conn, {"entities": [{"name": "Example", "kind": "organization"}]})
    assert tuple(conn.execute("SELECT id, kind FROM entities WHERE name = 'Example'").fetchone()) == (
        first_id, "company")


def test_background_thread_priority_is_supported(tmp_path):
    conn, db = fresh_conn(tmp_path)
    db.store_bundle(conn, {"threads": [{
        "title": "Long-running background follow-up", "priority": "background",
    }]})
    assert conn.execute("SELECT priority FROM threads").fetchone()[0] == "background"


def test_three_timestamps_stay_distinct(tmp_path):
    conn, db = fresh_conn(tmp_path)
    db.store_bundle(conn, base_bundle())
    row = conn.execute(
        "SELECT title, occurred_at, occurred_at_precision, reported_at, observed_at"
        " FROM events").fetchone()
    assert row["title"] == "Example changed"
    assert row["occurred_at"] == "2026-08-30"
    assert row["occurred_at_precision"] == "day"
    assert row["reported_at"] == "2026-08-30T09:00:00+08:00"
    assert row["observed_at"] == "2026-08-31T12:00:00+08:00"


def test_event_without_occurrence_time_keeps_null(tmp_path):
    conn, db = fresh_conn(tmp_path)
    bundle = base_bundle()
    bundle["events"][0].pop("occurred_at")
    bundle["events"][0]["occurred_at_precision"] = "unknown"
    db.store_bundle(conn, bundle)
    row = conn.execute("SELECT occurred_at, observed_at FROM events").fetchone()
    assert row["occurred_at"] is None
    assert row["observed_at"] is not None


def test_event_title_must_stay_short(tmp_path):
    conn, db = fresh_conn(tmp_path)
    bundle = base_bundle()
    bundle["events"][0]["title"] = "过" * 61
    try:
        db.store_bundle(conn, bundle)
    except db.ChronicleError as exc:
        assert "event.title must be at most 60 characters" in str(exc)
    else:
        raise AssertionError("an event title must not become a prose summary")
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_thread_title_dedupes_to_stable_id(tmp_path):
    conn, db = fresh_conn(tmp_path)
    first = db.store_bundle(conn, base_bundle())
    second = db.store_bundle(conn, base_bundle())
    assert conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0] == 1
    assert first["refs"]["t1"] == second["refs"]["t1"]
    assert first["refs"]["t1"].startswith("thr_")
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_superseded_claims_are_kept_not_deleted(tmp_path):
    conn, db = fresh_conn(tmp_path)
    first = db.store_bundle(conn, base_bundle())
    claim_id = first["refs"]["c1"]
    revision = base_bundle()
    revision["claims"] = [{
        "ref": "c2", "event_ref": "e1", "source_ref": "s1",
        "statement": "Example changed, later corrected.", "confidence": 0.8,
    }, {
        "ref": "c1", "event_ref": "e1", "source_ref": "s1",
        "statement": "Example changed.", "confidence": 0.9,
        "status": "superseded",
        "superseded_by": "c2",
    }]
    second = db.store_bundle(conn, revision)
    rows = conn.execute(
        "SELECT id, status, superseded_by FROM claims ORDER BY id").fetchall()
    assert len(rows) == 2  # history preserved, nothing deleted
    by_id = {dict(row)["id"]: dict(row) for row in rows}
    assert by_id[claim_id]["status"] == "superseded"
    assert by_id[claim_id]["superseded_by"] == second["refs"]["c2"]
    assert len({claim_id, second["refs"]["c2"]}) == 2  # stable distinct ids


def test_foreign_keys_block_dangling_claim(tmp_path):
    conn, db = fresh_conn(tmp_path)
    bundle = base_bundle()
    bundle["claims"][0]["source_ref"] = "no_such_source"
    try:
        db.store_bundle(conn, bundle)
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("dangling claim reference must be rejected")
    assert conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 0


def test_bad_claim_shape_rolls_back_whole_bundle(tmp_path):
    conn, db = fresh_conn(tmp_path)
    bundle = base_bundle()
    bundle["claims"][0].pop("statement")
    try:
        db.store_bundle(conn, bundle)
    except db.ChronicleError:
        pass
    else:
        raise AssertionError("missing claim statement must be rejected")
    assert conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_runtime_state_is_gitignored():
    """Runtime state is ignored by path, so a new agent cannot leak real data.

    Asserting the behaviour rather than a literal .gitignore line: enumerating
    agents one by one had already missed personal-historian, and its runtime
    directory holds prepared ContextPacks and Event payloads.
    """
    for path in ("var/world-historian/chronicle.sqlite",
                 "var/personal-historian/prepared/run.json",
                 "var/xiaohao/sessions/log.jsonl",
                 "var/state/runs.jsonl"):
        r = subprocess.run(["git", "check-ignore", "-q", path],
                           cwd=REPO, capture_output=True, text=True)
        assert r.returncode == 0, path
