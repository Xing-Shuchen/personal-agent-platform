"""Explicit thread links: storage, migration, and projection contracts."""

import json
import sqlite3
from pathlib import Path

import pytest

from conftest import load_runtime_module
from test_world_historian_runtime import run_runtime

db = load_runtime_module("db")
obsidian = load_runtime_module("obsidian")


def fresh(tmp_path):
    conn = db.connect(tmp_path / "chronicle.sqlite")
    db.migrate(conn)
    return conn


def bundle():
    return {"threads": [
        {"ref": "a", "title": "Alpha", "related_threads": [
            {"thread_ref": "b", "relation_type": "context", "note": "Shared context"},
            {"thread_ref": "b"},
        ]},
        {"ref": "b", "title": "Beta", "related_threads": [
            {"thread_ref": "a", "relation_type": "context"},
        ]},
    ]}


def test_forward_refs_reverse_duplicates_and_updates(tmp_path):
    conn = fresh(tmp_path)
    first = db.store_bundle(conn, bundle())
    second = db.store_bundle(conn, bundle())
    a, b = first["refs"]["a"], first["refs"]["b"]
    assert first == second
    assert first["touched_threads"] == sorted([a, b])
    assert conn.execute("SELECT COUNT(*) FROM thread_relations").fetchone()[0] == 2
    expected = [
        {"thread_id": b, "title": "Beta", "relation_type": "context", "note": "Shared context"},
        {"thread_id": b, "title": "Beta", "relation_type": "related", "note": None},
    ]
    assert db.thread_snapshot(conn, a)["related_threads"] == expected
    assert db.thread_detail(conn, a)["related_threads"] == expected
    assert db.thread_snapshot(conn, b)["related_threads"][0]["thread_id"] == a

    update = db.store_bundle(conn, {"threads": [
        {"id": b, "title": "Beta renamed", "related_threads": [
            {"thread_id": a, "relation_type": "context", "note": "Revised"},
        ]},
    ]})
    assert update["touched_threads"] == sorted([a, b])
    assert db.thread_snapshot(conn, a)["related_threads"][0] == {
        "thread_id": b, "title": "Beta renamed", "relation_type": "context", "note": "Revised",
    }
    renamed = db.store_bundle(conn, {"threads": [{"id": b, "title": "Beta final"}]})
    assert renamed["touched_threads"] == sorted([a, b])
    db.store_bundle(conn, {"threads": [{"id": a, "title": "Alpha", "related_threads": []}]})
    assert conn.execute("SELECT COUNT(*) FROM thread_relations").fetchone()[0] == 2


@pytest.mark.parametrize("links, error", [
    ([{"thread_id": "missing"}], "thread not found"),
    ([{"thread_ref": "a"}], "cannot relate to itself"),
    ([{}], "exactly one"),
    ([{"thread_id": "b", "thread_ref": "b"}], "exactly one"),
    ([{"thread_ref": 123}], "non-empty id or ref"),
    ([{"thread_ref": "b", "relation_type": ""}], "relation_type"),
    ([{"thread_ref": "b", "note": 123}], "note must be a string"),
    ({}, "list of objects"),
])
def test_invalid_links_roll_back_bundle(tmp_path, links, error):
    conn = fresh(tmp_path)
    data = bundle()
    data["threads"][0]["related_threads"] = links
    with pytest.raises(db.ChronicleError, match=error):
        db.store_bundle(conn, data)
    assert conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM thread_relations").fetchone()[0] == 0


def test_schema_enforces_foreign_keys_and_canonical_pair(tmp_path):
    conn = fresh(tmp_path)
    refs = db.store_bundle(conn, bundle())["refs"]
    a, b = sorted(refs.values())
    for endpoints in [(a, a), (b, a), (a, "zz_missing")]:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO thread_relations VALUES (?, ?, 'other', NULL, 'now', 'now')",
                endpoints,
            )
        conn.rollback()


def test_legacy_migration_and_sql_are_idempotent(tmp_path):
    conn = db.connect(tmp_path / "legacy.sqlite")
    migrations = Path(db.__file__).with_name("migrations")
    conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    for path in sorted(migrations.glob("000*.sql")):
        conn.executescript(path.read_text())
        conn.execute("INSERT INTO schema_migrations VALUES (?, 'test')", (path.stem,))
        conn.commit()
    conn.execute("INSERT INTO threads(id, title, created_at, updated_at) VALUES ('old', 'Legacy', 'now', 'now')")
    conn.commit()
    assert db.migrate(conn) == ["0010_thread_relations"]
    assert db.migrate(conn) == []
    sql = (migrations / "0010_thread_relations.sql").read_text()
    conn.executescript(sql)
    conn.executescript(sql)
    db.store_bundle(conn, {"threads": [{"title": "New", "related_threads": [{"thread_id": "old"}]}]})
    snapshot = db.thread_snapshot(conn, "old")
    assert snapshot["title"] == "Legacy"
    assert len(db.search(conn, "Legacy")) == 1
    assert "# 关联 Threads" in obsidian.render_snapshot(snapshot, "now")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_render_empty_compatibility_and_manual_notes_idempotence(tmp_path):
    conn = fresh(tmp_path)
    refs = db.store_bundle(conn, bundle())["refs"]
    snapshot = db.thread_snapshot(conn, refs["a"])
    manual = "My annotation\n\n## Nested heading\nKeep this."
    rendered = obsidian.render_snapshot(snapshot, "now", manual)
    assert "# 关联 Threads\n" in rendered
    assert f"Beta（thread `{refs['b']}`）· context · Shared context" in rendered
    assert obsidian.extract_manual_notes(rendered).strip() == manual
    without = dict(snapshot)
    without.pop("related_threads")
    empty = dict(without, related_threads=[])
    assert obsidian.render_snapshot(without, "now") == obsidian.render_snapshot(empty, "now")
    assert "# 关联 Threads" not in obsidian.render_snapshot(empty, "now")

    projection = tmp_path / "projection"
    index = tmp_path / "index.json"
    result = obsidian.sync_threads([snapshot], projection, index, synced_at="now")
    path = Path(result["written"][0])
    path.write_text(rendered)
    before = path.stat().st_mtime_ns
    repeated = obsidian.sync_threads([snapshot], projection, index, synced_at="later")
    assert repeated["unchanged"] == [str(path)]
    assert path.stat().st_mtime_ns == before
    assert path.read_text() == rendered


def test_cli_thread_contains_links(tmp_path):
    conn = fresh(tmp_path)
    refs = db.store_bundle(conn, bundle())["refs"]
    conn.close()
    result = run_runtime(tmp_path / "chronicle.sqlite", "thread", refs["a"])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["related_threads"][0]["thread_id"] == refs["b"]
