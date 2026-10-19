from datetime import date, datetime
import json
from pathlib import Path

from conftest import load_runtime_db, load_runtime_module
from pap.schedule import matches_schedule
from pap.spec import load_spec


def fixture(tmp_path, monkeypatch):
    runtime = Path(__file__).resolve().parents[1] / "agents/world-historian/runtime"
    monkeypatch.syspath_prepend(str(runtime))
    helper = load_runtime_module("daily_thread_relations")
    db = load_runtime_db()
    conn = db.connect(tmp_path / "chronicle.sqlite")
    db.migrate(conn)
    monkeypatch.setattr(db, "_now", lambda: "2026-10-01T00:00:00+00:00")
    db.store_bundle(conn, {
        "threads": [{"id": name, "title": name} for name in ("a", "b", "c", "quiet")],
        "events": [{"id": "e_" + name, "title": name, "summary": "Historical news",
                    "occurred_at": "2000-01-01", "thread_refs": [name]} for name in ("a", "b", "c")],
        "sources": [{"id": "source", "canonical_url": "https://example.test/report", "title": "Report"}],
        "claims": [{"id": "claim", "event_ref": "e_b", "source_ref": "source", "statement": "Corrected claim"}],
        "relations": [{"id": "existing", "src_type": "thread", "src_ref": "a",
                       "dst_type": "thread", "dst_ref": "b", "relation_type": "echoes", "status": "candidate"}],
    })
    with conn:
        conn.execute("UPDATE events SET updated_at='2026-10-15T16:00:00+00:00' WHERE id='e_a'")
        conn.execute("UPDATE claims SET updated_at='2026-10-16T23:59:59+08:00'")
        conn.execute("UPDATE events SET updated_at='2026-10-16T16:00:00+00:00' WHERE id='e_c'")
        conn.execute("UPDATE threads SET updated_at='2026-10-16T08:00:00Z',last_checked_at='2026-10-16T16:00:00+08:00' WHERE id='quiet'")
        conn.execute("UPDATE relations SET updated_at='2026-10-16T08:00:00Z'")
    return helper, conn


def test_local_day_tracks_content_updates_not_old_occurrence_or_quiet_poll(tmp_path, monkeypatch):
    helper, conn = fixture(tmp_path, monkeypatch)
    rows = helper.updated_threads(conn, date(2026, 10, 16))
    assert [r["id"] for r in rows] == ["a", "b"]
    assert rows[0]["update_reasons"] == ["event"]
    assert rows[1]["update_reasons"] == ["claim"]
    assert [r["id"] for r in helper.updated_threads(conn, date(2026, 10, 17))] == ["c"]


def test_prepare_keeps_existing_relations_sources_and_does_not_write_database(tmp_path, monkeypatch):
    helper, conn = fixture(tmp_path, monkeypatch)
    before = conn.total_changes
    out = tmp_path / "review"
    manifest = helper.prepare(conn, date(2026, 10, 16), out)
    assert manifest["thread_count"] == 2 and manifest["pair_count"] == 1
    pair = json.loads((out / "pairs.json").read_text())[0]
    assert (pair["a"], pair["b"]) == ("a", "b")
    assert pair["existing_thread_relations"][0]["id"] == "existing"
    evidence = json.loads((out / manifest["threads"][1]["evidence_file"]).read_text())
    assert evidence["sources"][0]["canonical_url"] == "https://example.test/report"
    assert evidence["events"][0]["claims"][0]["id"] == "claim"
    assert conn.total_changes == before
    empty = helper.prepare(conn, date(2026, 9, 1), tmp_path / "empty")
    assert empty["thread_count"] == empty["pair_count"] == 0


def test_nightly_job_uses_pap_local_delivery_and_explicit_timezone():
    root = Path(__file__).resolve().parents[1]
    spec = load_spec(root / "agents/world-historian/agent.yaml")
    job = next(j for j in spec.jobs if j.name == "world-thread-relations-nightly")
    assert job.enabled and job.delivery == "local" and not job.attach_to_session
    assert job.skill == "news-thread-relations" and job.timezone == "Asia/Shanghai"
    assert matches_schedule(job.schedule, datetime.fromisoformat("2026-10-16T15:50:00+00:00"), timezone_name=job.timezone)
    assert not matches_schedule(job.schedule, datetime.fromisoformat("2026-10-16T23:50:00+00:00"), timezone_name=job.timezone)
