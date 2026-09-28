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
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        raise LibrarianError("VALIDATION_FAILED", f"{location}: {error.validator} constraint failed")
    _validate_semantics(model, value)


def _validate_semantics(model: str, value: dict[str, Any]) -> None:
    """Cross-field constraints complement, rather than duplicate, JSON Schema."""
    revision = value.get("revision")
    if (revision is not None and "supersedes_revision" in value and
            value["supersedes_revision"] != (revision - 1 if revision > 1 else None)):
        raise LibrarianError("VALIDATION_FAILED", "revision and supersedes_revision disagree")
    if model == "CaptureBatch" and len(set(value["capture_ids"])) != len(value["capture_ids"]):
        raise LibrarianError("VALIDATION_FAILED", "capture IDs must be unique")
    if model == "CaptureResolution":
        for field in ("session", "work", "edition", "book_instance"):
            identity = value[field]
            if (identity["status"] == "resolved") != (identity["value"] is not None):
                raise LibrarianError("VALIDATION_FAILED", f"{field} resolution status/value disagree")
        for region in value["pages"]:
            page = region["page"]
            if (page["status"] == "resolved") != (page["value"] is not None):
                raise LibrarianError("VALIDATION_FAILED", "page status/value disagree")
    if model == "PageObservation" and "visible_title" in value:
        if value["visible_title"]["basis"] != "vision":
            raise LibrarianError("VALIDATION_FAILED", "visible title must come from vision")
    if model == "ReadingTrace":
        medium = value["medium"]
        if medium == "physical":
            if value["location"]["kind"] != "physical" or value["source"]["kind"] != "physical":
                raise LibrarianError("VALIDATION_FAILED", "physical trace needs physical source and location")
            if value["context_state"] == "resolved" and not all(
                    value[field] for field in ("work_id", "edition_id", "book_instance_id", "session_id")):
                raise LibrarianError("VALIDATION_FAILED", "resolved physical context requires full chain")
        elif value["location"]["kind"] != "digital" or value["source"]["kind"] != medium:
            raise LibrarianError("VALIDATION_FAILED", "digital trace source and medium disagree")
        if value["review"]["state"] == "pending" and not value["review"]["required"]:
            raise LibrarianError("VALIDATION_FAILED", "pending review must be required")
    if model == "KnowledgeCandidate":
        if (value["status"] == "promoted") != (value["knowledge_id"] is not None):
            raise LibrarianError("VALIDATION_FAILED", "promoted candidate needs a knowledge ID")
        if value["status"] == "rejected" and not value.get("decision_reason"):
            raise LibrarianError("VALIDATION_FAILED", "rejected candidate needs a reason")
        refs = [(ref["trace_id"], ref["revision"]) for ref in value["source_trace_refs"]]
        if len(refs) != len(set(refs)):
            raise LibrarianError("VALIDATION_FAILED", "candidate source refs must be unique")
    if model == "SearchRequest":
        filters = value["filters"]
        if not value["query"].strip() and not any(
                filters[key] for key in ("work_id", "edition_id", "book_instance_id",
                                         "session_id", "medium", "trace_types")) and not filters.get("page_number"):
            raise LibrarianError("VALIDATION_FAILED", "search needs text or a structural filter")
    if model == "Event":
        event = value["event"]
        aggregate = value["aggregate"]
        payload = value["payload"]
        expected = {
            "reading.capture.received": ("capture_batch", "batch_id"),
            "reading.capture.processed": ("processing_run", "processing_run_id"),
            "reading.session.started": ("reading_session", "session_id"),
            "reading.session.progressed": ("reading_session", "session_id"),
            "reading.session.closed": ("reading_session", "session_id"),
            "reading.trace.created": ("reading_trace", "trace_id"),
            "reading.trace.corrected": ("reading_trace", "trace_id"),
            "reading.knowledge_candidate.created": ("knowledge_candidate", "candidate_id"),
            "reading.knowledge.promoted": ("knowledge_candidate", "candidate_id"),
        }[event]
        if aggregate["type"] != expected[0] or aggregate["id"] != payload[expected[1]]:
            raise LibrarianError("VALIDATION_FAILED", "event aggregate and payload disagree")
        if "revision" in payload and aggregate["revision"] != payload["revision"]:
            raise LibrarianError("VALIDATION_FAILED", "event revisions disagree")
        if event == "reading.trace.corrected" and payload["previous_revision"] + 1 != payload["revision"]:
            raise LibrarianError("VALIDATION_FAILED", "corrected event revisions are not consecutive")


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
        self.db.executescript((Path(__file__).parent / "migrations" / "0002_koodo_native.sql").read_text(encoding="utf-8"))
        self.db.executescript((Path(__file__).parent / "migrations" / "0003_weread_native.sql").read_text(encoding="utf-8"))

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "Library":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self):
        """Compose domain operations without an inner commit escaping the caller."""
        if not self.db.in_transaction:
            with self.db:
                self.db.execute("BEGIN IMMEDIATE")
                yield
            return
        savepoint = "lib_" + uuid.uuid4().hex
        self.db.execute(f"SAVEPOINT {savepoint}")
        try:
            yield
            self.db.execute(f"RELEASE SAVEPOINT {savepoint}")
        except BaseException:
            self.db.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            self.db.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise

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
        with self.transaction():
            self._put(record)
        return record

    def start_session(self, owner_id: str, book_instance_id: str | None = None,
                      *, started_at: dict[str, Any] | None = None,
                      progress: dict[str, Any] | None = None,
                      scope: tuple[str, str, str] | None = None,
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
        with self.transaction():
            self._put(record)
            if scope is not None:
                if len(scope) != 3 or not all(scope):
                    raise LibrarianError("VALIDATION_FAILED", "session scope requires transport, account and conversation")
                self.db.execute("UPDATE session_scope SET selected=0 WHERE owner_id=? AND transport=? AND account_id=? AND conversation_id=?",
                                (owner_id, *scope))
                self.db.execute("INSERT INTO session_scope VALUES(?,?,?,?,?,?,?)",
                                (owner_id, *scope, record["id"], 1, None))
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
        with self.transaction():
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
        scope = (owner_id, transport, account_id, conversation_id)
        chosen_session, chosen_basis = self._choose_session(scope, context["session_id"])
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
            receipt = json.loads(prior["receipt"])
            for capture_id in receipt["capture_ids"]:
                self.read_original(owner_id, capture_id)
            return receipt

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
            with self.transaction():
                self._put(batch)
                for capture in captures:
                    self._put(capture)
                    if chosen_session:
                        self.db.execute("INSERT INTO capture_context VALUES(?,?,?,?)",
                                        (owner_id, capture["id"], chosen_session, chosen_basis))
                    origin = capture["origin"]
                    self.db.execute("INSERT INTO source_items(owner_id,transport,account_id,source_event_id,source_item_id,capture_id) VALUES(?,?,?,?,?,?)",
                                    (owner_id, transport, account_id, source_event_id,
                                     origin["source_item_id"], capture["id"]))
                self.db.execute("INSERT INTO idempotency(owner_id,key,fingerprint,receipt) VALUES(?,?,?,?)",
                                (owner_id, idempotency_key, fingerprint, _json(receipt)))
                self._event(owner_id, "reading.capture.received", "capture_batch", batch_id, 1,
                            {"batch_id": batch_id, "capture_ids": capture_ids}, idempotency_key)
                if chosen_session:
                    self._remember_session(scope, chosen_session, received_at,
                                           chosen_basis == "active_session")
        except sqlite3.IntegrityError as error:
            raise LibrarianError("IDEMPOTENCY_CONFLICT", "source item or idempotency key already accepted") from error
        return receipt

    def _choose_session(self, scope: tuple[str, str, str, str],
                        explicit_id: str | None) -> tuple[str | None, str]:
        if explicit_id:
            return explicit_id, "explicit_session"
        rows = self.db.execute("SELECT session_id,selected,last_assigned_at FROM session_scope "
                               "WHERE owner_id=? AND transport=? AND account_id=? AND conversation_id=?",
                               scope).fetchall()
        active = []
        for row in rows:
            try:
                session = self._get(scope[0], "ReadingSession", row["session_id"])
            except LibrarianError:
                continue
            if session["status"] == "active":
                active.append(row)
        selected = [row for row in active if row["selected"]]
        if len(selected) == 1:
            return selected[0]["session_id"], "active_session"
        if len(selected) > 1:
            return None, "unknown"
        recent = []
        now = datetime.now(timezone.utc)
        for row in active:
            if row["last_assigned_at"]:
                age = now - datetime.fromisoformat(row["last_assigned_at"])
                if timedelta(0) <= age <= timedelta(minutes=90):
                    recent.append(row)
        if len(recent) == 1:
            return recent[0]["session_id"], "recent_affinity"
        return None, "unknown"

    def _remember_session(self, scope: tuple[str, str, str, str], session_id: str,
                          at: str, selected: bool) -> None:
        # A per-message explicit hint is not a long-lived selection. It
        # replaces a stale selected session, then grants only soft affinity.
        prior = self.db.execute("SELECT selected FROM session_scope WHERE owner_id=? AND transport=? AND account_id=? AND conversation_id=? AND session_id=?",
                                (*scope, session_id)).fetchone()
        selected = selected or bool(prior and prior["selected"])
        if not selected:
            self.db.execute("UPDATE session_scope SET selected=0 WHERE owner_id=? AND transport=? AND account_id=? AND conversation_id=?",
                            scope)
        self.db.execute("INSERT INTO session_scope(owner_id,transport,account_id,conversation_id,session_id,selected,last_assigned_at) "
                        "VALUES(?,?,?,?,?,?,?) ON CONFLICT(owner_id,transport,account_id,conversation_id,session_id) "
                        "DO UPDATE SET selected=excluded.selected,last_assigned_at=excluded.last_assigned_at",
                        (*scope, session_id, int(selected), at))

    def _save_object(self, data: bytes, mime_type: str) -> dict[str, Any]:
        digest = hashlib.sha256(data).hexdigest()
        target = self.objects / digest[:2] / digest
        target.parent.mkdir(exist_ok=True)
        if target.is_symlink():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "object path is not a regular file")
        if target.exists():
            if _sha256_file(target) != digest or target.stat().st_size != len(data):
                raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "existing object failed integrity check")
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
        return self._read_object(capture["asset"])

    def read_trace_evidence(self, owner_id: str, trace_id: str,
                            index: int = 0) -> tuple[bytes, str]:
        trace = self._get(owner_id, "ReadingTrace", trace_id)
        if not 0 <= index < len(trace["provenance"]):
            raise LibrarianError("VALIDATION_FAILED", "evidence index out of range")
        asset = trace["provenance"][index]
        return self._read_object(asset), asset["mime_type"]

    def _read_object(self, asset: dict[str, Any]) -> bytes:
        path = (self.root / asset["object_key"]).resolve()
        if not path.is_relative_to(self.objects.resolve()) or path.is_symlink():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "object path outside private store")
        try:
            data = path.read_bytes()
        except OSError as error:
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "original object cannot be read") from error
        if hashlib.sha256(data).hexdigest() != asset["sha256"] or len(data) != asset["byte_size"]:
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "original object failed integrity check")
        return data

    def pending_events(self, owner_id: str) -> list[dict[str, Any]]:
        return [json.loads(row[0]) for row in self.db.execute(
            "SELECT body FROM outbox WHERE owner_id=? AND delivered_at IS NULL ORDER BY rowid", (owner_id,))]


def _unknown_time() -> dict[str, Any]:
    return {"value": None, "confidence": None, "basis": "unknown"}
