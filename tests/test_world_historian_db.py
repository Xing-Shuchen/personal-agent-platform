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
        "events": [{"ref": "e1", "summary": "Example changed",
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
        "SELECT occurred_at, occurred_at_precision, reported_at, observed_at"
        " FROM events").fetchone()
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
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "var/world-historian/" in gitignore
    r = subprocess.run(
        ["git", "check-ignore", "-q", "var/world-historian/chronicle.sqlite"],
        cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0
