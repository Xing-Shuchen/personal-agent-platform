from __future__ import annotations

import importlib.util
import json
import sqlite3
from datetime import datetime, timedelta, timezone
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
    with pytest.raises(LibrarianError, match="additionalProperties constraint"):
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


def test_storage_rejects_cross_owner_and_inconsistent_catalog_links(tmp_path: Path):
    with Library(tmp_path) as lib:
        lib.register("owner_a", work("owner_a"))
        lib.register("owner_a", work("owner_a", "work_other"))
        lib.register("owner_b", work("owner_b", "work_foreign"))
        edition = {"object_type": "Edition", "schema_version": "0.1.0",
                   "id": "edition_valid", "owner_id": "owner_a",
                   "created_at": "2026-09-28T00:00:00+00:00", "work_id": "work_one",
                   "edition_label": None, "publisher": None, "publication_year": None,
                   "isbn": {"isbn13": None, "isbn10": None}, "language": None,
                   "page_count": None, "volume_label": None,
                   "revision": 1, "supersedes_revision": None}
        with pytest.raises(LibrarianError) as rejected:
            with lib.transaction():
                lib._put({**edition, "id": "edition_foreign", "work_id": "work_foreign"})
        assert rejected.value.code == "VALIDATION_FAILED"
        lib.register("owner_a", edition)
        instance = {"object_type": "BookInstance", "schema_version": "0.1.0",
                    "id": "copy_valid", "owner_id": "owner_a",
                    "created_at": "2026-09-28T00:00:00+00:00",
                    "edition_id": edition["id"], "medium": "physical",
                    "acquired_at": {"value": None, "confidence": None, "basis": "unknown"},
                    "ownership_status": "unknown", "physical": {"qr_id": None, "shelf": None},
                    "reading_status": {"state": "unknown", "current_page": None,
                                       "progress_evidence_ref": None},
                    "revision": 1, "supersedes_revision": None}
        with pytest.raises(LibrarianError) as rejected:
            with lib.transaction():
                lib._put({**instance, "id": "copy_foreign", "edition_id": "edition_foreign"})
        assert rejected.value.code == "VALIDATION_FAILED"
        lib.register("owner_a", instance)
        session = lib.start_session("owner_a", instance["id"])
        forged = {**session, "id": "session_wrong_work", "work_id": "work_other"}
        with pytest.raises(LibrarianError) as rejected:
            with lib.transaction():
                lib._put(forged)
        assert rejected.value.code == "VALIDATION_FAILED"
        assert lib.db.execute("SELECT 1 FROM records WHERE id IN "
                              "('edition_foreign','copy_foreign','session_wrong_work')").fetchone() is None


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
        (tmp_path / a["asset"]["object_key"]).unlink()
        with pytest.raises(LibrarianError) as err:
            lib.ingest("owner_a", **args)
        assert err.value.code == "OBJECT_STORE_UNAVAILABLE"
        (tmp_path / a["asset"]["object_key"]).write_bytes(photo)
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


def test_corrupt_deduplicated_blob_cannot_be_accepted(tmp_path: Path):
    import hashlib
    photo = b"original photo"
    digest = hashlib.sha256(photo).hexdigest()
    target = tmp_path / "objects" / digest[:2] / digest
    target.parent.mkdir(parents=True)
    target.write_bytes(b"corrupt")
    with Library(tmp_path) as lib:
        with pytest.raises(LibrarianError) as err:
            lib.ingest("owner_a", transport="gateway", account_id="a",
                       conversation_id="c", source_event_id="m", idempotency_key="k",
                       attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                     "data": photo}])
        assert err.value.code == "OBJECT_STORE_UNAVAILABLE"
        assert lib.db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0


def test_object_write_failure_does_not_acknowledge_capture_and_retry_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import os

    args = dict(transport="gateway", account_id="a", conversation_id="c",
                source_event_id="m", idempotency_key="k",
                attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                              "data": b"photo bytes"}])
    real_replace = os.replace
    failed = False

    def fail_once(source, target):
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("object store unavailable")
        return real_replace(source, target)

    with Library(tmp_path) as lib:
        monkeypatch.setattr(os, "replace", fail_once)
        with pytest.raises(OSError, match="object store unavailable"):
            lib.ingest("owner_a", **args)
        assert lib.db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0
        assert lib.db.execute("SELECT COUNT(*) FROM idempotency").fetchone()[0] == 0
        assert lib.pending_events("owner_a") == []
        receipt = lib.ingest("owner_a", **args)
        assert lib.read_original("owner_a", receipt["capture_ids"][0]) == b"photo bytes"
        assert lib.ingest("owner_a", **args) == receipt


def test_session_selection_and_soft_affinity_stay_in_conversation_scope(tmp_path: Path):
    def accept(lib: Library, source: str, conversation: str = "c",
               context: dict | None = None) -> str:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id=conversation, source_event_id=source,
                             attachments=[{"source_item_id": "image", "mime_type": "image/jpeg",
                                           "data": b"photo"}], idempotency_key=source,
                             submitted_context=context)
        return receipt["capture_ids"][0]

    with Library(tmp_path) as lib:
        selected = lib.start_session("owner_a", scope=("gateway", "a", "c"))
        first = accept(lib, "m1")
        context = lib.db.execute("SELECT session_id,basis FROM capture_context WHERE capture_id=?",
                                 (first,)).fetchone()
        assert tuple(context) == (selected["id"], "active_session")
        assert lib.get("owner_a", "PageCapture", first)["submitted_context"]["session_id"] is None
        assert lib.db.execute("SELECT COUNT(*) FROM capture_context WHERE capture_id=?",
                              (accept(lib, "m2", "other-chat"),)).fetchone()[0] == 0

        # A per-message explicit context grants at most 90-minute affinity.
        soft = lib.start_session("owner_a")
        explicit = accept(lib, "m3", "affinity-chat", context={"session_id": soft["id"]})
        assert lib.db.execute("SELECT basis FROM capture_context WHERE capture_id=?",
                              (explicit,)).fetchone()[0] == "explicit_session"
        following = accept(lib, "m4", "affinity-chat")
        assert lib.db.execute("SELECT basis FROM capture_context WHERE capture_id=?",
                              (following,)).fetchone()[0] == "recent_affinity"
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        lib.db.execute("UPDATE session_scope SET last_assigned_at=? WHERE conversation_id='affinity-chat'", (old,))
        lib.db.commit()
        expired = accept(lib, "m5", "affinity-chat")
        assert lib.db.execute("SELECT COUNT(*) FROM capture_context WHERE capture_id=?",
                              (expired,)).fetchone()[0] == 0
        assert lib.get("owner_a", "ReadingSession", soft["id"])["status"] == "active"
