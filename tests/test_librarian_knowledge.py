from __future__ import annotations

import copy

import pytest

from agents.librarian.runtime.commands import execute_command
from agents.librarian.runtime.digital import ingest_export
from agents.librarian.runtime.knowledge import create_candidate, decide_candidate, promote_candidate
from agents.librarian.runtime.pipeline import correct_trace
from agents.librarian.runtime.store import Library, LibrarianError


EXPORT = """---
bookId: "synthetic-knowledge"
---
> [!abstract] Synthetic Knowledge Book
# 高亮划线
## Chapter
> 📌 An ordinary highlight
> ⏱ 2024-01-01 12:00:00 ^synthetic-knowledge-1
""".encode()


def _command(name: str, payload: dict, key: str) -> dict:
    return {"command": name, "version": 1, "command_id": f"cmd_{key}",
            "owner_id": "owner_a", "issued_at": "2026-09-28T00:00:00+00:00",
            "idempotency_key": key, "actor": {"type": "user", "id": "actor_a"},
            "payload": payload}


def test_candidate_requires_explicit_trigger_and_promotion_confirms_external_write(tmp_path):
    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "synthetic.md", EXPORT)[0]
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='KnowledgeCandidate'").fetchone()[0] == 0
        source = [{"trace_id": trace["id"], "revision": trace["revision"]}]
        candidate = create_candidate(lib, "owner_a", source, candidate_type="question",
                                     content={"text": "Synthetic question", "confidence": None,
                                              "basis": "model_inference"},
                                     correlation_id="explicit-review")
        with pytest.raises(LibrarianError) as wrong_owner:
            create_candidate(lib, "owner_b", source, candidate_type="question",
                             content={"text": None, "confidence": None, "basis": "unknown"},
                             correlation_id="wrong-owner")
        assert wrong_owner.value.code == "UNAUTHORIZED"
        approved_receipt = execute_command(lib,
            _command("reading.knowledge_candidate.approve",
                     {"candidate_id": candidate["id"], "expected_revision": 1}, "approve-1"),
            trusted_owner_id="owner_a", trusted_actor_id="actor_a")
        assert approved_receipt["object_id"] == candidate["id"]
        approved = lib.get("owner_a", "KnowledgeCandidate", candidate["id"])
        assert approved["status"] == "approved" and approved["revision"] == 2
        def fail(_candidate, _key):
            raise RuntimeError("knowledge service unavailable")
        with pytest.raises(RuntimeError, match="unavailable"):
            promote_candidate(lib, "owner_a", candidate["id"], 2, fail)
        assert lib.get("owner_a", "KnowledgeCandidate", candidate["id"])["status"] == "approved"
        assert not any(event["event"] == "reading.knowledge.promoted"
                       for event in lib.pending_events("owner_a"))
        calls = []
        def write(record, key):
            calls.append((record["id"], key))
            return "knowledge_fixture"
        promoted = promote_candidate(lib, "owner_a", candidate["id"], 2, write)
        assert promoted["status"] == "promoted"
        assert promoted["knowledge_id"] == "knowledge_fixture"
        assert promote_candidate(lib, "owner_a", candidate["id"], 2, write) == promoted
        assert len(calls) == 1
        events = [event for event in lib.pending_events("owner_a")
                  if event["event"] == "reading.knowledge.promoted"]
        assert len(events) == 1
        assert events[0]["payload"]["knowledge_id"] == "knowledge_fixture"


def test_storage_rejects_candidate_reference_to_other_owner(tmp_path):
    with Library(tmp_path) as lib:
        own = ingest_export(lib, "owner_a", "weread", "own.md", EXPORT)[0]
        foreign = ingest_export(lib, "owner_b", "weread", "foreign.md", EXPORT)[0]
        candidate = create_candidate(
            lib, "owner_a", [{"trace_id": own["id"], "revision": 1}],
            candidate_type="concept",
            content={"text": None, "confidence": None, "basis": "unknown"},
            correlation_id="fixture")
        forged = {**candidate, "id": "candidate_wrong_owner",
                  "source_trace_refs": [{"trace_id": foreign["id"], "revision": 1}]}
        with pytest.raises(LibrarianError) as rejected:
            with lib.transaction():
                lib._put(forged)
        assert rejected.value.code == "VALIDATION_FAILED"
        assert lib.db.execute("SELECT 1 FROM records WHERE id=?",
                              (forged["id"],)).fetchone() is None


def test_storage_enforces_candidate_state_machine_and_immutable_interpretation(tmp_path):
    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "synthetic.md", EXPORT)[0]
        candidate = create_candidate(lib, "owner_a",
            [{"trace_id": trace["id"], "revision": 1}], candidate_type="concept",
            content={"text": None, "confidence": None, "basis": "unknown"},
            correlation_id="state-test")
        initial_promotion = {**candidate, "id": "candidate_skipped", "status": "promoted",
                             "knowledge_id": "knowledge_fake"}
        with pytest.raises(LibrarianError) as skipped:
            with lib.transaction():
                lib._put(initial_promotion)
        assert skipped.value.code == "INVALID_STATE_TRANSITION"

        forged = {**candidate, "revision": 2, "supersedes_revision": 1,
                  "status": "promoted", "knowledge_id": "knowledge_fake"}
        with pytest.raises(LibrarianError) as skipped:
            with lib.transaction():
                lib._put(forged)
        assert skipped.value.code == "INVALID_STATE_TRANSITION"

        changed = copy.deepcopy(candidate)
        changed.update(revision=2, supersedes_revision=1, status="approved")
        changed["content"] = {"text": "Different claim", "confidence": None,
                              "basis": "user_statement"}
        with pytest.raises(LibrarianError) as altered:
            with lib.transaction():
                lib._put(changed)
        assert altered.value.code == "VALIDATION_FAILED"
        assert lib.get("owner_a", "KnowledgeCandidate", candidate["id"])["revision"] == 1

        legacy = {**candidate, "id": "candidate_legacy"}
        legacy.pop("trigger")
        with lib.transaction():
            lib._put(legacy)
        assert decide_candidate(lib, "owner_a", legacy["id"], 1, approve=True)["status"] == "approved"


def test_rejection_reason_and_changed_trace_prevent_stale_approval(tmp_path):
    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "synthetic.md", EXPORT)[0]
        source = [{"trace_id": trace["id"], "revision": 1}]
        rejected_candidate = create_candidate(lib, "owner_a", source,
            candidate_type="concept",
            content={"text": None, "confidence": None, "basis": "unknown"},
            correlation_id="explicit-review-1")
        execute_command(lib,
            _command("reading.knowledge_candidate.reject",
                     {"candidate_id": rejected_candidate["id"], "expected_revision": 1,
                      "reason": "Not my note"}, "reject-1"),
            trusted_owner_id="owner_a", trusted_actor_id="actor_a")
        rejected = lib.get("owner_a", "KnowledgeCandidate", rejected_candidate["id"])
        assert rejected["status"] == "rejected"
        assert rejected["decision_reason"] == "Not my note"
        with pytest.raises(LibrarianError) as terminal:
            promote_candidate(lib, "owner_a", rejected_candidate["id"], 2,
                              lambda _record, _key: "should_not_write")
        assert terminal.value.code == "INVALID_STATE_TRANSITION"

        stale = create_candidate(lib, "owner_a", source, candidate_type="question",
            content={"text": None, "confidence": None, "basis": "unknown"},
            correlation_id="explicit-review-2")
        correct_trace(lib, "owner_a", trace["id"], 1,
                      annotation="Corrected note", reason="user correction")
        with pytest.raises(LibrarianError) as changed:
            execute_command(lib,
                _command("reading.knowledge_candidate.approve",
                         {"candidate_id": stale["id"], "expected_revision": 1}, "approve-stale"),
                trusted_owner_id="owner_a", trusted_actor_id="actor_a")
        assert changed.value.code == "REVISION_CONFLICT"
        assert lib.get("owner_a", "KnowledgeCandidate", stale["id"])["status"] == "superseded"


def test_source_correction_during_external_write_does_not_publish_promotion(tmp_path):
    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "synthetic.md", EXPORT)[0]
        candidate = create_candidate(lib, "owner_a",
            [{"trace_id": trace["id"], "revision": 1}], candidate_type="concept",
            content={"text": None, "confidence": None, "basis": "unknown"},
            correlation_id="explicit-review")
        decide = execute_command(lib,
            _command("reading.knowledge_candidate.approve",
                     {"candidate_id": candidate["id"], "expected_revision": 1}, "approve-race"),
            trusted_owner_id="owner_a", trusted_actor_id="actor_a")
        assert decide["status"] == "completed"

        def write(_record, _key):
            correct_trace(lib, "owner_a", trace["id"], 1,
                          annotation="Changed during write", reason="user correction")
            return "knowledge_fixture"

        with pytest.raises(LibrarianError) as stale:
            promote_candidate(lib, "owner_a", candidate["id"], 2, write)
        assert stale.value.code == "REVISION_CONFLICT"
        assert lib.get("owner_a", "KnowledgeCandidate", candidate["id"])["status"] == "approved"
        assert not any(event["event"] == "reading.knowledge.promoted"
                       for event in lib.pending_events("owner_a"))


def test_promotion_event_failure_rolls_back_candidate_and_retries_same_key(tmp_path, monkeypatch):
    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "synthetic.md", EXPORT)[0]
        candidate = create_candidate(lib, "owner_a",
            [{"trace_id": trace["id"], "revision": 1}], candidate_type="concept",
            content={"text": None, "confidence": None, "basis": "unknown"},
            correlation_id="explicit-review")
        execute_command(lib,
            _command("reading.knowledge_candidate.approve",
                     {"candidate_id": candidate["id"], "expected_revision": 1}, "approve-event"),
            trusted_owner_id="owner_a", trusted_actor_id="actor_a")

        keys = []
        def write(_record, key):
            keys.append(key)
            return "knowledge_fixture"

        original_event = lib._event
        def fail_event(*_args, **_kwargs):
            raise RuntimeError("outbox unavailable")
        monkeypatch.setattr(lib, "_event", fail_event)
        with pytest.raises(RuntimeError, match="outbox unavailable"):
            promote_candidate(lib, "owner_a", candidate["id"], 2, write)
        assert lib.get("owner_a", "KnowledgeCandidate", candidate["id"])["status"] == "approved"
        assert not any(event["event"] == "reading.knowledge.promoted"
                       for event in lib.pending_events("owner_a"))

        monkeypatch.setattr(lib, "_event", original_event)
        promoted = promote_candidate(lib, "owner_a", candidate["id"], 2, write)
        assert promoted["status"] == "promoted"
        assert len(keys) == 2 and keys[0] == keys[1]
        events = [event for event in lib.pending_events("owner_a")
                  if event["event"] == "reading.knowledge.promoted"]
        assert len(events) == 1
