"""Versioned human decisions for Bookscan handwritten margin notes."""
from __future__ import annotations

import json
from typing import Any

from .knowledge import supersede_pending_for_trace
from .pipeline import _repair_trace_index_best_effort
from .store import Library, LibrarianError, _json, _now, validate


ACCEPTED = "handwriting confirmed by user"
REJECTED = "handwriting rejected by user"


def _note_detection(trace: dict[str, Any]) -> str:
    ids = trace.get("source", {}).get("detection_ids", [])
    if (trace.get("medium") != "physical" or
            "margin_note" not in trace.get("trace_types", []) or
            len(ids) != 1 or not ids[0].startswith("bookscan_note_") or
            not ids[0][len("bookscan_note_"):].isdigit()):
        raise LibrarianError("VALIDATION_FAILED", "trace is not a Bookscan handwritten note")
    return ids[0]


def review_handwriting(lib: Library, owner: str, decision: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise LibrarianError("VALIDATION_FAILED", "handwriting decision must be an object")
    trace_id = decision.get("trace_id")
    revision = decision.get("expected_revision")
    verdict = decision.get("decision")
    text = decision.get("text", "")
    if (not isinstance(trace_id, str) or not trace_id or type(revision) is not int or
            revision < 1 or verdict not in {"accepted", "rejected"} or
            not isinstance(text, str) or len(text) > 4000 or
            (verdict == "accepted" and not text.strip()) or
            (verdict == "rejected" and text.strip())):
        raise LibrarianError("VALIDATION_FAILED", "invalid handwriting decision")
    with lib.transaction():
        prior = lib.get(owner, "ReadingTrace", trace_id)
        _note_detection(prior)
        if prior["revision"] != revision:
            if (prior["revision"] == revision + 1 and
                    prior["supersedes_revision"] == revision and
                    prior["review"]["reason"] == (ACCEPTED if verdict == "accepted" else REJECTED) and
                    (verdict == "rejected" or
                     prior["content"]["annotation"]["text"] == text.strip())):
                return {"status": "already_applied", "trace_id": trace_id,
                        "revision": prior["revision"]}
            raise LibrarianError("REVISION_CONFLICT", "handwriting trace revision changed")
        if (prior["status"] not in {"active", "superseded"} or
                (prior["status"] == "superseded" and prior["review"]["reason"] != REJECTED)):
            raise LibrarianError("INVALID_STATE_TRANSITION", "handwriting note cannot be reviewed")
        if ((verdict == "accepted" and prior["status"] == "active" and
             prior["review"]["reason"] == ACCEPTED and
             prior["content"]["annotation"]["text"] == text.strip()) or
            (verdict == "rejected" and prior["status"] == "superseded" and
             prior["review"]["reason"] == REJECTED)):
            return {"status": "already_applied", "trace_id": trace_id,
                    "revision": prior["revision"]}
        source_ref = (trace_id, revision)
        for row in lib.db.execute(
                "SELECT body FROM records WHERE owner_id=? AND model='KnowledgeCandidate' AND current=1",
                (owner,)):
            candidate = json.loads(row["body"])
            if (candidate["status"] == "promoted" and
                    any((ref["trace_id"], ref["revision"]) == source_ref
                        for ref in candidate["source_trace_refs"])):
                raise LibrarianError("RECONCILIATION_REQUIRED", "knowledge depends on this note")
        revised = json.loads(_json(prior))
        revised.update({"revision": revision + 1, "supersedes_revision": revision,
                        "created_at": _now()})
        revised["review"] = {"required": False, "state": "resolved",
                             "reason": ACCEPTED if verdict == "accepted" else REJECTED}
        if verdict == "accepted":
            revised["status"] = "active"
            revised["content"]["annotation"] = {
                "text": text.strip(), "confidence": None, "basis": "user_statement"}
        else:
            revised["status"] = "superseded"
        validate("ReadingTrace", revised)
        lib._put(revised)
        supersede_pending_for_trace(lib, owner, prior, revised)
        lib._event(owner, "reading.trace.corrected", "reading_trace", trace_id,
                   revised["revision"], {"trace_id": trace_id,
                   "previous_revision": revision, "revision": revised["revision"],
                   "reason": revised["review"]["reason"]}, trace_id)
    _repair_trace_index_best_effort(lib, owner)
    return {"status": "applied", "trace_id": trace_id, "revision": revised["revision"]}
