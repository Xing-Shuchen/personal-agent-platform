"""Tests for the privacy-bounded personal-history lookup adapter."""

import importlib.util
import json
import sqlite3
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def load_lookup():
    path = REPO / "agents/world-historian/runtime/personal_lookup.py"
    spec = importlib.util.spec_from_file_location("personal_lookup", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_lookup_returns_only_redacted_fields(tmp_path):
    db = tmp_path / "chronicle.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE events (id TEXT, summary TEXT, occurred_at TEXT, observed_at TEXT, confidence REAL, status TEXT)")
        conn.execute("CREATE TABLE personal_links (world_event_id TEXT, personal_event_id TEXT, relation_type TEXT)")
        conn.execute("INSERT INTO events VALUES ('world-1', 'OpenAI releases new research model', '2026-09-01', '2026-09-01', .9, 'active')")
    personal = tmp_path / "observations.json"
    personal.write_text(json.dumps([{
        "observation_id": "personal-1", "kind": "bilibili_view_recorded", "domain": "personal",
        "time": {"at": "2026-09-01T10:00:00+08:00"},
        "statement": "PRIVATE WORDING: watched OpenAI research model analysis",
    }]), encoding="utf-8")
    data = load_lookup().lookup(db_path=db, personal_paths=[personal])
    assert data["candidates"][0]["world_event_id"] == "world-1"
    assert data["candidates"][0]["personal_event_id"] == "personal-1"
    rendered = json.dumps(data, ensure_ascii=False)
    assert "PRIVATE WORDING" not in rendered
    assert "watched" not in rendered


def test_lookup_excludes_existing_link_and_weak_overlap(tmp_path):
    db = tmp_path / "chronicle.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE events (id TEXT, summary TEXT, occurred_at TEXT, observed_at TEXT, confidence REAL, status TEXT)")
        conn.execute("CREATE TABLE personal_links (world_event_id TEXT, personal_event_id TEXT, relation_type TEXT)")
        conn.execute("INSERT INTO events VALUES ('world-1', 'OpenAI releases new research model', '2026-09-01', '2026-09-01', .9, 'active')")
        conn.execute("INSERT INTO personal_links VALUES ('world-1', 'personal-1', 'read_about')")
    personal = tmp_path / "observations.json"
    personal.write_text(json.dumps([{
        "observation_id": "personal-1", "kind": "bilibili_view_recorded", "domain": "personal",
        "time": {"at": "2026-09-01T10:00:00+08:00"},
        "statement": "watched OpenAI research model analysis",
    }, {
        "observation_id": "personal-2", "kind": "note", "domain": "personal",
        "time": {"at": "2026-09-01T10:00:00+08:00"},
        "statement": "model",  # one short shared token is insufficient
    }]), encoding="utf-8")
    assert load_lookup().lookup(db_path=db, personal_paths=[personal]) == {"candidates": []}
