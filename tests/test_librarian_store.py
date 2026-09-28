from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "agents/librarian/runtime"
spec = importlib.util.spec_from_file_location("librarian_store", RUNTIME / "store.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Library, LibrarianError = module.Library, module.LibrarianError


def work(owner: str, object_id: str = "work_one") -> dict:
    return {"object_type": "Work", "schema_version": "0.1.0", "id": object_id,
            "owner_id": owner, "created_at": "2026-09-28T00:00:00+00:00",
            "title": "Synthetic book", "original_title": None,
            "authors": [], "identifiers": [], "revision": 1,
            "supersedes_revision": None}


def test_18_entry_schemas_are_valid_and_reject_unknown_fields():
    schema_dir = RUNTIME / "schemas"
    schema = json.loads((schema_dir / "contracts.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    entries = list(schema_dir.glob("*.schema.json"))
    assert len(entries) == 19  # master plus 18 entry points
    for path in entries:
        Draft202012Validator.check_schema(json.loads(path.read_text()))
    entry = json.loads((schema_dir / "Work.schema.json").read_text())
    resolver = RefResolver.from_schema(entry, store={schema["$id"]: schema})
    Draft202012Validator(entry, resolver=resolver).validate(work("owner_a"))
    module.validate("Work", work("owner_a"))
    with pytest.raises(LibrarianError, match="Additional properties"):
        module.validate("Work", work("owner_a") | {"imaginary": True})


def test_catalog_owner_chain_and_session_progress(tmp_path: Path):
    with Library(tmp_path) as lib:
        lib.register("owner_a", work("owner_a"))
        edition = {"object_type": "Edition", "schema_version": "0.1.0",
                   "id": "edition_one", "owner_id": "owner_a",
                   "created_at": "2026-09-28T00:00:00+00:00", "work_id": "work_one",
                   "edition_label": None, "publisher": None, "publication_year": None,
                   "isbn": {"isbn13": None, "isbn10": None}, "language": None,
                   "page_count": None, "volume_label": None, "revision": 1,
                   "supersedes_revision": None}
        with pytest.raises(LibrarianError) as err:
            lib.register("owner_b", edition)
        assert err.value.code == "UNAUTHORIZED"
        lib.register("owner_a", edition)
        instance = {"object_type": "BookInstance", "schema_version": "0.1.0",
                    "id": "bookinst_one", "owner_id": "owner_a",
                    "created_at": "2026-09-28T00:00:00+00:00",
                    "edition_id": "edition_one", "medium": "physical",
                    "acquired_at": {"value": None, "confidence": None, "basis": "unknown"},
                    "ownership_status": "owned", "physical": {"qr_id": None, "shelf": None},
                    "reading_status": {"state": "reading", "current_page": None,
                                       "progress_evidence_ref": None},
                    "revision": 1, "supersedes_revision": None}
        lib.register("owner_a", instance)
        session = lib.start_session("owner_a", "bookinst_one")
        assert session["started_at"]["value"] is None
        paused = lib.session_transition("owner_a", session["id"], "pause", 1)
        assert paused["status"] == "paused"
        progress = {"start_page": None, "end_page": {"label": "184", "number": 184,
                    "scheme": "arabic"}, "basis": "user_statement",
                    "reported_at": "2026-09-28T00:10:00+00:00", "evidence_ref": "cmd_progress"}
        updated = lib.session_transition("owner_a", session["id"], "report_progress", 2,
                                         progress=progress)
        assert updated["progress"]["end_page"]["number"] == 184
        assert lib.get("owner_a", "BookInstance", "bookinst_one")["reading_status"]["current_page"]["number"] == 184
        unknown_end = dict(progress, end_page=None, evidence_ref="cmd_unknown")
        lib.session_transition("owner_a", session["id"], "report_progress", 3,
                               progress=unknown_end)
        assert lib.get("owner_a", "BookInstance", "bookinst_one")["reading_status"]["current_page"]["number"] == 184
        closed = lib.session_transition("owner_a", session["id"], "close", 4)
        assert closed["ended_at"]["value"] is None
        with pytest.raises(LibrarianError) as err:
            lib.session_transition("owner_a", session["id"], "resume", 5)
        assert err.value.code == "INVALID_STATE_TRANSITION"
        assert [e["event"] for e in lib.pending_events("owner_a")] == [
            "reading.session.started", "reading.session.progressed",
            "reading.session.progressed", "reading.session.closed"]


def test_capture_durability_retry_conflict_and_same_bytes_new_message(tmp_path: Path):
    photo = b"synthetic image bytes"
    args = dict(transport="gateway", account_id="a", conversation_id="c",
                source_event_id="message-1", attachments=[{"source_item_id": "item-1",
                "mime_type": "image/jpeg", "data": photo}], idempotency_key="ingest-1")
    with Library(tmp_path) as lib:
        first = lib.ingest("owner_a", **args)
        assert lib.ingest("owner_a", **args) == first
        assert lib.read_original("owner_a", first["capture_ids"][0]) == photo
        with pytest.raises(LibrarianError) as err:
            lib.read_original("owner_b", first["capture_ids"][0])
        assert err.value.code == "UNAUTHORIZED"
        with pytest.raises(LibrarianError) as err:
            lib.ingest("owner_a", **(args | {"attachments": [{"source_item_id": "item-1",
                         "mime_type": "image/jpeg", "data": b"different"}]}))
        assert err.value.code == "IDEMPOTENCY_CONFLICT"
        second = lib.ingest("owner_a", **(args | {"source_event_id": "message-2",
                                                  "idempotency_key": "ingest-2"}))
        assert second["capture_ids"] != first["capture_ids"]
        a = lib.get("owner_a", "PageCapture", first["capture_ids"][0])
        b = lib.get("owner_a", "PageCapture", second["capture_ids"][0])
        assert a["asset"]["object_key"] == b["asset"]["object_key"]
        assert len(list((tmp_path / "objects").glob("*/*"))) == 1
        assert len(lib.pending_events("owner_a")) == 2
        with pytest.raises(sqlite3.DatabaseError, match="immutable evidence"):
            with lib.db:
                lib.db.execute("UPDATE records SET body='{}' WHERE model='PageCapture'")
    with Library(tmp_path) as reopened:
        assert reopened.read_original("owner_a", first["capture_ids"][0]) == photo


def test_capture_all_or_retry_on_invalid_attachment(tmp_path: Path):
    with Library(tmp_path) as lib:
        with pytest.raises(LibrarianError) as err:
            lib.ingest("owner_a", transport="gateway", account_id="a", conversation_id="c",
                       source_event_id="m", idempotency_key="key", attachments=[
                           {"source_item_id": "i1", "mime_type": "image/jpeg", "data": b"ok"},
                           {"source_item_id": "i2", "mime_type": "image/jpeg", "data": "not bytes"}])
        assert err.value.code == "VALIDATION_FAILED"
        assert not lib.pending_events("owner_a")
        assert lib.db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0
