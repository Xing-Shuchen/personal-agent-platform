"""Read-only Koodo SQLite source adapter with replayable local synchronization."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .knowledge import supersede_pending_for_trace
from .pipeline import _index_trace
from .store import Library, LibrarianError, _json, _now, _unknown_time, validate


BOOK_COLUMNS = ("key", "name", "author", "description", "md5", "cover", "format",
                "publisher", "size", "page", "path", "charset")
NOTE_COLUMNS = ("key", "bookKey", "date", "chapter", "chapterIndex", "text", "cfi",
                "range", "notes", "percentage", "color", "tag")


def _read_table(path: Path, table: str, columns: tuple[str, ...]) -> list[dict[str, Any]]:
    if not path.is_file():
        raise LibrarianError("UPSTREAM_UNAVAILABLE", f"Koodo {table} database is unavailable")
    try:
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True,
                             timeout=5)
        try:
            db.row_factory = sqlite3.Row
            actual = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
            if not set(columns) <= actual:
                raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", f"Koodo {table} columns changed")
            return [dict(row) for row in db.execute(
                f"SELECT {','.join(columns)} FROM {table} ORDER BY key")]
        finally:
            db.close()
    except sqlite3.Error as error:
        raise LibrarianError("UPSTREAM_UNAVAILABLE", f"Koodo {table} database cannot be read") from error


def read_koodo_snapshot(books_db: Path, notes_db: Path) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return a validated native snapshot without writing to Koodo's files."""
    books = _read_table(Path(books_db), "books", BOOK_COLUMNS)
    notes = _read_table(Path(notes_db), "notes", NOTE_COLUMNS)
    by_key = {book["key"]: book for book in books if isinstance(book["key"], str) and book["key"]}
    if len(by_key) != len(books):
        raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "Koodo book keys are not unique")
    seen = set()
    result = []
    for note in notes:
        key, book_key = note["key"], note["bookKey"]
        if (not isinstance(key, str) or not key or key in seen or book_key not in by_key
                or not isinstance(note["text"], str) or not isinstance(note["notes"], str)):
            raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "Koodo note identity or content is invalid")
        try:
            if not isinstance(json.loads(note["cfi"]), dict):
                raise ValueError("locator must be an object")
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "Koodo note locator is invalid") from error
        seen.add(key)
        result.append((by_key[book_key], note))
    return result


def _identity(owner_id: str, source_id: str, book: dict[str, Any], note: dict[str, Any]) -> tuple[str, str, str]:
    work_id = "work_" + hashlib.sha256(_json([owner_id, "koodo-sqlite", source_id,
                                              book["key"]]).encode()).hexdigest()[:32]
    trace_id = "rt_" + hashlib.sha256(_json([owner_id, "koodo-sqlite", source_id,
                                             book["key"], note["key"]]).encode()).hexdigest()[:32]
    record_id = f"sqlite:{source_id}:{note['key']}"
    return work_id, trace_id, record_id


def _source_fields(note: dict[str, Any]) -> dict[str, Any]:
    printed = note["text"] if note["text"].strip() else None
    annotation = note["notes"] if note["notes"].strip() else None
    return {
        "location": {"kind": "digital", "chapter": note["chapter"] or None,
                     "paragraph": None, "source_locator": note["cfi"], "epub_cfi": None},
        "trace_types": ["highlight", "inline_note"] if annotation else ["highlight"],
        "content": {"printed_text": {"text": printed, "confidence": None,
                                     "basis": "source_payload" if printed else "unknown"},
                    "annotation": {"text": annotation, "confidence": None,
                                   "basis": "source_payload" if annotation else "unknown"},
                    "symbols": []},
    }


def _new_trace(owner_id: str, source_id: str, book: dict[str, Any],
               note: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    work_id, trace_id, record_id = _identity(owner_id, source_id, book, note)
    trace = {"object_type": "ReadingTrace", "schema_version": "0.1.0",
             "id": trace_id, "owner_id": owner_id, "created_at": _now(),
             "revision": 1, "supersedes_revision": None, "status": "active",
             "context_state": "resolved", "work_id": work_id,
             "edition_id": None, "book_instance_id": None, "session_id": None,
             "medium": "koodo", **_source_fields(note),
             "source": {"kind": "koodo", "raw_payload": asset,
                        "source_record_id": record_id},
             "provenance": [asset],
             "confidence": {"book_resolution": None, "page_number": None},
             "marked_at": _unknown_time(),
             "attribution": {"mark_author": "unknown", "basis": "unknown"},
             "intent_signals": [], "vocabulary_version": None,
             "review": {"required": False, "state": "none", "reason": None}}
    validate("ReadingTrace", trace)
    return trace


def _work(owner_id: str, source_id: str, book: dict[str, Any], work_id: str) -> dict[str, Any]:
    return {"object_type": "Work", "schema_version": "0.1.0",
            "id": work_id, "owner_id": owner_id, "created_at": _now(),
            "title": book["name"], "original_title": None,
            "authors": [{"name": book["author"], "entity_id": None}]
            if book["author"] else [],
            "identifiers": [{"scheme": "koodo_book_key", "value": book["key"]}],
            "revision": 1, "supersedes_revision": None}


def _revise(lib: Library, owner_id: str, prior: dict[str, Any], *,
            fields: dict[str, Any] | None = None, asset: dict[str, Any] | None = None,
            status: str = "active", reason: str, source_id: str) -> dict[str, Any]:
    revised = json.loads(_json(prior))
    revised.update({"revision": prior["revision"] + 1,
                    "supersedes_revision": prior["revision"],
                    "created_at": _now(), "status": status})
    if fields:
        revised.update(fields)
    if asset:
        revised["source"]["raw_payload"] = asset
        revised["provenance"] = [asset]
    lib._put(revised)
    supersede_pending_for_trace(lib, owner_id, prior, revised)
    if status == "active":
        _index_trace(lib, revised)
    else:
        lib.db.execute("DELETE FROM trace_index WHERE owner_id=? AND trace_id=?",
                       (owner_id, revised["id"]))
    lib._event(owner_id, "reading.trace.corrected", "reading_trace", revised["id"],
               revised["revision"], {"trace_id": revised["id"],
               "previous_revision": prior["revision"], "revision": revised["revision"],
               "reason": reason}, source_id)
    return revised


def _matches_accepted_source(lib: Library, trace: dict[str, Any]) -> bool:
    raw = lib._read_object(trace["source"]["raw_payload"])
    old = json.loads(raw)
    fields = _source_fields(old["note"])
    return all(trace[key] == value for key, value in fields.items())


def sync_koodo_sqlite(lib: Library, owner_id: str, source_id: str,
                      books_db: Path, notes_db: Path, *,
                      allow_empty_source: bool = False) -> dict[str, int]:
    """Sync native Koodo notes; preserve corrected traces for reconciliation."""
    if not owner_id or not re.fullmatch(r"[A-Za-z0-9_-]+", source_id):
        raise LibrarianError("VALIDATION_FAILED", "trusted owner and stable source ID required")
    snapshot = read_koodo_snapshot(books_db, notes_db)
    if not snapshot and not allow_empty_source and lib.db.execute(
            "SELECT 1 FROM koodo_native_records WHERE owner_id=? AND source_id=? LIMIT 1",
            (owner_id, source_id)).fetchone():
        raise LibrarianError("RECONCILIATION_REQUIRED", "empty Koodo snapshot needs explicit confirmation")
    counts = {"source_notes": len(snapshot), "created": 0, "updated": 0,
              "deleted": 0, "unchanged": 0, "pending": 0}
    seen = set()
    with lib.transaction():
        lib.bind_digital_source(owner_id, "koodo", source_id)
        for book, note in snapshot:
            note_key = note["key"]
            seen.add(note_key)
            work_id, trace_id, _ = _identity(owner_id, source_id, book, note)
            raw = _json({"book": book, "note": note}).encode("utf-8")
            digest = hashlib.sha256(raw).hexdigest()
            row = lib.db.execute(
                "SELECT * FROM koodo_native_records WHERE owner_id=? AND source_id=? AND note_key=?",
                (owner_id, source_id, note_key)).fetchone()
            if row and row["book_key"] != book["key"]:
                raise LibrarianError("RECONCILIATION_REQUIRED", "Koodo note moved between books")
            if row and row["state"] == "active" and row["accepted_sha256"] == digest:
                counts["unchanged"] += 1
                continue
            if row and row["state"] == "pending" and row["pending_sha256"] == digest:
                counts["pending"] += 1
                continue
            if row and row["state"] == "pending" and row["accepted_sha256"] == digest:
                lib.db.execute("UPDATE koodo_native_records SET state='active',pending_sha256=NULL,pending_asset=NULL "
                               "WHERE owner_id=? AND source_id=? AND note_key=?",
                               (owner_id, source_id, note_key))
                counts["unchanged"] += 1
                continue
            asset = lib._save_object(raw, "application/json")
            if row is None:
                if lib.db.execute("SELECT 1 FROM records WHERE owner_id=? AND model='Work' AND id=?",
                                  (owner_id, work_id)).fetchone() is None:
                    lib._put(_work(owner_id, source_id, book, work_id))
                trace = _new_trace(owner_id, source_id, book, note, asset)
                lib._put(trace)
                _index_trace(lib, trace)
                lib._event(owner_id, "reading.trace.created", "reading_trace", trace_id, 1,
                           {"trace_id": trace_id, "revision": 1, "medium": "koodo",
                            "book_instance_id": None}, source_id)
                lib.db.execute("INSERT INTO koodo_native_records VALUES(?,?,?,?,?,?,?,?,?)",
                               (owner_id, source_id, note_key, book["key"], trace_id,
                                digest, "active", None, None))
                counts["created"] += 1
                continue
            prior = lib.get(owner_id, "ReadingTrace", row["trace_id"])
            if row["state"] != "deleted" and not _matches_accepted_source(lib, prior):
                lib.db.execute("UPDATE koodo_native_records SET state='pending',pending_sha256=?,pending_asset=? "
                               "WHERE owner_id=? AND source_id=? AND note_key=?",
                               (digest, _json(asset), owner_id, source_id, note_key))
                counts["pending"] += 1
                continue
            _revise(lib, owner_id, prior, fields=_source_fields(note), asset=asset,
                    reason="Koodo source record changed", source_id=source_id)
            lib.db.execute("UPDATE koodo_native_records SET accepted_sha256=?,state='active',"
                           "pending_sha256=NULL,pending_asset=NULL WHERE owner_id=? AND source_id=? AND note_key=?",
                           (digest, owner_id, source_id, note_key))
            counts["updated"] += 1
        prior_rows = lib.db.execute(
            "SELECT note_key,trace_id,state FROM koodo_native_records WHERE owner_id=? AND source_id=?",
            (owner_id, source_id)).fetchall()
        for row in prior_rows:
            if row["note_key"] in seen or row["state"] == "deleted":
                continue
            prior = lib.get(owner_id, "ReadingTrace", row["trace_id"])
            _revise(lib, owner_id, prior, status="superseded",
                    reason="Koodo source record removed", source_id=source_id)
            lib.db.execute("UPDATE koodo_native_records SET state='deleted',pending_sha256=NULL,pending_asset=NULL "
                           "WHERE owner_id=? AND source_id=? AND note_key=?",
                           (owner_id, source_id, row["note_key"]))
            counts["deleted"] += 1
    return counts


def pending_koodo_reconciliation(lib: Library, owner_id: str) -> list[dict[str, str]]:
    """List owner-scoped source edits held because a trace was corrected."""
    if not owner_id:
        raise LibrarianError("VALIDATION_FAILED", "trusted owner required")
    rows = lib.db.execute(
        "SELECT source_id,note_key,trace_id FROM koodo_native_records "
        "WHERE owner_id=? AND state='pending' ORDER BY source_id,note_key", (owner_id,))
    return [dict(row) for row in rows]


def reconcile_koodo_note(lib: Library, owner_id: str, source_id: str,
                         note_key: str, expected_trace_revision: int, *,
                         accept_source: bool) -> dict[str, Any]:
    """Resolve a held source edit, explicitly replacing or retaining user text."""
    with lib.transaction():
        row = lib.db.execute(
            "SELECT * FROM koodo_native_records WHERE owner_id=? AND source_id=? AND note_key=?",
            (owner_id, source_id, note_key)).fetchone()
        if row is None:
            raise LibrarianError("UNAUTHORIZED", "Koodo record not found for owner")
        if row["state"] != "pending" or not row["pending_asset"]:
            raise LibrarianError("INVALID_STATE_TRANSITION", "Koodo record has no pending edit")
        prior = lib.get(owner_id, "ReadingTrace", row["trace_id"])
        if prior["revision"] != expected_trace_revision:
            raise LibrarianError("REVISION_CONFLICT", "trace revision changed")
        asset = json.loads(row["pending_asset"])
        payload = json.loads(lib._read_object(asset))
        note = payload["note"]
        if note["key"] != note_key or note["bookKey"] != row["book_key"]:
            raise LibrarianError("VALIDATION_FAILED", "pending Koodo identity changed")
        revised = _revise(
            lib, owner_id, prior, fields=_source_fields(note) if accept_source else None,
            asset=asset, reason=("Koodo source edit accepted" if accept_source
                                 else "Koodo source edit linked; user correction retained"),
            source_id=source_id)
        lib.db.execute(
            "UPDATE koodo_native_records SET accepted_sha256=pending_sha256,state='active',"
            "pending_sha256=NULL,pending_asset=NULL "
            "WHERE owner_id=? AND source_id=? AND note_key=?",
            (owner_id, source_id, note_key))
        return revised


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync read-only Koodo SQLite notes into Librarian")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--owner", required=True, help="trusted local owner ID")
    parser.add_argument("--source-id", required=True, help="stable ID for this Koodo installation")
    parser.add_argument("--books-db", type=Path, required=True)
    parser.add_argument("--notes-db", type=Path, required=True)
    parser.add_argument("--allow-empty-source", action="store_true",
                        help="confirm that an empty source should retire all tracked notes")
    args = parser.parse_args()
    with Library(args.root) as lib:
        result = sync_koodo_sqlite(lib, args.owner, args.source_id,
                                   args.books_db, args.notes_db,
                                   allow_empty_source=args.allow_empty_source)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
