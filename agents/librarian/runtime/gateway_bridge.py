"""Local OpenClaw media hook bridge into the transactional capture command.

The caller must be the trusted Gateway plugin: this stdin protocol is not an
authentication boundary or a network endpoint. The plugin maps a sender to an
owner and sends only staged attachment bytes with stable message identities.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .commands import execute_command
from .store import Library, LibrarianError
from .gateway_errors import write_error


MAX_INPUT_BYTES = 80 * 1024 * 1024
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
MAX_BATCH_BYTES = 100 * 1024 * 1024


def accept_inbound(lib: Library, message: dict[str, Any]) -> dict[str, Any]:
    owner_id, actor_id = message.get("owner_id"), message.get("actor_id")
    source, incoming = message.get("source"), message.get("attachments")
    if not isinstance(owner_id, str) or not owner_id or not isinstance(actor_id, str) or not actor_id:
        raise LibrarianError("VALIDATION_FAILED", "trusted owner and actor required")
    if not isinstance(source, dict) or not isinstance(incoming, list) or not incoming:
        raise LibrarianError("VALIDATION_FAILED", "source and image attachments required")
    source_keys = ("transport", "account_id", "conversation_id", "source_event_id")
    if any(not isinstance(source.get(key), str) or not source[key] for key in source_keys):
        raise LibrarianError("VALIDATION_FAILED", "stable source identity required")
    source = {key: source[key] for key in source_keys}
    upload_bytes: dict[str, bytes] = {}
    attachments = []
    batch_bytes = 0
    for item in incoming:
        if not isinstance(item, dict):
            raise LibrarianError("VALIDATION_FAILED", "invalid image attachment")
        item_id, mime, encoded = (item.get(key) for key in ("source_item_id", "mime_type", "data_b64"))
        data_path = item.get("data_path")
        if (not isinstance(item_id, str) or not item_id or item_id in upload_bytes
                or not isinstance(mime, str) or not mime.startswith("image/")
                or (isinstance(encoded, str) == isinstance(data_path, str))):
            raise LibrarianError("VALIDATION_FAILED", "invalid image attachment identity or MIME")
        if isinstance(data_path, str):
            path = Path(data_path)
            if not path.is_absolute():
                raise LibrarianError("VALIDATION_FAILED", "attachment path must be absolute")
            try:
                if not path.is_file() or path.stat().st_size > MAX_ATTACHMENT_BYTES:
                    raise LibrarianError("VALIDATION_FAILED", "attachment size outside allowed range")
                data = path.read_bytes()
            except OSError as error:
                raise LibrarianError("VALIDATION_FAILED", "attachment unavailable") from error
        else:
            try:
                data = base64.b64decode(encoded, validate=True)
            except (ValueError, base64.binascii.Error) as error:
                raise LibrarianError("VALIDATION_FAILED", "invalid attachment encoding") from error
        if not data or len(data) > MAX_ATTACHMENT_BYTES:
            raise LibrarianError("VALIDATION_FAILED", "attachment size outside allowed range")
        batch_bytes += len(data)
        if batch_bytes > MAX_BATCH_BYTES:
            raise LibrarianError("VALIDATION_FAILED", "image batch too large")
        upload_bytes[item_id] = data
        attachments.append({"source_item_id": item_id, "mime_type": mime, "upload_ref": item_id})
    key_material = json.dumps([owner_id, *[source[key] for key in source_keys]],
                              ensure_ascii=False, separators=(",", ":"))
    identity = hashlib.sha256(key_material.encode()).hexdigest()
    command = {"command": "reading.capture.ingest", "version": 1,
               "command_id": "cmd_gateway_" + identity,
               "owner_id": owner_id,
               "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "idempotency_key": "gateway_" + identity,
               "actor": {"type": "user", "id": actor_id},
               "payload": {"source": source, "attachments": attachments,
                           "submitted_context": message.get("submitted_context") or {
                               "session_id": None, "work_id": None,
                               "edition_id": None, "book_instance_id": None}}}
    return execute_command(lib, command, trusted_owner_id=owner_id,
                           trusted_actor_id=actor_id,
                           resolve_upload=upload_bytes.__getitem__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Trusted local Librarian media intake")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return write_error(LibrarianError("VALIDATION_FAILED", "input too large"), "gateway.media_intake")
    try:
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise LibrarianError("VALIDATION_FAILED", "message must be an object")
        with Library(args.root) as lib:
            receipt = accept_inbound(lib, message)
    except Exception as error:
        return write_error(error, "gateway.media_intake")
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
