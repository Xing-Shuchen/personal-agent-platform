"""Trusted inbound session actions use the domain command path."""
import json
from pathlib import Path

import pytest

from agents.librarian.runtime.gateway_session import session_inbound
from agents.librarian.runtime.store import Library, LibrarianError


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "positive.json"


def _message(event: str, action: str, **params) -> dict:
    return {"owner_id": "owner_fixture", "actor_id": "person",
            "source": {"transport": "feishu", "account_id": "librarian",
                       "conversation_id": "chat_fixture", "source_event_id": event},
            "action": action, **params}


@pytest.fixture
def lib(tmp_path):
    cases = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    with Library(tmp_path) as library:
        for model in ("Work", "Edition", "BookInstance"):
            library.register("owner_fixture", next(case["value"] for case in cases
                                                   if case["id"] == f"model-{model}"))
        yield library


def test_session_lifecycle_and_message_retry(lib):
    start = _message("msg-1", "start", book="Synthetic Work")
    result = session_inbound(lib, start)
    assert result["status"] == "active"
    assert session_inbound(lib, start) == result
    assert session_inbound(lib, _message("msg-2", "start", book="Synthetic Work"))["status"] == "unchanged"
    page = session_inbound(lib, _message("msg-3", "progress", page=39))
    assert page["progress"]["end_page"]["number"] == 39
    assert page["progress"]["basis"] == "user_statement"
    assert lib.get("owner_fixture", "BookInstance", "bookinst_fixture")["reading_status"]["current_page"]["number"] == 39
    assert session_inbound(lib, _message("msg-4", "pause"))["status"] == "paused"
    resumed = session_inbound(lib, _message("msg-5", "start", book="Synthetic Work"))
    assert resumed["status"] == "active"
    assert resumed["session_id"] == result["session_id"]
    assert session_inbound(lib, _message("msg-6", "close"))["status"] == "closed"
    fresh = session_inbound(lib, _message("msg-7", "start", book="Synthetic Work"))
    assert fresh["session_id"] != result["session_id"]


def test_identity_ambiguity_and_conflicting_retry(lib):
    session_inbound(lib, _message("msg-1", "start", book="Synthetic Work"))
    with pytest.raises(LibrarianError, match="source message changed"):
        session_inbound(lib, _message("msg-1", "progress", page=42))
    with pytest.raises(LibrarianError, match="exactly one physical copy"):
        session_inbound(lib, _message("msg-2", "start", book="Missing"))
    with pytest.raises(LibrarianError, match="selected|select one"):
        session_inbound(lib, {**_message("msg-3", "progress", page=1),
                              "source": {**_message("msg-3", "progress")["source"],
                                         "conversation_id": "another-chat"}})
    with pytest.raises(LibrarianError):
        session_inbound(lib, {**_message("msg-4", "start", book="Synthetic Work"),
                              "owner_id": "another_owner"})
