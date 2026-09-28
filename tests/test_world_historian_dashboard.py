"""Contract tests for Chronicle → disposable dashboard generation."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from conftest import load_runtime_db, load_runtime_module


def fixture_db(path: Path) -> None:
    db = load_runtime_db()
    conn = db.connect(path)
    db.migrate(conn)
    with conn:
        conn.execute("INSERT INTO threads (id,title,status,priority,created_at,updated_at,last_event_ingested_at) VALUES ('t1','Trade route','active','high','2026-01-01','2026-01-01','2026-02-03')")
        conn.execute("INSERT INTO threads (id,title,status,priority,created_at,updated_at) VALUES ('t2','Empty thread','closed','low','2026-01-02','2026-08-01')")
        conn.execute("INSERT INTO events (id,title,summary,occurred_at,occurred_at_precision,reported_at,observed_at,created_at,updated_at) VALUES ('e1','Route changed','Vessels diverted','2026-02-01','day','2026-02-02','2026-02-03','2026-02-03','2026-02-03')")
        conn.execute("INSERT INTO thread_events (thread_id,event_id,created_at) VALUES ('t1','e1','2026-02-03')")
        conn.execute("INSERT INTO sources (id,canonical_url,title,source_kind,fetched_at,created_at) VALUES ('s1','https://example.test/report','Report','primary','2026-02-03','2026-02-03')")
        conn.execute("INSERT INTO claims (id,event_id,source_id,statement,asserted_at,confidence,status,created_at,updated_at) VALUES ('c1','e1','s1','Traffic declined','2026-02-02',0.8,'disputed','2026-02-03','2026-02-04')")
        conn.execute("INSERT INTO entities (id,name,kind,aliases_json,created_at) VALUES ('actor1','Carrier','company','[]','2026-01-01')")
        conn.execute("INSERT INTO event_entities VALUES ('e1','actor1','involved')")
        conn.execute("INSERT INTO open_questions (id,thread_id,question,status,created_at,updated_at) VALUES ('q1','t1','When will traffic recover?','open','2026-02-03','2026-02-05')")
        conn.execute("INSERT INTO relations (id,src_type,src_id,dst_type,dst_id,relation_type,confidence,evidence_json,status,created_at,updated_at) VALUES ('r1','event','e1','location','loc1','occurs_at',0.8,'[]','active','2026-02-03','2026-02-03')")
    conn.close()


def generation(output: Path) -> Path:
    return output / "generations" / (output / "CURRENT").read_text().strip()


def test_projection_preserves_semantics_and_canonical_database(tmp_path):
    projector = load_runtime_module("dashboard_projector")
    db_path, output = tmp_path / "chronicle.sqlite", tmp_path / "dashboard"
    fixture_db(db_path)
    before = hashlib.sha256(db_path.read_bytes()).digest()
    manifest = projector.publish(db_path, output)
    root = generation(output)
    assert manifest["thread_count"] == 2
    assert manifest["event_count"] == 1
    assert manifest["location_count"] == 0  # relation alone does not invent coordinates
    thread = json.loads((root / "threads" / "t1.json").read_text())
    assert thread["current_state"]["provenance"] == "unavailable"
    assert thread["last_meaningful_change_at"] == "2026-02-05"
    assert thread["attention"]["reasons"] == ["contested_or_corrected_claim", "high_priority_open_questions"]
    assert thread["activity_series"]["measure"] == "event_count"
    assert thread["activity_series"]["aggregation"] == "week"
    assert len(thread["activity_series"]["bins"]) == 12
    assert sum(bin["count"] for bin in thread["activity_series"]["bins"]) == 1
    assert {"claim_contested", "open_question"} <= set(thread["recent_change_types"])
    assert json.loads((root / "threads" / "t2.json").read_text())["event_ids"] == []
    assert json.loads((root / "threads" / "t2.json").read_text())["activity_series"]["bins"] == []
    event = json.loads((root / "events" / "e1.json").read_text())
    assert event["occurred_at"] == "2026-02-01" and event["time_precision"] == "day"
    assert event["claims"][0]["state"] == "contested"
    assert event["claims"][0]["source"]["url"] == "https://example.test/report"
    entity = json.loads((root / "entities" / "actor1.json").read_text())
    assert entity["current_thread_ids"] == ["t1"]
    assert entity["contextual_questions"][0]["owner_thread_id"] == "t1"
    assert sum(bin["count"] for bin in entity["activity_series"]["bins"]) == 1
    buckets = [json.loads(path.read_text()) for path in (root / "graph").glob("*.json")]
    assert {"thread", "event", "claim", "source", "entity", "question"} <= {node["type"] for bucket in buckets for node in bucket["nodes"].values()}
    assert {edge["type"] for bucket in buckets for edges in bucket["adjacency"].values() for edge in edges} >= {"event_contains_claim", "claim_supported_by_source", "question_about_thread"}
    assert hashlib.sha256(db_path.read_bytes()).digest() == before
    assert projector.publish(db_path, output)["source_revision"] == manifest["source_revision"]
    assert len(list((output / "generations").iterdir())) == 1


def test_bad_location_registry_keeps_previous_generation(tmp_path):
    projector = load_runtime_module("dashboard_projector")
    db_path, output = tmp_path / "chronicle.sqlite", tmp_path / "dashboard"
    fixture_db(db_path)
    projector.publish(db_path, output)
    previous = (output / "CURRENT").read_text()
    registry = tmp_path / "locations.json"
    registry.write_text(json.dumps([{"location_id": "loc1", "name": "Port", "lat": 120,
                                     "lon": 1, "geo_precision": "city", "canonical_source_ref": {"kind": "manual"}}]))
    with pytest.raises(ValueError, match="invalid location coordinates"):
        projector.publish(db_path, output, location_registry=registry)
    assert (output / "CURRENT").read_text() == previous
    projector.validate(generation(output))


def test_corrected_claim_has_visual_change_marker(tmp_path):
    projector = load_runtime_module("dashboard_projector")
    db = load_runtime_db()
    db_path, output = tmp_path / "chronicle.sqlite", tmp_path / "dashboard"
    fixture_db(db_path)
    conn = db.connect(db_path)
    with conn:
        conn.execute("UPDATE claims SET status='superseded' WHERE id='c1'")
    conn.close()
    projector.publish(db_path, output)
    thread = next(row for row in json.loads((generation(output) / "threads.json").read_text()) if row["thread_id"] == "t1")
    assert "claim_corrected" in thread["recent_change_types"]
    assert thread["attention"]["required"] is True


def test_explicit_geography_and_vault_reference(tmp_path):
    projector = load_runtime_module("dashboard_projector")
    db_path, output = tmp_path / "chronicle.sqlite", tmp_path / "dashboard"
    fixture_db(db_path)
    vault = tmp_path / "vault"
    note = vault / "2Area" / "41 新闻及事件" / "Trade route.md"
    note.parent.mkdir(parents=True)
    note.write_text('---\nthread_id: "t1"\n---\n# 手工批注\n\nCheck customs figures.\n')
    registry = tmp_path / "locations.json"
    registry.write_text(json.dumps([{"location_id": "loc1", "name": "Port", "lat": 12.5,
                                     "lon": 43.3, "geo_precision": "city", "canonical_source_ref": {"kind": "manual_registry", "id": "loc1"}}]))
    projector.publish(db_path, output, location_registry=registry, vault_dir=vault)
    root = generation(output)
    location = json.loads((root / "locations.json").read_text())[0]
    assert location["event_ids"] == ["e1"] and location["thread_ids"] == ["t1"]
    thread = json.loads((root / "threads" / "t1.json").read_text())
    assert thread["canonical_ref"]["obsidian_path"] == "2Area/41 新闻及事件/Trade route.md"
    assert thread["annotations"][0]["text"] == "Check customs figures."
    assert thread["annotations"][0]["provenance"] == "manual"
    event = json.loads((root / "events" / "e1.json").read_text())
    assert event["location_ids"] == ["loc1"]
    note.rename(note.with_name("Renamed.md"))
    projector.publish(db_path, output, location_registry=registry, vault_dir=vault)
    renamed = json.loads((generation(output) / "threads" / "t1.json").read_text())
    assert renamed["thread_id"] == "t1"
    assert renamed["canonical_ref"]["obsidian_path"].endswith("Renamed.md")


def test_canonical_current_state_is_distinct_and_stale_when_events_are_newer(tmp_path):
    db = load_runtime_db()
    projector = load_runtime_module("dashboard_projector")
    db_path, output = tmp_path / "chronicle.sqlite", tmp_path / "dashboard"
    fixture_db(db_path)
    conn = db.connect(db_path)
    with conn:
        conn.execute("INSERT INTO thread_current_states VALUES ('t1','Traffic remains diverted','historian_generated','[\"e1\"]','rev-1','2026-02-02')")
    conn.close()
    projector.publish(db_path, output)
    thread = json.loads((generation(output) / "threads" / "t1.json").read_text())
    assert thread["current_state"]["text"] == "Traffic remains diverted"
    assert thread["current_state"]["provenance"] == "historian_generated"
    assert thread["current_state"]["stale"] is True
    assert thread["current_state"]["source_refs"] == ["e1"]


def test_current_state_bundle_records_provenance_and_rejects_invalid_state(tmp_path):
    db = load_runtime_db()
    db_path = tmp_path / "chronicle.sqlite"
    fixture_db(db_path)
    conn = db.connect(db_path)
    outcome = db.store_bundle(conn, {"thread_states": [{"thread_ref": "t1", "text": "Manual review", "provenance": "manual", "source_refs": ["e1"]}]})
    assert "t1" in outcome["touched_threads"]
    state = db.thread_snapshot(conn, "t1")["current_state"]
    assert state["body"] == "Manual review" and state["provenance"] == "manual"
    with pytest.raises(db.ChronicleError, match="provenance"):
        db.store_bundle(conn, {"thread_states": [{"thread_ref": "t1", "text": "Invalid", "provenance": "unknown"}]})
    assert db.thread_snapshot(conn, "t1")["current_state"]["body"] == "Manual review"
    created = db.store_bundle(conn, {"threads": [{"ref": "new_thread", "title": "New thread"}],
                                     "events": [{"ref": "new_event", "summary": "New evidence", "thread_refs": ["new_thread"]}],
                                     "thread_states": [{"thread_ref": "new_thread", "text": "New state", "source_refs": ["new_event"]}]})
    new_tid = created["touched_threads"][0]
    new_state = db.thread_snapshot(conn, new_tid)["current_state"]
    assert json.loads(new_state["source_refs_json"])[0].startswith("evt_")
    conn.close()


def test_meaningful_change_uses_instants_across_timezones():
    projector = load_runtime_module("dashboard_projector")
    assert projector._meaningful("2026-01-01T23:30:00+08:00", "2026-01-01T16:00:00Z") == "2026-01-01T16:00:00Z"


def test_incremental_generation_reuses_unaffected_details(tmp_path):
    projector = load_runtime_module("dashboard_projector")
    db_path, output = tmp_path / "chronicle.sqlite", tmp_path / "dashboard"
    fixture_db(db_path)
    projector.publish(db_path, output)
    previous = generation(output)
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE open_questions SET updated_at = '2026-03-01' WHERE id = 'q1'")
    conn.commit()
    conn.close()
    manifest = projector.publish(db_path, output)
    current = generation(output)
    assert current != previous
    assert manifest["reused_file_count"] > 0
    assert (previous / "events" / "e1.json").stat().st_ino == (current / "events" / "e1.json").stat().st_ino
    assert (previous / "threads" / "t1.json").stat().st_ino != (current / "threads" / "t1.json").stat().st_ino


def test_deleted_read_model_rebuilds_same_semantic_state(tmp_path):
    projector = load_runtime_module("dashboard_projector")
    db_path, output = tmp_path / "chronicle.sqlite", tmp_path / "dashboard"
    fixture_db(db_path)
    projector.publish(db_path, output)
    first = generation(output)
    semantic = {name: (first / name).read_bytes() for name in ("threads.json", "timeline-partitions.json", "timeline/2026-02.json", "entities.json", "locations.json", "graph-manifest.json", "threads/t1.json", "events/e1.json")}
    shutil.rmtree(output)
    projector.publish(db_path, output)
    second = generation(output)
    assert {name: (second / name).read_bytes() for name in semantic} == semantic


def test_canonical_inspector_is_read_only_and_whitelisted(tmp_path):
    projector = load_runtime_module("dashboard_projector")
    db_path = tmp_path / "chronicle.sqlite"
    fixture_db(db_path)
    before = hashlib.sha256(db_path.read_bytes()).digest()
    assert projector.inspect_canonical(db_path, "events", "e1")["record"]["summary"] == "Vessels diverted"
    with pytest.raises(ValueError, match="unsupported"):
        projector.inspect_canonical(db_path, "sqlite_master", "x")
    assert hashlib.sha256(db_path.read_bytes()).digest() == before
