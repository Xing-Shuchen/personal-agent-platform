"""Explicit, provenance-bound candidate lifecycle; no automatic knowledge write."""
from __future__ import annotations

from typing import Any, Callable

from .store import Library, LibrarianError, _new, _now, validate


def create_candidate(lib: Library, owner_id: str,
                     source_trace_refs: list[dict[str, Any]], *,
                     candidate_type: str, content: dict[str, Any],
                     correlation_id: str) -> dict[str, Any]:
    """Create a candidate only when an explicit caller or enabled signal asks."""
    if not source_trace_refs or not correlation_id:
        raise LibrarianError("VALIDATION_FAILED", "candidate needs sources and correlation")
    for ref in source_trace_refs:
        trace = lib.get(owner_id, "ReadingTrace", ref["trace_id"])
        if trace["revision"] != ref["revision"] or trace["status"] != "active":
            raise LibrarianError("REVISION_CONFLICT", "candidate source is not current")
    record = {"object_type": "KnowledgeCandidate", "schema_version": "0.1.0",
              "id": _new("candidate"), "owner_id": owner_id, "created_at": _now(),
              "revision": 1, "supersedes_revision": None,
              "source_trace_refs": source_trace_refs, "candidate_type": candidate_type,
              "content": content, "status": "pending", "knowledge_id": None,
              "decision_reason": None}
    validate("KnowledgeCandidate", record)
    with lib.transaction():
        lib._put(record)
        lib._event(owner_id, "reading.knowledge_candidate.created", "knowledge_candidate",
                   record["id"], 1,
                   {"candidate_id": record["id"], "revision": 1,
                    "source_trace_refs": source_trace_refs}, correlation_id)
    return record


def decide_candidate(lib: Library, owner_id: str, candidate_id: str,
                     expected_revision: int, *, approve: bool,
                     reason: str | None = None) -> dict[str, Any]:
    with lib.transaction():
        current = lib.get(owner_id, "KnowledgeCandidate", candidate_id)
        if current["revision"] != expected_revision:
            raise LibrarianError("REVISION_CONFLICT", "candidate revision changed")
        if current["status"] != "pending":
            raise LibrarianError("INVALID_STATE_TRANSITION", "candidate is not pending")
        if not approve and (not isinstance(reason, str) or not reason.strip()):
            raise LibrarianError("VALIDATION_FAILED", "rejection reason required")
        if approve:
            for ref in current["source_trace_refs"]:
                trace = lib.get(owner_id, "ReadingTrace", ref["trace_id"])
                if trace["revision"] != ref["revision"] or trace["status"] != "active":
                    raise LibrarianError("REVISION_CONFLICT", "candidate source changed")
        record = {**current, "revision": expected_revision + 1,
                  "supersedes_revision": expected_revision,
                  "created_at": _now(), "status": "approved" if approve else "rejected",
                  "decision_reason": None if approve else reason.strip()}
        lib._put(record)
        return record


def promote_candidate(lib: Library, owner_id: str, candidate_id: str,
                      expected_revision: int,
                      write_knowledge: Callable[[dict[str, Any], str], str]) -> dict[str, Any]:
    """Advance only after an external idempotent knowledge port confirms write.

    The port must use the supplied stable key for replay safety. It returns a
    persisted knowledge ID; an exception leaves the candidate approved.
    """
    current = lib.get(owner_id, "KnowledgeCandidate", candidate_id)
    if (current["status"] == "promoted" and current["revision"] == expected_revision + 1
            and current["supersedes_revision"] == expected_revision):
        return current
    if current["revision"] != expected_revision:
        raise LibrarianError("REVISION_CONFLICT", "candidate revision changed")
    if current["status"] != "approved":
        raise LibrarianError("INVALID_STATE_TRANSITION", "candidate is not approved")
    for ref in current["source_trace_refs"]:
        trace = lib.get(owner_id, "ReadingTrace", ref["trace_id"])
        if trace["revision"] != ref["revision"] or trace["status"] != "active":
            raise LibrarianError("REVISION_CONFLICT", "candidate source changed")
    knowledge_id = write_knowledge(current, f"librarian:{owner_id}:{candidate_id}:{expected_revision}")
    if not isinstance(knowledge_id, str) or not knowledge_id:
        raise LibrarianError("VALIDATION_FAILED", "knowledge port did not confirm persistence")
    with lib.transaction():
        latest = lib.get(owner_id, "KnowledgeCandidate", candidate_id)
        if latest["revision"] != expected_revision or latest["status"] != "approved":
            raise LibrarianError("REVISION_CONFLICT", "candidate changed during knowledge write")
        for ref in latest["source_trace_refs"]:
            trace = lib.get(owner_id, "ReadingTrace", ref["trace_id"])
            if trace["revision"] != ref["revision"] or trace["status"] != "active":
                raise LibrarianError("REVISION_CONFLICT", "candidate source changed during knowledge write")
        record = {**latest, "revision": expected_revision + 1,
                  "supersedes_revision": expected_revision,
                  "created_at": _now(), "status": "promoted",
                  "knowledge_id": knowledge_id}
        lib._put(record)
        lib._event(owner_id, "reading.knowledge.promoted", "knowledge_candidate",
                   candidate_id, record["revision"],
                   {"candidate_id": candidate_id, "revision": record["revision"],
                    "knowledge_id": knowledge_id,
                    "source_trace_refs": record["source_trace_refs"]}, candidate_id)
        return record
