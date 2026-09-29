"""Record authenticated, source-linked decisions on pending scan candidates.

This is a review ledger, not trace promotion. A later reconciliation must use
the decisions for the exact ProcessingRun and retain all earlier evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .gateway_review import pending_extractions
from .store import Library, LibrarianError, _now
from .gateway_errors import write_error

MAX_INPUT_BYTES = 8192


def record_review_decision(lib: Library, message: dict) -> dict:
    owner, actor, source = (message.get(key) for key in
                            ("owner_id", "actor_id", "source"))
    capture_id, run_id, selected = (message.get(key) for key in
                                    ("capture_id", "pending_run_id", "candidate_id"))
    decision, corrected_text = message.get("decision"), message.get("corrected_text")
    if (not all(isinstance(value, str) and value for value in
                (owner, actor, capture_id, run_id, selected)) or
            decision not in {"accept", "reject"} or not isinstance(source, dict)):
        raise LibrarianError("VALIDATION_FAILED", "review identity and decision required")
    keys = ("transport", "account_id", "conversation_id", "source_event_id")
    if any(not isinstance(source.get(key), str) or not source[key] for key in keys):
        raise LibrarianError("VALIDATION_FAILED", "trusted inbound source required")
    if (corrected_text is not None and
            (decision != "accept" or not isinstance(corrected_text, str) or
             not corrected_text.strip() or len(corrected_text) > 2000)):
        raise LibrarianError("VALIDATION_FAILED", "corrected text only applies to acceptance")
    source_key = hashlib.sha256(json.dumps(
        [owner, actor, *[source[key] for key in keys], selected],
        ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    payload = {"owner_id": owner, "capture_id": capture_id,
               "pending_run_id": run_id, "candidate_id": selected,
               "decision": decision, "corrected_text": corrected_text}
    fingerprint = hashlib.sha256(json.dumps(payload, ensure_ascii=False,
                                             sort_keys=True).encode()).hexdigest()
    lib.db.execute("CREATE TABLE IF NOT EXISTS gateway_review_decisions ("
                   "owner_id TEXT NOT NULL, source_key TEXT NOT NULL, "
                   "fingerprint TEXT NOT NULL, capture_id TEXT NOT NULL, "
                   "pending_run_id TEXT NOT NULL, candidate_id TEXT NOT NULL, "
                   "decision TEXT NOT NULL, corrected_text TEXT, actor_id TEXT NOT NULL, "
                   "source_event_id TEXT NOT NULL, created_at TEXT NOT NULL, "
                   "PRIMARY KEY(owner_id,source_key))")
    with lib.transaction():
        previous = lib.db.execute("SELECT fingerprint FROM gateway_review_decisions "
                                  "WHERE owner_id=? AND source_key=?",
                                  (owner, source_key)).fetchone()
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise LibrarianError("IDEMPOTENCY_CONFLICT", "source review changed")
            status = "unchanged"
        else:
            detail = pending_extractions(lib, owner, capture_id)
            if detail["pending_run_id"] != run_id or selected not in {
                    item["candidate_id"] for item in detail["proposed"]}:
                raise LibrarianError("REVISION_CONFLICT", "review candidate changed")
            lib.db.execute("INSERT INTO gateway_review_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (owner, source_key, fingerprint, capture_id, run_id, selected,
                            decision, corrected_text, actor, source["source_event_id"], _now()))
            status = "recorded"
    return {"status": status, "capture_id": capture_id, "pending_run_id": run_id,
            "candidate_id": selected, "decision": decision,
            "trace_status": "pending_reconciliation"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return write_error(LibrarianError("VALIDATION_FAILED", "input too large"), "gateway.review_decision")
    try:
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise LibrarianError("VALIDATION_FAILED", "review request must be an object")
        if not (args.root / "librarian.sqlite").is_file():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "Librarian store unavailable")
        with Library(args.root) as lib:
            result = record_review_decision(lib, message)
    except Exception as error:
        return write_error(error, "gateway.review_decision")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
