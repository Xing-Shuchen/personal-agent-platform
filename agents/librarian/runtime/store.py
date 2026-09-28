"""Durable Librarian M0 state: catalog, sessions, immutable captures, outbox.

The trusted caller supplies ``owner_id``; this module never accepts it from an
image, extractor, or catalog record as proof of authorization. Runtime files
belong under var/librarian (or an explicitly supplied test directory).
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


class LibrarianError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


_SCHEMA = json.loads((Path(__file__).parent / "schemas" / "contracts.schema.json").read_text(encoding="utf-8"))


def validate(model: str, value: dict[str, Any]) -> None:
    if model not in _SCHEMA["$defs"]:
        raise LibrarianError("VALIDATION_FAILED", f"unknown model {model}")
    schema = dict(_SCHEMA, **{"$ref": f"#/$defs/{model}"})
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
                    key=lambda error: list(map(str, error.path)))
    if errors:
        error = errors[0]
        location = ".".join(map(str, error.path)) or model
        raise LibrarianError("VALIDATION_FAILED", f"{location}: {error.message}")


class Library:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.objects = self.root / "objects"
        self.objects.mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.root / "librarian.sqlite")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript((Path(__file__).parent / "migrations" / "0001_initial.sql").read_text(encoding="utf-8"))

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "Library":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _get(self, owner_id: str, model: str, object_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT body FROM records WHERE owner_id=? AND model=? AND id=? AND current=1",
                              (owner_id, model, object_id)).fetchone()
        if row is None:
            raise LibrarianError("UNAUTHORIZED", f"{model} not found for owner")
        return json.loads(row["body"])

    def get(self, owner_id: str, model: str, object_id: str) -> dict[str, Any]:
        return self._get(owner_id, model, object_id)

    def _put(self, record: dict[str, Any]) -> None:
        model = record["object_type"]
        validate(model, record)
        revision = record.get("revision", 1)
        old = self.db.execute("SELECT revision FROM records WHERE owner_id=? AND model=? AND id=? AND current=1",
                              (record["owner_id"], model, record["id"])).fetchone()
        if old is None:
            if revision != 1 or record.get("supersedes_revision") is not None:
                raise LibrarianError("REVISION_CONFLICT", "initial record must be revision 1")
        else:
            if revision != old["revision"] + 1 or record.get("supersedes_revision") != old["revision"]:
                raise LibrarianError("REVISION_CONFLICT", "revision must follow current version")
            self.db.execute("UPDATE records SET current=0 WHERE owner_id=? AND model=? AND id=? AND current=1",
                            (record["owner_id"], model, record["id"]))
        self.db.execute("INSERT INTO records(owner_id,model,id,revision,current,body) VALUES(?,?,?,?,1,?)",
                        (record["owner_id"], model, record["id"], revision, _json(record)))

    def _event(self, owner_id: str, kind: str, aggregate_type: str, aggregate_id: str,
               revision: int, payload: dict[str, Any], correlation_id: str) -> None:
        event = {"event": kind, "version": 1, "event_id": _new("evt"),
                 "owner_id": owner_id, "occurred_at": _now(), "producer": "librarian",
                 "correlation_id": correlation_id, "causation_id": None,
                 "aggregate": {"type": aggregate_type, "id": aggregate_id, "revision": revision},
                 "payload": payload}
        validate("Event", event)
        self.db.execute("INSERT INTO outbox(event_id, owner_id, event_type, body) VALUES(?,?,?,?)",
                        (event["event_id"], owner_id, kind, _json(event)))

    def register(self, owner_id: str, record: dict[str, Any]) -> dict[str, Any]:
        """Register first Work/Edition/BookInstance revision under trusted owner."""
        model = record.get("object_type")
        if model not in {"Work", "Edition", "BookInstance"} or record.get("owner_id") != owner_id:
            raise LibrarianError("UNAUTHORIZED", "invalid owner or catalog model")
        validate(model, record)
        if model == "Edition":
            self._get(owner_id, "Work", record["work_id"])
        elif model == "BookInstance":
            self._get(owner_id, "Edition", record["edition_id"])
        with self.db:
            self._put(record)
        return record

    def start_session(self, owner_id: str, book_instance_id: str | None = None,
                      *, started_at: dict[str, Any] | None = None,
                      progress: dict[str, Any] | None = None,
                      correlation_id: str | None = None) -> dict[str, Any]:
        work_id = edition_id = None
        if book_instance_id:
            instance = self._get(owner_id, "BookInstance", book_instance_id)
            edition = self._get(owner_id, "Edition", instance["edition_id"])
            edition_id, work_id = edition["id"], edition["work_id"]
        record = {"object_type": "ReadingSession", "schema_version": "0.1.0",
                  "id": _new("session"), "owner_id": owner_id, "created_at": _now(),
                  "work_id": work_id, "edition_id": edition_id,
                  "book_instance_id": book_instance_id, "medium": "physical",
                  "status": "active", "started_at": started_at or _unknown_time(),
                  "ended_at": _unknown_time(), "progress": progress,
                  "session_note": None, "revision": 1, "supersedes_revision": None}
        with self.db:
            self._put(record)
            self._event(owner_id, "reading.session.started", "reading_session", record["id"], 1,
                        {"session_id": record["id"], "revision": 1, "medium": "physical",
                         "book_instance_id": book_instance_id}, correlation_id or record["id"])
        return record

    def session_transition(self, owner_id: str, session_id: str, action: str,
                           expected_revision: int, *, progress: dict[str, Any] | None = None,
                           ended_at: dict[str, Any] | None = None,
                           correlation_id: str | None = None) -> dict[str, Any]:
        current = self._get(owner_id, "ReadingSession", session_id)
        if current["revision"] != expected_revision:
            raise LibrarianError("REVISION_CONFLICT", "session revision changed")
        allowed = {"pause": {"active": "paused"}, "resume": {"paused": "active"},
                   "close": {"active": "closed", "paused": "closed"},
                   "report_progress": {"active": "active", "paused": "paused"}}
        if action not in allowed or current["status"] not in allowed[action]:
            raise LibrarianError("INVALID_STATE_TRANSITION", "session transition is not allowed")
        if action == "report_progress" and progress is None:
            raise LibrarianError("VALIDATION_FAILED", "progress report required")
        record = dict(current, revision=expected_revision + 1,
                      supersedes_revision=expected_revision,
                      created_at=_now(), status=allowed[action][current["status"]])
        if action in {"report_progress", "close"} and progress is not None:
            record["progress"] = progress
        if action == "close" and ended_at is not None:
            record["ended_at"] = ended_at
        with self.db:
            self._put(record)
            # A photographed page never changes reading progress. Only an
            # explicit report can update the held copy's current page.
            if (action in {"report_progress", "close"} and progress is not None
                    and progress["end_page"] is not None and record["book_instance_id"]):
                instance = self._get(owner_id, "BookInstance", record["book_instance_id"])
                instance = dict(instance, revision=instance["revision"] + 1,
                                supersedes_revision=instance["revision"], created_at=_now())
                instance["reading_status"] = dict(instance["reading_status"])
                instance["reading_status"]["current_page"] = progress["end_page"]
                instance["reading_status"]["progress_evidence_ref"] = progress["evidence_ref"]
                self._put(instance)
            kind = {"report_progress": "reading.session.progressed",
                    "close": "reading.session.closed"}.get(action)
            if kind:
                self._event(owner_id, kind, "reading_session", session_id, record["revision"],
                            {"session_id": session_id, "revision": record["revision"],
                             "progress": record["progress"]}, correlation_id or session_id)
        return record

    def ingest(self, owner_id: str, *, transport: str, account_id: str,
               conversation_id: str, source_event_id: str,
               attachments: list[dict[str, Any]], idempotency_key: str,
               submitted_context: dict[str, str | None] | None = None) -> dict[str, Any]:
        """Accept all original bytes before exposing a batch receipt.

        Attachments contain ``source_item_id``, ``mime_type`` and ``data`` bytes.
        Source event/item IDs identify a message, never the image hash alone.
        """
        if not owner_id or not idempotency_key or not all((transport, account_id, conversation_id, source_event_id)):
            raise LibrarianError("VALIDATION_FAILED", "stable source identity and idempotency key required")
        if not attachments or any(not isinstance(item.get("data"), bytes) or not item.get("source_item_id")
                                  or not item.get("mime_type") for item in attachments):
            raise LibrarianError("VALIDATION_FAILED", "attachments require bytes, MIME and item IDs")
        item_ids = [item["source_item_id"] for item in attachments]
        if len(set(item_ids)) != len(item_ids):
            raise LibrarianError("VALIDATION_FAILED", "source item IDs must be unique")
        context = {key: (submitted_context or {}).get(key) for key in
                   ("session_id", "work_id", "edition_id", "book_instance_id")}
        if context["session_id"]:
            self._get(owner_id, "ReadingSession", context["session_id"])
        for key, model in (("work_id", "Work"), ("edition_id", "Edition"),
                           ("book_instance_id", "BookInstance")):
            if context[key]:
                self._get(owner_id, model, context[key])
        fingerprint = hashlib.sha256(_json({"source": [transport, account_id, conversation_id,
                                                        source_event_id], "context": context,
                                           "attachments": [(item["source_item_id"], item["mime_type"],
                                                            hashlib.sha256(item["data"]).hexdigest())
                                                           for item in attachments]}).encode()).hexdigest()
        prior = self.db.execute("SELECT fingerprint,receipt FROM idempotency WHERE owner_id=? AND key=?",
                                (owner_id, idempotency_key)).fetchone()
        if prior:
            if prior["fingerprint"] != fingerprint:
                raise LibrarianError("IDEMPOTENCY_CONFLICT", "same key has different business payload")
            return json.loads(prior["receipt"])

        # Object files are placed first, fsynced, and then referenced by the
        # metadata transaction. Failed transactions may leave safe orphan blobs.
        assets = [self._save_object(item["data"], item["mime_type"]) for item in attachments]
        batch_id = _new("batch")
        capture_ids = [_new("capture") for _ in attachments]
        received_at = _now()
        batch = {"object_type": "CaptureBatch", "schema_version": "0.1.0",
                 "id": batch_id, "owner_id": owner_id, "created_at": received_at,
                 "origin": {"transport": transport, "account_id": account_id,
                            "conversation_id": conversation_id, "source_event_id": source_event_id},
                 "received_at": received_at, "capture_ids": capture_ids,
                 "status": "received", "revision": 1, "supersedes_revision": None}
        captures = []
        for item, asset, capture_id in zip(attachments, assets, capture_ids):
            captures.append({"object_type": "PageCapture", "schema_version": "0.1.0",
                             "id": capture_id, "owner_id": owner_id, "created_at": received_at,
                             "batch_id": batch_id, "received_at": received_at,
                             "captured_at": _unknown_time(), "asset": asset,
                             "origin": {**batch["origin"], "source_item_id": item["source_item_id"]},
                             "submitted_context": context})
        validate("CaptureBatch", batch)
        for capture in captures:
            validate("PageCapture", capture)
        receipt = {"command_id": idempotency_key, "status": "accepted",
                   "batch_id": batch_id, "capture_ids": capture_ids, "object_id": None}
        validate("CommandReceipt", receipt)
        try:
            with self.db:
                self._put(batch)
                for capture in captures:
                    self._put(capture)
                    origin = capture["origin"]
                    self.db.execute("INSERT INTO source_items(owner_id,transport,account_id,source_event_id,source_item_id,capture_id) VALUES(?,?,?,?,?,?)",
                                    (owner_id, transport, account_id, source_event_id,
                                     origin["source_item_id"], capture["id"]))
                self.db.execute("INSERT INTO idempotency(owner_id,key,fingerprint,receipt) VALUES(?,?,?,?)",
                                (owner_id, idempotency_key, fingerprint, _json(receipt)))
                self._event(owner_id, "reading.capture.received", "capture_batch", batch_id, 1,
                            {"batch_id": batch_id, "capture_ids": capture_ids}, idempotency_key)
        except sqlite3.IntegrityError as error:
            raise LibrarianError("IDEMPOTENCY_CONFLICT", "source item or idempotency key already accepted") from error
        return receipt

    def _save_object(self, data: bytes, mime_type: str) -> dict[str, Any]:
        digest = hashlib.sha256(data).hexdigest()
        target = self.objects / digest[:2] / digest
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            fd, temp_name = tempfile.mkstemp(dir=target.parent, prefix=".incoming-")
            try:
                with os.fdopen(fd, "wb") as out:
                    out.write(data)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(temp_name, target)
                directory_fd = os.open(target.parent, os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        return {"object_key": str(target.relative_to(self.root)), "sha256": digest,
                "mime_type": mime_type, "byte_size": len(data)}

    def read_original(self, owner_id: str, capture_id: str) -> bytes:
        capture = self._get(owner_id, "PageCapture", capture_id)
        asset = capture["asset"]
        path = self.root / asset["object_key"]
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != asset["sha256"] or len(data) != asset["byte_size"]:
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "original object failed integrity check")
        return data

    def pending_events(self, owner_id: str) -> list[dict[str, Any]]:
        return [json.loads(row[0]) for row in self.db.execute(
            "SELECT body FROM outbox WHERE owner_id=? AND delivered_at IS NULL ORDER BY rowid", (owner_id,))]


def _unknown_time() -> dict[str, Any]:
    return {"value": None, "confidence": None, "basis": "unknown"}
