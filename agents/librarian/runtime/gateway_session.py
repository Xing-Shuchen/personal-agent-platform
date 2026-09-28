"""Trusted Gateway adapter for explicit reading-session operations.

The plugin supplies owner, actor, conversation and source-message identity from
the inbound channel. Model arguments contain only the requested operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .commands import execute_command
from .store import Library, LibrarianError, _now


MAX_INPUT_BYTES = 8192
ACTIONS = {"start", "progress", "pause", "resume", "close", "status"}


def _current(lib: Library, owner: str, model: str) -> list[dict]:
    return [json.loads(row[0]) for row in lib.db.execute(
        "SELECT body FROM records WHERE owner_id=? AND model=? AND current=1",
        (owner, model))]


def _book_instance(lib: Library, owner: str, query: str) -> tuple[str, str]:
    works = _current(lib, owner, "Work")
    editions = _current(lib, owner, "Edition")
    copies = [item for item in _current(lib, owner, "BookInstance")
              if item["medium"] == "physical"]
    query = query.strip().casefold()
    matched = [work for work in works if work["title"].casefold() == query]
    if not matched:
        matched = [work for work in works if query in work["title"].casefold()]
    ids = {work["id"] for work in matched}
    edition_ids = {item["id"] for item in editions if item["work_id"] in ids or
                   item["isbn"]["isbn13"] == query}
    choices = [item for item in copies if item["edition_id"] in edition_ids]
    if len(choices) != 1:
        raise LibrarianError("NEEDS_BOOK_RESOLUTION" if not choices else "CONTEXT_CONFLICT",
                             "book title/ISBN must identify exactly one physical copy")
    edition = lib.get(owner, "Edition", choices[0]["edition_id"])
    work = lib.get(owner, "Work", edition["work_id"])
    return choices[0]["id"], work["title"]


def _scoped_session(lib: Library, owner: str, scope: tuple[str, str, str]) -> dict:
    rows = lib.db.execute(
        "SELECT session_id FROM session_scope WHERE owner_id=? AND transport=? "
        "AND account_id=? AND conversation_id=? AND selected=1",
        (owner, *scope)).fetchall()
    if len(rows) != 1:
        raise LibrarianError("CONTEXT_CONFLICT", "select one reading session first")
    return lib.get(owner, "ReadingSession", rows[0]["session_id"])


def session_inbound(lib: Library, message: dict) -> dict:
    owner, actor = message.get("owner_id"), message.get("actor_id")
    source, action = message.get("source"), message.get("action")
    if (not isinstance(owner, str) or not owner or not isinstance(actor, str) or not actor
            or not isinstance(source, dict) or action not in ACTIONS):
        raise LibrarianError("VALIDATION_FAILED", "trusted identity, source and session action required")
    keys = ("transport", "account_id", "conversation_id", "source_event_id")
    if any(not isinstance(source.get(key), str) or not source[key] for key in keys):
        raise LibrarianError("VALIDATION_FAILED", "stable inbound source identity required")
    scope = tuple(source[key] for key in keys[:3])
    identity = json.dumps([owner, actor, *[source[key] for key in keys]],
                          ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(identity.encode()).hexdigest()
    request = {"action": action, "book": message.get("book") if action == "start" else None,
               "page": message.get("page") if action == "progress" else None}
    fingerprint = hashlib.sha256(json.dumps(request, ensure_ascii=False,
                                            sort_keys=True).encode()).hexdigest()
    lib.db.execute("CREATE TABLE IF NOT EXISTS gateway_session_receipts ("
                   "owner_id TEXT NOT NULL, source_key TEXT NOT NULL, "
                   "fingerprint TEXT NOT NULL, result TEXT NOT NULL, "
                   "PRIMARY KEY(owner_id,source_key))")
    with lib.transaction():
        previous = lib.db.execute("SELECT fingerprint,result FROM gateway_session_receipts "
                                  "WHERE owner_id=? AND source_key=?", (owner, digest)).fetchone()
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise LibrarianError("IDEMPOTENCY_CONFLICT", "source message changed session action")
            return json.loads(previous["result"])
        result = _execute_session_action(lib, message, owner, actor, source, action,
                                         scope, digest)
        lib.db.execute("INSERT INTO gateway_session_receipts VALUES(?,?,?,?)",
                       (owner, digest, fingerprint, json.dumps(result, ensure_ascii=False)))
        return result


def _execute_session_action(lib: Library, message: dict, owner: str, actor: str,
                            source: dict, action: str, scope: tuple[str, str, str],
                            digest: str) -> dict:
    if action == "start":
        book = message.get("book")
        if not isinstance(book, str) or not book.strip() or len(book) > 200:
            raise LibrarianError("VALIDATION_FAILED", "book title or ISBN required")
        copy_id, title = _book_instance(lib, owner, book)
        selected = None
        try:
            selected = _scoped_session(lib, owner, scope)
        except LibrarianError as error:
            if error.code != "CONTEXT_CONFLICT":
                raise
        if selected and selected["book_instance_id"] == copy_id:
            if selected["status"] == "active":
                return {"status": "unchanged", "action": action,
                        "session_id": selected["id"], "revision": selected["revision"],
                        "book": title}
            if selected["status"] == "paused":
                payload = {"session_id": selected["id"],
                           "expected_revision": selected["revision"]}
                command_name = "reading.session.resume"
            else:
                payload = {"book_instance_id": copy_id, "scope": list(scope)}
                command_name = "reading.session.start"
        else:
            payload = {"book_instance_id": copy_id, "scope": list(scope)}
            command_name = "reading.session.start"
    else:
        session = _scoped_session(lib, owner, scope)
        if action == "status":
            return {"status": session["status"], "action": action,
                    "session_id": session["id"], "revision": session["revision"],
                    "work_id": session["work_id"], "progress": session["progress"]}
        payload = {"session_id": session["id"],
                   "expected_revision": session["revision"]}
        if action == "progress":
            page = message.get("page")
            if isinstance(page, bool) or not isinstance(page, int) or not 1 <= page <= 9999:
                raise LibrarianError("VALIDATION_FAILED", "reported page must be an integer")
            payload["progress"] = {"start_page": None,
                                   "end_page": {"label": str(page), "number": page,
                                                "scheme": "arabic"},
                                   "basis": "user_statement", "reported_at": _now(),
                                   "evidence_ref": source["source_event_id"]}
            command_name = "reading.session.report_progress"
        else:
            command_name = f"reading.session.{action}"
    command = {"command": command_name, "version": 1,
               "command_id": "cmd_session_" + digest,
               "owner_id": owner, "issued_at": _now(),
               "idempotency_key": "gateway_session_" + digest,
               "actor": {"type": "user", "id": actor}, "payload": payload}
    receipt = execute_command(lib, command, trusted_owner_id=owner,
                              trusted_actor_id=actor)
    updated = lib.get(owner, "ReadingSession", receipt["object_id"])
    return {"status": updated["status"], "action": action,
            "session_id": updated["id"], "revision": updated["revision"],
            "work_id": updated["work_id"], "progress": updated["progress"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Trusted Librarian session command")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        print(json.dumps({"error": {"code": "VALIDATION_FAILED"}}))
        return 2
    try:
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise LibrarianError("VALIDATION_FAILED", "session request must be an object")
        if not (args.root / "librarian.sqlite").is_file():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "Librarian store is unavailable")
        with Library(args.root) as lib:
            result = session_inbound(lib, message)
    except (json.JSONDecodeError, LibrarianError) as error:
        code = error.code if isinstance(error, LibrarianError) else "VALIDATION_FAILED"
        print(json.dumps({"error": {"code": code}}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
