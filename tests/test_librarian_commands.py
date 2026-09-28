from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.librarian.runtime import commands
from agents.librarian.runtime.store import Library, LibrarianError


def envelope(name: str, payload: dict, *, key: str = "key-1",
             command_id: str = "command-1", owner: str = "owner_a") -> dict:
    return {"command": name, "version": 1, "command_id": command_id,
            "owner_id": owner, "issued_at": "2026-09-28T00:00:00+00:00",
            "idempotency_key": key, "actor": {"type": "user", "id": "user_a"},
            "payload": payload}


def work() -> dict:
    return {"object_type": "Work", "schema_version": "0.1.0",
            "id": "work_one", "owner_id": "owner_a",
            "created_at": "2026-09-28T00:00:00+00:00",
            "title": "Synthetic book", "original_title": None,
            "authors": [], "identifiers": [], "revision": 1,
            "supersedes_revision": None}


def execute(lib: Library, command: dict, **kwargs) -> dict:
    return commands.execute_command(lib, command, trusted_owner_id="owner_a",
                                    trusted_actor_id="user_a", **kwargs)


def test_command_key_ignores_tracking_fields_but_rejects_business_change(tmp_path: Path):
    with Library(tmp_path) as lib:
        command = envelope("catalog.register_work", {"record": work()})
        receipt = execute(lib, command)
        assert receipt["object_id"] == "work_one"
        retry = command | {"command_id": "command-retry",
                           "issued_at": "2026-09-29T00:00:00+00:00"}
        assert execute(lib, retry) == receipt
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='Work'").fetchone()[0] == 1
        changed = envelope("catalog.register_work", {"record": work() | {"title": "Changed"}})
        with pytest.raises(LibrarianError) as error:
            execute(lib, changed)
        assert error.value.code == "IDEMPOTENCY_CONFLICT"
        with pytest.raises(LibrarianError) as error:
            execute(lib, command | {"owner_id": "owner_b"})
        assert error.value.code == "UNAUTHORIZED"
        with pytest.raises(LibrarianError) as error:
            execute(lib, envelope("catalog.register_edition", {"record": work()}, key="wrong-model"))
        assert error.value.code == "VALIDATION_FAILED"
        secret = "private reading note text"
        with pytest.raises(LibrarianError) as error:
            execute(lib, envelope("catalog.register_work",
                                  {"record": work() | {"unexpected": secret}}, key="invalid-extra"))
        assert secret not in str(error.value)


def test_session_and_capture_receipts_are_atomic_and_replayable(tmp_path: Path):
    with Library(tmp_path) as lib:
        start = envelope("reading.session.start", {"book_instance_id": None}, key="session-key")
        session_receipt = execute(lib, start)
        assert execute(lib, start | {"command_id": "retry"}) == session_receipt
        session_id = session_receipt["object_id"]
        assert lib.get("owner_a", "ReadingSession", session_id)["revision"] == 1
        source = {"transport": "gateway", "account_id": "a",
                  "conversation_id": "c", "source_event_id": "message-1"}
        payload = {"source": source, "submitted_context": {"session_id": session_id},
                   "attachments": [{"source_item_id": "photo-1", "mime_type": "image/png",
                                    "upload_ref": "upload-1"}]}
        command = envelope("reading.capture.ingest", payload, key="capture-key")
        accepted = execute(lib, command, resolve_upload=lambda ref: b"stored bytes")
        assert accepted["status"] == "accepted"
        assert len(accepted["capture_ids"]) == 1
        assert execute(lib, command | {"command_id": "retry"},
                       resolve_upload=lambda ref: b"stored bytes") == accepted
        with pytest.raises(LibrarianError) as error:
            execute(lib, command | {"command_id": "retry"},
                    resolve_upload=lambda ref: b"different bytes")
        assert error.value.code == "IDEMPOTENCY_CONFLICT"
        assert lib.read_original("owner_a", accepted["capture_ids"][0]) == b"stored bytes"
        resolve = envelope("reading.capture.resolve",
                           {"capture_id": accepted["capture_ids"][0],
                            "expected_resolution_revision": None,
                            "session_id": session_id}, key="resolve-key")
        resolved = execute(lib, resolve)
        assert execute(lib, resolve | {"command_id": "resolve-retry"}) == resolved
        assert lib.get("owner_a", "CaptureResolution", resolved["object_id"])["session"]["value"] == session_id
        assert [e["event"] for e in lib.pending_events("owner_a")] == [
            "reading.session.started", "reading.capture.received"]


def test_receipt_failure_rolls_back_domain_record_and_event(tmp_path: Path, monkeypatch):
    with Library(tmp_path) as lib:
        def fail(*args):
            raise RuntimeError("receipt write failed")
        monkeypatch.setattr(commands, "_store_receipt", fail)
        with pytest.raises(RuntimeError, match="receipt write failed"):
            execute(lib, envelope("reading.session.start", {"book_instance_id": None}))
        assert lib.db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0
        assert lib.pending_events("owner_a") == []
