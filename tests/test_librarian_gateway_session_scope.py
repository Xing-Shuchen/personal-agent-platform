from __future__ import annotations

import pytest

from agents.librarian.runtime.gateway_session import session_inbound
from agents.librarian.runtime.store import Library, LibrarianError


def _message(conversation: str, event: str) -> dict:
    return {"owner_id": "owner_a", "actor_id": "sender_a", "action": "status",
            "source": {"transport": "telegram", "account_id": "account_a",
                       "conversation_id": conversation, "source_event_id": event}}


def test_session_command_uses_capture_scope_and_preserves_legacy_replay(tmp_path):
    with Library(tmp_path) as lib:
        session = lib.start_session("owner_a", scope=("telegram", "account_a", "agent:legacy"))
        old_message = _message("agent:legacy", "old-event")
        old_result = session_inbound(lib, old_message)
        replay = _message("chat_a", "old-event")
        replay["legacy_conversation_id"] = "agent:legacy"
        assert session_inbound(lib, replay) == old_result
        new_message = _message("chat_a", "new-event")
        new_message["legacy_conversation_id"] = "agent:legacy"
        assert session_inbound(lib, new_message)["session_id"] == session["id"]
        changed = {**replay, "action": "pause"}
        with pytest.raises(LibrarianError) as error:
            session_inbound(lib, changed)
        assert error.value.code == "IDEMPOTENCY_CONFLICT"


def test_legacy_selection_does_not_override_canonical_selection(tmp_path):
    with Library(tmp_path) as lib:
        lib.start_session("owner_a", scope=("telegram", "account_a", "agent:legacy"))
        canonical = lib.start_session("owner_a", scope=("telegram", "account_a", "chat_a"))
        message = _message("chat_a", "new-event")
        message["legacy_conversation_id"] = "agent:legacy"
        assert session_inbound(lib, message)["session_id"] == canonical["id"]
