"""Regression tests for World Historian defects confirmed in the 2026-10 audit.

Pins: concurrent migration safety, omitted-field carry-through in bundle
upserts, case-variant entity resolution, thread-note filename collisions,
timezone normalization in lifecycle timestamps, per-feed database failure
isolation, loud feed-config errors, personal-lookup input containment, and
daily-stats tolerance for a missing/partial run log.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from conftest import load_runtime_module

db = load_runtime_module("db")
feeds = load_runtime_module("feeds")
obsidian = load_runtime_module("obsidian")
cli = load_runtime_module("cli")
personal_lookup = load_runtime_module("personal_lookup")

CST = timezone(timedelta(hours=8))


def fresh(tmp_path: Path):
    conn = db.connect(tmp_path / "chronicle.sqlite")
    db.migrate(conn)
    return conn


def thread_bundle(title: str, **extra) -> dict:
    return {"threads": [{"id": "thr_1", "title": title, **extra}]}


# ---------------------------------------------------------------------------
# migrations


def test_concurrent_migrations_apply_each_script_once(tmp_path):
    path = tmp_path / "chronicle.sqlite"
    errors: list[BaseException] = []

    def migrate_once():
        try:
            conn = db.connect(path)
            try:
                db.migrate(conn)
            finally:
                conn.close()
        except BaseException as exc:  # noqa: BLE001 - collected for the assert
            errors.append(exc)

    threads = [threading.Thread(target=migrate_once) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    conn = db.connect(path)
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    conn.close()
    on_disk = {p.stem for p in Path(db.__file__).with_name("migrations").glob("*.sql")}
    assert applied == on_disk


def test_migrate_is_idempotent_and_records_versions_atomically(tmp_path):
    conn = fresh(tmp_path)
    assert db.migrate(conn) == []
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    assert [row[0] for row in rows] == sorted(
        p.stem for p in Path(db.__file__).with_name("migrations").glob("*.sql"))


# ---------------------------------------------------------------------------
# bundle upserts must not reset omitted fields


def test_thread_upsert_preserves_omitted_lifecycle_state(tmp_path):
    conn = fresh(tmp_path)
    db.store_bundle(conn, thread_bundle(
        "Example", status="closed", priority="low", quiet_count=7,
        seed_type="user_instruction"))
    # A later bundle re-declaring only id+title must not undo the lifecycle.
    db.store_bundle(conn, {"threads": [{"id": "thr_1", "title": "Example"}]})
    row = conn.execute("SELECT status, priority, quiet_count, seed_type FROM threads").fetchone()
    assert (row["status"], row["priority"], row["quiet_count"], row["seed_type"]) == (
        "closed", "low", 7, "user_instruction")
    # Explicit values still apply.
    db.store_bundle(conn, thread_bundle("Example", status="active"))
    assert conn.execute("SELECT status, quiet_count FROM threads").fetchone()[0] == "active"
    assert conn.execute("SELECT quiet_count FROM threads").fetchone()[0] == 7


def test_event_upsert_preserves_omitted_evidence_fields(tmp_path):
    conn = fresh(tmp_path)
    db.store_bundle(conn, {"events": [{
        "id": "evt_1", "summary": "Example changed",
        "occurred_at": "2026-09-01T10:00:00+08:00", "occurred_at_precision": "instant",
        "reported_at": "2026-09-01T12:00:00+08:00", "confidence": 0.9,
        "status": "confirmed",
    }]})
    db.store_bundle(conn, {"events": [{"id": "evt_1", "summary": "Example changed (updated)"}]})
    row = conn.execute(
        "SELECT summary, occurred_at, occurred_at_precision, reported_at, confidence, status "
        "FROM events").fetchone()
    assert row["summary"] == "Example changed (updated)"
    assert row["occurred_at"] == "2026-09-01T10:00:00+08:00"
    assert row["occurred_at_precision"] == "instant"
    assert row["reported_at"] == "2026-09-01T12:00:00+08:00"
    assert row["confidence"] == 0.9
    assert row["status"] == "confirmed"


def test_quote_upsert_preserves_omitted_links_and_format(tmp_path):
    conn = fresh(tmp_path)
    base = {
        "sources": [{"id": "src_1", "canonical_url": "https://example.test/a",
                     "title": "Report A"}],
        "events": [{"id": "evt_1", "summary": "Example changed"}],
    }
    bundle = dict(base)
    bundle["quotes"] = [{
        "id": "qte_1", "event_ref": "evt_1", "quote_text": "We changed it.",
        "quote_format": "markdown", "speaker": "Spokesperson",
        "url": "https://example.test/a#q", "fetched_at": "2026-09-01T12:00:00+08:00",
    }]
    db.store_bundle(conn, bundle)
    again = dict(base)
    again["quotes"] = [{"id": "qte_1", "source_ref": "src_1", "quote_text": "We changed it."}]
    db.store_bundle(conn, again)
    row = conn.execute(
        "SELECT event_id, source_id, speaker, quote_format, url, fetched_at FROM quotes").fetchone()
    assert row["event_id"] == "evt_1"       # kept, not clobbered to NULL
    assert row["source_id"] == "src_1"      # newly provided link applied
    assert row["speaker"] == "Spokesperson"
    assert row["quote_format"] == "markdown"
    assert row["url"] == "https://example.test/a#q"
    assert row["fetched_at"] == "2026-09-01T12:00:00+08:00"


def test_thread_state_revision_is_not_clobbered(tmp_path):
    conn = fresh(tmp_path)
    db.store_bundle(conn, {"threads": [{"id": "thr_1", "title": "Example"}],
                           "thread_states": [{"thread_ref": "thr_1", "text": "b1",
                                              "revision": "rev-2"}]})
    db.store_bundle(conn, {"threads": [{"id": "thr_1", "title": "Example"}],
                           "thread_states": [{"thread_ref": "thr_1", "text": "b2"}]})
    row = conn.execute("SELECT body, revision FROM thread_current_states").fetchone()
    assert (row["body"], row["revision"]) == ("b2", "rev-2")


def test_case_variant_entity_names_resolve_to_one_row(tmp_path):
    conn = fresh(tmp_path)
    db.store_bundle(conn, {"entities": [{"name": "OpenAI", "kind": "company"}]})
    # Previously raised a raw IntegrityError (UNIQUE entities.id) and rolled
    # the whole bundle back.
    db.store_bundle(conn, {"entities": [{"name": "openai", "kind": "company"}]})
    rows = conn.execute("SELECT id, name, kind FROM entities").fetchall()
    assert len(rows) == 1
    assert rows[0]["name"] == "OpenAI"  # first-seen spelling stays canonical
    assert rows[0]["kind"] == "company"


# ---------------------------------------------------------------------------
# obsidian sync


def test_same_batch_filename_collision_does_not_clobber_notes(tmp_path):
    conn = fresh(tmp_path)
    db.store_bundle(conn, {"threads": [
        {"id": "thr_a", "title": "Foo/Bar"},
        {"id": "thr_b", "title": "Foo:Bar"},  # sanitizes to the same filename
    ]})
    vault = tmp_path / "vault"
    index_path = tmp_path / "obsidian-index.json"
    snapshots = [db.thread_snapshot(conn, tid) for tid in ("thr_a", "thr_b")]
    first = obsidian.sync_threads(snapshots, vault, index_path)
    assert first["errors"] == []
    files = sorted(p.name for p in vault.glob("*.md"))
    assert len(files) == 2, files
    # Full re-sync (what `cli.py sync` does) must keep both projections.
    second = obsidian.sync_threads(
        [db.thread_snapshot(conn, tid) for tid in ("thr_a", "thr_b")], vault, index_path)
    assert second["errors"] == []
    index = json.loads(index_path.read_text(encoding="utf-8"))
    mapped = set(index["threads"].values())
    assert len(mapped) == 2
    assert sorted(p.name for p in vault.glob("*.md")) == files
    bodies = {p.read_text(encoding="utf-8") for p in vault.glob("*.md")}
    assert any("thr_a" in body for body in bodies)
    assert any("thr_b" in body for body in bodies)


# ---------------------------------------------------------------------------
# lifecycle timezone normalization


def test_lifecycle_timestamp_normalizes_offsets():
    utc = cli._lifecycle_timestamp("2026-09-16T16:00:00Z")
    local = cli._lifecycle_timestamp("2026-09-17T00:00:00+08:00")
    assert utc == local  # the same instant must compare equal
    naive = cli._lifecycle_timestamp("2026-09-17T00:00:00")
    assert naive == datetime(2026, 9, 17, 0, 0)  # naive stays local wall time
    assert cli._lifecycle_timestamp("garbage") is None
    assert cli._lifecycle_timestamp(None) is None


# ---------------------------------------------------------------------------
# feeds


def test_missing_feed_config_fails_loudly(tmp_path):
    with pytest.raises(feeds.ChronicleError, match="unreadable"):
        feeds.configured_rss_sources(tmp_path / "missing.yaml")


def test_malformed_feed_config_fails_loudly(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("sources: [unclosed\n", encoding="utf-8")
    with pytest.raises(feeds.ChronicleError, match="not valid YAML"):
        feeds.configured_rss_sources(config)


class _LockExplodingConn:
    """A connection whose writes hit a concurrent-writer lock."""

    def execute(self, sql, *args):
        if sql.lstrip().upper().startswith("INSERT"):
            raise sqlite3.OperationalError("database is locked")

        class _None:
            def fetchone(self):
                return None
        return _None()

    def commit(self):
        pass

    def rollback(self):
        pass


def test_database_lock_is_one_feeds_error_not_a_dead_job(tmp_path):
    result = feeds.ingest_feed(_LockExplodingConn(), feed_name="A",
                               feed_url="https://a.test/feed",
                               fetch=lambda url: RSS_SAMPLE)
    assert result["error"] is not None
    assert "database is locked" in result["error"]
    assert result["added"] == 0


RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>A</title>
<item><title>Alpha</title><link>https://a.test/1</link>
<pubDate>Wed, 16 Sep 2026 01:00:00 GMT</pubDate><description>Alpha</description></item>
</channel></rss>"""


def test_feeds_update_uses_the_repository_venv_interpreter():
    """The manifest command must match the documented interpreter (PyYAML)."""
    import yaml  # the repo venv has it; the point is the manifest's argv[0]

    manifest = yaml.safe_load(
        (Path(db.__file__).parents[1] / "agent.yaml").read_text(encoding="utf-8"))
    jobs = manifest["spec"]["proactive"]["desired_jobs"]
    feeds_job = next(job for job in jobs if job["name"] == "world-feeds")
    assert feeds_job["command"][0] == ".venv/bin/python"


# ---------------------------------------------------------------------------
# personal lookup containment


def test_personal_lookup_contains_bad_inputs(tmp_path):
    chronicle = tmp_path / "chronicle.sqlite"
    with sqlite3.connect(chronicle) as conn:
        conn.execute("CREATE TABLE events (id TEXT, summary TEXT, occurred_at TEXT, "
                     "observed_at TEXT, confidence REAL, status TEXT)")
        conn.execute("CREATE TABLE personal_links (world_event_id TEXT, "
                     "personal_event_id TEXT, relation_type TEXT)")
        conn.execute("INSERT INTO events VALUES ('w1', 'OpenAI research model', "
                     "'2026-09-01', '2026-09-01', .9, 'active')")
    good = tmp_path / "good.json"
    good.write_text(json.dumps([{
        "observation_id": "p1", "kind": "note", "domain": "personal",
        "time": {"at": "2026-09-01T10:00:00+08:00"},
        "statement": "OpenAI research model notes",
    }]), encoding="utf-8")
    missing = tmp_path / "missing.json"
    broken_json = tmp_path / "broken.json"
    broken_json.write_text('{"truncated": ', encoding="utf-8")
    not_utf8 = tmp_path / "binary.json"
    not_utf8.write_bytes(b"\xff\xfe\x00bad")
    not_a_list = tmp_path / "dict.json"
    not_a_list.write_text('{"a": 1}', encoding="utf-8")
    a_directory = tmp_path / "dir.json"
    a_directory.mkdir()

    result = personal_lookup.lookup(
        db_path=chronicle,
        personal_paths=[missing, broken_json, not_utf8, not_a_list, a_directory, good])
    # The healthy file still matches; every bad input is reported, none crashes.
    assert [c["personal_event_id"] for c in result["candidates"]] == ["p1"]
    assert len(result["errors"]) == 5
    rendered = json.dumps(result, ensure_ascii=False)
    assert "OpenAI research model notes" not in rendered  # privacy contract holds

    # A missing database degrades the same way.
    only_bad = personal_lookup.lookup(db_path=tmp_path / "absent.sqlite",
                                      personal_paths=[good])
    assert only_bad["candidates"] == []
    assert any("absent.sqlite" in error for error in only_bad["errors"])


def test_personal_lookup_cli_rejects_out_of_range_limit(tmp_path):
    script = Path(personal_lookup.__file__)
    proc = subprocess.run(
        [sys.executable, str(script), "--limit", "11"],
        capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "PAP_PERSONAL_INPUTS": "",
             "PAP_ROOT": str(Path(db.__file__).parents[3])})
    assert proc.returncode == 2
    assert "between 1 and 10" in proc.stderr


# ---------------------------------------------------------------------------
# daily-stats tolerance


def test_daily_stats_tolerates_missing_and_truncated_run_logs(tmp_path, capsys):
    conn = fresh(tmp_path)
    db.store_bundle(conn, thread_bundle("Example"))
    missing = tmp_path / "absent-runs.jsonl"
    cli._print_daily_stats(conn, "2026-09-16", missing)
    out = capsys.readouterr().out
    assert out.startswith("day 2026-09-16\nruns\nchronicle\n")

    partial = tmp_path / "runs.jsonl"
    partial.write_text(
        '{"event":"run.completed","run_id":"r1","agent_id":"world-historian",'
        '"completed_at":"2026-09-16T09:00:00+08:00","status":"success",'
        '"job_id":"world-historian/world-feeds"}\n{"event": "run.comp\n',
        encoding="utf-8")
    cli._print_daily_stats(conn, "2026-09-16", partial)
    out = capsys.readouterr().out
    assert "job world-historian/world-feeds delivery:not-attempted=1 success=1" in out
