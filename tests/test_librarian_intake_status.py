import json

from agents.librarian.runtime.gateway_review import pending_extractions
from agents.librarian.runtime.store import Library


def test_pending_review_lists_only_owner_hook_failures(tmp_path):
    folder = tmp_path / "intake-status"
    folder.mkdir()
    def status(name, owner, state):
        (folder / (name * 64 + ".json")).write_text(json.dumps({
            "owner_id": owner, "channel_id": "feishu", "account_id": "librarian",
            "message_id": f"message-{name}", "state": state,
            "code": "BRIDGE_FAILED", "stage": "gateway.intake",
            "retryable": True, "updated_at": "2026-09-29T00:00:00Z"}))
    status("a", "owner_a", "failed")
    status("b", "owner_b", "failed")
    status("c", "owner_a", "accepted")
    with Library(tmp_path) as lib:
        result = pending_extractions(lib, "owner_a")
        assert result["pending"] == []
        assert len(result["intake_failures"]) == 1
        assert result["intake_failures"][0]["message_id"] == "message-a"
        assert pending_extractions(lib, "owner_b")["intake_failures"][0]["message_id"] == "message-b"
