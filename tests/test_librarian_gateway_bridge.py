from __future__ import annotations

import base64
import io
import json
import subprocess
import sys

import pytest
from PIL import Image

from agents.librarian.runtime.gateway_bridge import accept_inbound
from agents.librarian.runtime.store import Library, LibrarianError


def _image() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(stream, format="PNG")
    return stream.getvalue()


def _message(image: bytes) -> dict:
    return {"owner_id": "owner_a", "actor_id": "sender_a",
            "source": {"transport": "telegram", "account_id": "account_a",
                       "conversation_id": "chat_a", "source_event_id": "message_a"},
            "attachments": [{"source_item_id": "message_a:0", "mime_type": "image/png",
                             "data_b64": base64.b64encode(image).decode()}]}


def test_gateway_bridge_accepts_staged_bytes_and_retries_by_source_identity(tmp_path):
    image = _image()
    with Library(tmp_path) as lib:
        first = accept_inbound(lib, _message(image))
        capture_id = first["capture_ids"][0]
        assert lib.read_original("owner_a", capture_id) == image
        assert accept_inbound(lib, _message(image)) == first
        assert len(lib.pending_events("owner_a")) == 1
        altered = _message(image + b"different bytes")
        with pytest.raises(LibrarianError) as error:
            accept_inbound(lib, altered)
        assert error.value.code == "IDEMPOTENCY_CONFLICT"
        assert lib.read_original("owner_a", capture_id) == image
        another = _message(image)
        another["source"]["source_event_id"] = "message_b"
        another["attachments"][0]["source_item_id"] = "message_b:0"
        second = accept_inbound(lib, another)
        assert second["capture_ids"] != first["capture_ids"]
        assert lib.get("owner_a", "PageCapture", second["capture_ids"][0])["asset"] == (
            lib.get("owner_a", "PageCapture", capture_id)["asset"])


def test_gateway_bridge_rejects_missing_source_identity_and_bad_image_payload(tmp_path):
    with Library(tmp_path) as lib:
        missing = _message(_image())
        missing["source"]["source_event_id"] = ""
        with pytest.raises(LibrarianError, match="stable source identity"):
            accept_inbound(lib, missing)
        bad = _message(_image())
        bad["attachments"][0]["data_b64"] = "not base64"
        with pytest.raises(LibrarianError, match="encoding"):
            accept_inbound(lib, bad)
        assert lib.db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0


def test_gateway_bridge_module_accepts_json_from_stdin(tmp_path):
    result = subprocess.run([sys.executable, "-m", "agents.librarian.runtime.gateway_bridge",
                             "--root", str(tmp_path)],
                            input=json.dumps(_message(_image())).encode(),
                            capture_output=True, check=True)
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "accepted"
    with Library(tmp_path) as lib:
        assert lib.read_original("owner_a", receipt["capture_ids"][0]) == _image()


def test_gateway_bridge_accepts_staged_paths_as_one_replayable_batch(tmp_path):
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    first_path.write_bytes(_image())
    second_path.write_bytes(_image() + b"second")
    message = _message(_image())
    message["attachments"] = [
        {"source_item_id": "message_a:0", "mime_type": "image/png",
         "data_path": str(first_path)},
        {"source_item_id": "message_a:1", "mime_type": "image/png",
         "data_path": str(second_path)},
    ]
    with Library(tmp_path / "library") as lib:
        receipt = accept_inbound(lib, message)
        assert len(receipt["capture_ids"]) == 2
        assert lib.read_original("owner_a", receipt["capture_ids"][0]) == first_path.read_bytes()
        assert lib.read_original("owner_a", receipt["capture_ids"][1]) == second_path.read_bytes()
        assert accept_inbound(lib, message) == receipt
        second_path.write_bytes(_image() + b"changed")
        with pytest.raises(LibrarianError) as error:
            accept_inbound(lib, message)
        assert error.value.code == "IDEMPOTENCY_CONFLICT"


def test_gateway_bridge_adopts_trusted_legacy_selection_for_future_images(tmp_path):
    image = _image()
    with Library(tmp_path) as lib:
        session = lib.start_session("owner_a", scope=("telegram", "account_a", "agent:legacy"))
        message = _message(image)
        message["legacy_conversation_id"] = "agent:legacy"
        first = accept_inbound(lib, message)
        capture_id = first["capture_ids"][0]
        context = lib.db.execute(
            "SELECT session_id,basis FROM capture_context WHERE owner_id=? AND capture_id=?",
            ("owner_a", capture_id)).fetchone()
        assert tuple(context) == (session["id"], "active_session")
        selected = lib.db.execute(
            "SELECT session_id FROM session_scope WHERE owner_id=? AND transport=? "
            "AND account_id=? AND conversation_id=? AND selected=1",
            ("owner_a", "telegram", "account_a", "chat_a")).fetchone()
        assert selected["session_id"] == session["id"]
        assert accept_inbound(lib, message) == first
        changed = _message(image + b"changed")
        changed["legacy_conversation_id"] = "agent:legacy"
        with pytest.raises(LibrarianError) as error:
            accept_inbound(lib, changed)
        assert error.value.code == "IDEMPOTENCY_CONFLICT"


def test_gateway_bridge_rejects_same_source_when_conversation_scope_changes(tmp_path):
    with Library(tmp_path) as lib:
        message = _message(_image())
        accept_inbound(lib, message)
        replay = _message(_image())
        replay["source"]["conversation_id"] = "agent:legacy"
        replay["attachments"][0]["source_item_id"] = "message_a:renumbered"
        with pytest.raises(LibrarianError) as error:
            accept_inbound(lib, replay)
        assert error.value.code == "IDEMPOTENCY_CONFLICT"
