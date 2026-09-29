import json
import hashlib

from agents.librarian.runtime.gateway_review import pending_extractions, worker_launch_status
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


def test_worker_launch_status_is_owner_scoped_and_does_not_claim_completion(tmp_path):
    folder = tmp_path / "worker-launch-status"
    folder.mkdir()
    for owner, mode, state in (("owner_a", "physical", "failed"),
                               ("owner_b", "physical", "spawned")):
        name = hashlib.sha256(json.dumps([owner, mode], separators=(",", ":")).encode()).hexdigest()
        (folder / f"{name}.json").write_text(json.dumps({
            "owner_id": owner, "mode": mode, "state": state,
            "code": "WORKER_SPAWN_FAILED" if state == "failed" else None,
            "updated_at": "2026-09-29T00:00:00Z"}))
    assert worker_launch_status(tmp_path, "owner_a") == [{
        "mode": "physical", "state": "failed", "code": "WORKER_SPAWN_FAILED",
        "updated_at": "2026-09-29T00:00:00Z"}]
    with Library(tmp_path) as lib:
        result = pending_extractions(lib, "owner_b")
        assert result["worker_launch_status"] == [{
            "mode": "physical", "state": "spawned", "code": None,
            "updated_at": "2026-09-29T00:00:00Z"}]
