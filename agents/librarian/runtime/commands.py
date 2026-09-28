"""Owner-verified, idempotent application command entry point.

The Gateway resolves upload references to bytes before/while dispatching a
capture command. This module never trusts an owner or actor asserted inside a
model response, a photo, or unverified remote metadata.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from .knowledge import decide_candidate
from .pipeline import correct_trace, resolve_capture
from .store import Library, LibrarianError, _json, validate


def _required(payload: dict[str, Any], key: str) -> Any:
    if key not in payload or payload[key] is None:
        raise LibrarianError("VALIDATION_FAILED", f"payload.{key} is required")
    return payload[key]


def _store_receipt(lib: Library, owner_id: str, key: str,
                   fingerprint: str, receipt: dict[str, Any]) -> None:
    lib.db.execute("INSERT INTO command_receipts VALUES(?,?,?,?)",
                   (owner_id, key, fingerprint, _json(receipt)))


def _capture_args(payload: dict[str, Any],
                  resolve_upload: Callable[[str], bytes] | None) -> dict[str, Any]:
    if resolve_upload is None:
        raise LibrarianError("VALIDATION_FAILED", "trusted upload resolver required")
    source = _required(payload, "source")
    attachments = _required(payload, "attachments")
    if not isinstance(source, dict) or not isinstance(attachments, list):
        raise LibrarianError("VALIDATION_FAILED", "invalid capture payload")
    resolved = []
    for item in attachments:
        if not isinstance(item, dict):
            raise LibrarianError("VALIDATION_FAILED", "invalid attachment")
        data = resolve_upload(_required(item, "upload_ref"))
        if not isinstance(data, bytes):
            raise LibrarianError("VALIDATION_FAILED", "upload resolver did not return bytes")
        resolved.append({"source_item_id": _required(item, "source_item_id"),
                         "mime_type": _required(item, "mime_type"), "data": data})
    return {"transport": _required(source, "transport"),
            "account_id": _required(source, "account_id"),
            "conversation_id": _required(source, "conversation_id"),
            "source_event_id": _required(source, "source_event_id"),
            "attachments": resolved,
            "submitted_context": payload.get("submitted_context")}


def execute_command(lib: Library, command: dict[str, Any], *,
                    trusted_owner_id: str, trusted_actor_id: str,
                    resolve_upload: Callable[[str], bytes] | None = None) -> dict[str, Any]:
    """Execute the supported MVP command subset with a transactional receipt.

    A retry with the same owner/key/command/payload returns the original
    receipt. A changed business payload conflicts even if command_id or
    issued_at changes. Unsupported later-stage commands fail explicitly.
    """
    validate("Command", command)
    if command["owner_id"] != trusted_owner_id or command["actor"]["id"] != trusted_actor_id:
        raise LibrarianError("UNAUTHORIZED", "command identity differs from trusted caller")
    name = command["command"]
    payload = command["payload"]
    fingerprint = hashlib.sha256(_json({"command": name, "payload": payload}).encode()).hexdigest()
    key = command["idempotency_key"]
    with lib.transaction():
        previous = lib.db.execute("SELECT fingerprint,receipt FROM command_receipts WHERE owner_id=? AND idempotency_key=?",
                                  (trusted_owner_id, key)).fetchone()
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise LibrarianError("IDEMPOTENCY_CONFLICT", "same key has different business payload")
            if name == "reading.capture.ingest":
                # Verify immutable upload bytes and the previously accepted
                # object before repeating an accepted receipt.
                lib.ingest(trusted_owner_id, idempotency_key=key,
                           **_capture_args(payload, resolve_upload))
            return json.loads(previous["receipt"])
        object_id = None
        if name in {"catalog.register_work", "catalog.register_edition",
                    "catalog.register_book_instance"}:
            expected = {"catalog.register_work": "Work", "catalog.register_edition": "Edition",
                        "catalog.register_book_instance": "BookInstance"}[name]
            record = _required(payload, "record")
            if not isinstance(record, dict) or record.get("object_type") != expected:
                raise LibrarianError("VALIDATION_FAILED", "catalog record has wrong model")
            object_id = lib.register(trusted_owner_id, record)["id"]
        elif name == "reading.session.start":
            scope = payload.get("scope")
            session = lib.start_session(trusted_owner_id, payload.get("book_instance_id"),
                                        started_at=payload.get("started_at"),
                                        progress=payload.get("progress"),
                                        scope=tuple(scope) if scope is not None else None,
                                        correlation_id=command["command_id"])
            object_id = session["id"]
        elif name in {"reading.session.pause", "reading.session.resume",
                      "reading.session.report_progress", "reading.session.close"}:
            action = name.rsplit(".", 1)[1]
            session = lib.session_transition(trusted_owner_id,
                                             _required(payload, "session_id"), action,
                                             _required(payload, "expected_revision"),
                                             progress=payload.get("progress"),
                                             ended_at=payload.get("ended_at"),
                                             correlation_id=command["command_id"])
            object_id = session["id"]
        elif name == "reading.trace.correct":
            correction = _required(payload, "correction")
            if not isinstance(correction, dict) or not correction.keys() <= {"printed_text", "annotation"}:
                raise LibrarianError("VALIDATION_FAILED", "unsupported correction fields")
            fields = {field: correction[field] for field in ("printed_text", "annotation")
                      if field in correction}
            trace = correct_trace(lib, trusted_owner_id, _required(payload, "trace_id"),
                                  _required(payload, "expected_revision"),
                                  reason=_required(payload, "reason"), **fields)
            object_id = trace["id"]
        elif name == "reading.capture.resolve":
            updates = {field: payload[field] for field in
                       ("session_id", "work_id", "edition_id", "book_instance_id", "pages")
                       if field in payload}
            resolution = resolve_capture(lib, trusted_owner_id,
                                         _required(payload, "capture_id"),
                                         payload.get("expected_resolution_revision"),
                                         **updates)
            object_id = resolution["id"]
        elif name == "reading.capture.ingest":
            receipt = lib.ingest(trusted_owner_id, idempotency_key=key,
                                 **_capture_args(payload, resolve_upload))
            receipt = dict(receipt, command_id=command["command_id"])
            validate("CommandReceipt", receipt)
            _store_receipt(lib, trusted_owner_id, key, fingerprint, receipt)
            return receipt
        elif name in {"reading.knowledge_candidate.approve",
                      "reading.knowledge_candidate.reject"}:
            candidate = decide_candidate(
                lib, trusted_owner_id, _required(payload, "candidate_id"),
                _required(payload, "expected_revision"),
                approve=name.endswith(".approve"), reason=payload.get("reason"))
            object_id = candidate["id"]
        else:
            raise LibrarianError("VALIDATION_FAILED", f"command not implemented: {name}")
        receipt = {"command_id": command["command_id"], "status": "completed",
                   "batch_id": None, "capture_ids": [], "object_id": object_id}
        validate("CommandReceipt", receipt)
        _store_receipt(lib, trusted_owner_id, key, fingerprint, receipt)
        return receipt
